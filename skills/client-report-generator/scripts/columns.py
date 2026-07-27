#!/usr/bin/env python3
"""
Column detection and value parsing for messy real-world exports.

Ad and store exports vary wildly: different languages, different UI versions,
different encodings, a summary row at the bottom, a title preamble at the top,
and number/date formats that differ by locale. Rather than demanding one exact
format, this module reads defensively and, crucially, fails loudly and clearly
when it cannot trust the input. A tool that silently produces a wrong number is
worse than one that refuses, because the wrong number gets forwarded to a client.
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
                    r"websitepurchasesconversionvalue", r"valeurdeconversion", r"^revenue$",
                    r"^convvalue$", r"^conversionsvalue$", r"allconvvalue"],
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

# Slash-date parsing is split from ISO parsing so the day/month order can be
# decided once per column (see detect_day_first) instead of guessed per value.
ISO_DATE_FORMATS = [
    "%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S %z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y/%m/%d",
]
SLASH_DAY_FIRST = ["%d/%m/%Y", "%d/%m/%Y %H:%M:%S", "%d/%m/%y"]
SLASH_MONTH_FIRST = ["%m/%d/%Y", "%m/%d/%Y %H:%M:%S", "%m/%d/%y"]

PAID_SOCIAL_REFERRER = re.compile(r"(facebook|instagram|fb\.|meta|l\.facebook|fbclid|ig\.)", re.I)

# A row whose first meaningful cell is one of these is a summary line the export
# appended, not a campaign. Meta and Google both add one by default; counting it
# doubles every figure, and because ROAS is a ratio it survives the eyeball test.
TOTAL_ROW_MARKERS = re.compile(r"^(total|totals|grand ?total|total:.*|sum|resultats?|gesamt)$", re.I)


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


def is_total_row(row, columns):
    """True if this row is an appended summary line rather than real data.

    Checks the campaign/order identifier cell and, failing that, a row that has
    numbers but no label at all. Applied in the loaders so a Total row never
    inflates the figures.
    """
    label_field = columns.get("campaign") or columns.get("order_id") or columns.get("ad")
    if label_field:
        label = (row.get(label_field) or "").strip()
        if TOTAL_ROW_MARKERS.fullmatch(label):
            return True
    return False


# ---------------------------------------------------------------------------
# Reading: encoding, preamble, delimiter, and honest errors
# ---------------------------------------------------------------------------

def read_csv_rows(path):
    """Read a CSV defensively, or raise a message a non-technical user can act on."""
    text = _decode_file(path)
    lines = text.splitlines()
    if not any(line.strip() for line in lines):
        raise ValueError(f"{path} is empty.")
    delimiter = _sniff_delimiter(lines)
    header_index = _find_header_line(lines, delimiter)
    reader = csv.DictReader(lines[header_index:], delimiter=delimiter)
    rows = [row for row in reader]
    if not rows:
        raise ValueError(
            f"{path}: found the column headers but no data rows. The export may be "
            "filtered to an empty date range.")
    return rows


def _decode_file(path):
    """Detect the encoding from the leading bytes, or reject a non-CSV file clearly."""
    with open(path, "rb") as handle:
        head = handle.read(8)
        handle.seek(0)
        raw = handle.read()
    if head[:4] == b"PK\x03\x04":
        raise ValueError(
            f"{path} looks like an Excel .xlsx file, not a CSV. In Excel or Google "
            "Sheets, use File then Save As and choose CSV.")
    if head[:1] == b"<":
        raise ValueError(
            f"{path} looks like an HTML file, not a CSV. Re-export as CSV from the platform.")
    for bom, encoding in ((b"\xff\xfe", "utf-16"), (b"\xfe\xff", "utf-16"),
                          (b"\xef\xbb\xbf", "utf-8-sig")):
        if head.startswith(bom):
            return raw.decode(encoding, errors="replace")
    # Google Ads often exports UTF-16LE with no BOM: NUL bytes give it away.
    if raw[:200].count(b"\x00") > 20:
        return raw.decode("utf-16", errors="replace")
    return raw.decode("utf-8", errors="replace")


def _sniff_delimiter(lines):
    """Pick the delimiter from the busiest lines, covering comma, semicolon and tab."""
    sample = "\n".join(lines[:40])
    counts = {char: sample.count(char) for char in (",", ";", "\t")}
    best = max(counts, key=counts.get)
    return best if counts[best] else ","


def _find_header_line(lines, delimiter):
    """Skip a title/date-range preamble by starting at the first real header row.

    Google Ads prepends report-title lines before the header. The real header is
    the first line whose field count reaches the modal field count of the file,
    which the one-cell preamble lines never do.
    """
    field_counts = [line.count(delimiter) for line in lines]
    busy = [count for count in field_counts if count > 0]
    if not busy:
        return 0
    target = max(set(busy), key=busy.count)
    for index, count in enumerate(field_counts):
        if count >= target:
            return index
    return 0


# ---------------------------------------------------------------------------
# Number parsing
# ---------------------------------------------------------------------------

def parse_number(raw):
    """Parse a number from messy spreadsheet text such as '1,234.56' or '€1 234,56'."""
    if raw is None:
        return 0.0
    text = str(raw).strip()
    if not text or text in {"-", "--", "N/A", "n/a"}:
        return 0.0
    negative = text.startswith("(") and text.endswith(")")  # accounting negative
    cleaned = re.sub(r"[^\d,.\-]", "", text)
    if not cleaned:
        return 0.0
    cleaned = _resolve_decimal_separator(cleaned)
    try:
        value = float(cleaned)
    except ValueError:
        return 0.0
    return -value if negative and value > 0 else value


def _resolve_decimal_separator(text):  # craftsman-ignore: PY001
    # When both separators are present the rightmost one is the decimal mark.
    # When only one is present the same 3-digit-group heuristic decides decimal
    # versus thousands for comma and period alike; applying it to comma only (the
    # original bug) read a lone-period thousands value like "1.234" a thousandfold
    # too small.
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            return text.replace(".", "").replace(",", ".")
        return text.replace(",", "")
    for separator in (",", "."):
        if separator in text:
            return _resolve_single_separator(text, separator)
    return text


def _resolve_single_separator(text, separator):
    """A lone separator: decimal if it leaves a 1-2 digit tail, else a thousands mark."""
    fragments = text.replace("-", "").split(separator)
    looks_decimal = len(fragments) == 2 and 1 <= len(fragments[-1]) <= 2
    if looks_decimal:
        return text.replace(separator, ".")
    return text.replace(separator, "")


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------

def detect_day_first(values):
    """Decide a slash-date column's day/month order once, from the whole column.

    Returns True for day-first (dd/mm), False for month-first (mm/dd), or None
    when every value is ambiguous or ISO. Deciding once per column stops a single
    file from resolving some rows as d/m and others as m/d, which silently corrupts
    date overlap.
    """
    day_first_seen = month_first_seen = False
    for value in values:
        match = re.match(r"\s*(\d{1,2})/(\d{1,2})/", str(value or ""))
        if not match:
            continue
        first, second = int(match.group(1)), int(match.group(2))
        if first > 12:
            day_first_seen = True
        elif second > 12:
            month_first_seen = True
    if day_first_seen and not month_first_seen:
        return True
    if month_first_seen and not day_first_seen:
        return False
    return None


def parse_date(raw, day_first=None):
    """Parse a date, trying ISO first, then slash formats in the resolved order."""
    if not raw:
        return None
    text = str(raw).strip()
    without_offset = re.sub(r"\s*[+-]\d{2}:?\d{2}$", "", text)
    for date_format in ISO_DATE_FORMATS:
        parsed = _try_formats((text, without_offset), [date_format])
        if parsed:
            return parsed
    slash_formats = _slash_order(day_first)
    parsed = _try_formats((text, without_offset), slash_formats)
    if parsed:
        return parsed
    return _parse_iso_prefix(text)


def _slash_order(day_first):
    if day_first is True:
        return SLASH_DAY_FIRST + SLASH_MONTH_FIRST
    if day_first is False:
        return SLASH_MONTH_FIRST + SLASH_DAY_FIRST
    # Ambiguous: default to month-first (US), the dominant export locale, but the
    # column-level detection above resolves any file that has a >12 day in it.
    return SLASH_MONTH_FIRST + SLASH_DAY_FIRST


def _try_formats(candidates, formats):
    for date_format in formats:
        for candidate in candidates:
            try:
                return datetime.strptime(candidate, date_format)
            except ValueError:
                continue
    return None


def _parse_iso_prefix(text):
    match = re.match(r"(\d{4})-(\d{2})-(\d{2})", text)
    if match:
        return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    return None
