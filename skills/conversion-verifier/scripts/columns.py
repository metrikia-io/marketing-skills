#!/usr/bin/env python3
"""
Column detection and value parsing for messy real-world exports.

Ad and store exports vary wildly: different languages, different UI versions,
different column sets depending on which breakdowns the user enabled. Rather
than demanding one exact format, we look for any column whose normalized name
matches a known pattern. This is the difference between a tool that works on
the user's actual file and one that only works on the sample file.
"""

import csv
import re
from datetime import datetime

ADS_PATTERNS = {
    "campaign":    [r"campaignname", r"campaign$", r"nomdelacampagne", r"kampagnenname"],
    "adset":       [r"adsetname", r"adset$", r"nomdelensembledepublicites"],
    "ad":          [r"adname", r"^ad$", r"nomdelapublicite"],
    "date":        [r"^day$", r"^date$", r"reportingstarts", r"jour", r"datestart"],
    "spend":       [r"amountspent", r"^spend$", r"^cost$", r"montantdepense", r"ausgegebenerbetrag"],
    "purchases":   [r"^purchases$", r"^websitepurchases$", r"^results$", r"^conversions$", r"achats"],
    "purch_click": [r"purchasesclick", r"^clickthroughpurchases$", r"purchasesclick1d", r"purchasesclick7d"],
    "purch_view":  [r"purchasesview", r"^viewthroughpurchases$", r"purchasesview1d"],
    "revenue":     [r"purchasesconversionvalue", r"conversionvalue", r"purchasevalue",
                    r"websitepurchasesconversionvalue", r"valeurdeconversion", r"^revenue$"],
    "impressions": [r"^impressions$", r"^impr$"],
    "clicks":      [r"^clicks$", r"linkclicks", r"^clicksall$"],
}

ORDERS_PATTERNS = {
    "order_id":  [r"^name$", r"^id$", r"^orderid$", r"^ordernumber$", r"^ordername$"],
    "created":   [r"^createdat$", r"^paidat$", r"^created$", r"^createdutc$", r"^date$", r"^processedat$"],
    "total":     [r"^total$", r"^amount$", r"^ordertotal$", r"^totalprice$", r"^grandtotal$"],
    "financial": [r"^financialstatus$", r"^status$", r"^paymentstatus$"],
    "refunded":  [r"refundedamount", r"amountrefunded", r"^refunded$", r"^refund$"],
    "currency":  [r"^currency$", r"^presentmentcurrency$"],
    "referring": [r"referringsite", r"^referrer$", r"^source$", r"^utmsource$", r"^landingsite$"],
    "email":     [r"^email$", r"^customeremail$"],
}

DATE_FORMATS = [
    "%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S %z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ",
    "%m/%d/%Y", "%d/%m/%Y", "%m/%d/%Y %H:%M:%S", "%d/%m/%Y %H:%M:%S",
    "%m/%d/%y", "%d/%m/%y", "%Y/%m/%d",
]

PAID_SOCIAL_REFERRER = re.compile(r"(facebook|instagram|fb\.|meta|l\.facebook|fbclid|ig\.)", re.I)


def normalize_header(header):
    """Lowercase and strip everything but alphanumerics, for fuzzy matching."""
    return re.sub(r"[^a-z0-9]", "", (header or "").lower())


def detect_columns(headers, patterns):
    """Map each logical field to the actual header that matches it first."""
    detected = {}
    normalized = [(original, normalize_header(original)) for original in headers]
    for field, field_patterns in patterns.items():
        for pattern in field_patterns:
            match = _first_matching_header(normalized, pattern)
            if match:
                detected[field] = match
                break
    return detected


def _first_matching_header(normalized_headers, pattern):
    for original, normalized in normalized_headers:
        if re.fullmatch(pattern, normalized) or re.search(pattern, normalized):
            return original
    return None


def read_csv_rows(path):
    """Read a CSV, tolerating byte-order marks and both comma and semicolon files."""
    with open(path, "r", encoding="utf-8-sig", newline="") as handle:
        sample = handle.read(8192)
        handle.seek(0)
        delimiter = ";" if sample.count(";") > sample.count(",") else ","
        rows = list(csv.DictReader(handle, delimiter=delimiter))
    if not rows:
        raise ValueError(f"{path} contains no data rows")
    return rows


def parse_number(raw):
    """Parse a number out of messy spreadsheet text such as '1,234.56' or '€1 234,56'."""
    if raw is None:
        return 0.0
    text = str(raw).strip()
    if not text or text in {"-", "--", "N/A", "n/a"}:
        return 0.0
    text = re.sub(r"[^\d,.\-]", "", text)
    if not text:
        return 0.0
    text = _resolve_decimal_separator(text)
    try:
        return float(text)
    except ValueError:
        return 0.0


def _resolve_decimal_separator(text):
    """Decide whether comma or period is the decimal mark, then normalize to period."""
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            return text.replace(".", "").replace(",", ".")
        return text.replace(",", "")
    if "," in text:
        # Ambiguous on its own: '1,234' is thousands, '1,23' is decimal.
        fragments = text.split(",")
        return text.replace(",", "." if len(fragments[-1]) <= 2 else "")
    return text


def parse_date(raw):
    """Parse a date from any format these exports commonly use, else return None."""
    if not raw:
        return None
    text = str(raw).strip()
    without_offset = re.sub(r"\s*[+-]\d{2}:?\d{2}$", "", text)
    for date_format in DATE_FORMATS:
        for candidate in (text, without_offset):
            try:
                return datetime.strptime(candidate, date_format)
            except ValueError:
                continue
    return _parse_iso_prefix(text)


def _parse_iso_prefix(text):
    match = re.match(r"(\d{4})-(\d{2})-(\d{2})", text)
    if match:
        return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    return None
