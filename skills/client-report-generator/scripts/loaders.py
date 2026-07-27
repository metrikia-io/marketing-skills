#!/usr/bin/env python3
"""
Loading and daily aggregation of ad-platform exports and store exports.

Both loaders collapse their input to a per-day summary. Days are the finest
grain an ad export reliably provides, so that is the grain the comparison uses.
"""

from collections import defaultdict
from datetime import timedelta

from columns import (
    ADS_PATTERNS,
    ORDERS_PATTERNS,
    PAID_SOCIAL_REFERRER,
    detect_columns,
    detect_day_first,
    is_total_row,
    parse_date,
    parse_number,
    read_csv_rows,
)

REFUNDED_STATUSES = {"refunded", "voided", "partially_refunded"}


def _empty_ads_day():
    return {"purchases": 0.0, "click": 0.0, "view": 0.0, "revenue": 0.0, "spend": 0.0}


def _empty_orders_day():
    return {"orders": 0.0, "revenue": 0.0, "refunded_amount": 0.0,
            "refunded_orders": 0.0, "referrer_paid_social": 0.0}


def load_ads(path):
    """Read an ad-platform export into per-day and per-campaign totals."""
    rows = read_csv_rows(path)
    columns = detect_columns(rows[0].keys(), ADS_PATTERNS)
    _require_ads_columns(columns, rows)

    has_split = ("purch_click" in columns) or ("purch_view" in columns)
    daily = defaultdict(_empty_ads_day)
    by_campaign = defaultdict(lambda: {"purchases": 0.0, "revenue": 0.0, "spend": 0.0,
                                       "click": 0.0, "view": 0.0})

    day_first = detect_day_first([row.get(columns.get("date")) for row in rows])
    for row in rows:
        _ingest_ad_row(row, columns, daily, by_campaign, day_first)

    return {
        "columns_detected": columns,
        "has_click_view_split": has_split,
        "daily": dict(daily),
        "by_campaign": dict(by_campaign),
        "row_count": len(rows),
    }


def _ingest_ad_row(row, columns, daily, by_campaign, day_first=None):
    """Fold one export row into the daily and per-campaign totals.

    A trailing Total row (Meta and Google add one by default) is skipped, because
    counting it doubles every figure and, since ROAS is a ratio, the doubling
    survives the eyeball test. The click/view split is carried to campaign level
    as well as daily, so the per-campaign chart shows real ratios not one average.
    """
    if is_total_row(row, columns):
        return
    parsed_date = parse_date(row.get(columns.get("date")), day_first)
    if not parsed_date:
        return
    metrics = _extract_ad_metrics(row, columns)
    _accumulate(daily[parsed_date.date().isoformat()], metrics)
    campaign = row.get(columns.get("campaign")) or "(unnamed)"
    _accumulate(by_campaign[campaign], metrics,
                keys=("purchases", "revenue", "spend", "click", "view"))


def _require_ads_columns(columns, rows):
    missing = [field for field in ("purchases", "date") if field not in columns]
    if "purchases" in missing and ("purch_click" in columns or "purch_view" in columns):
        missing.remove("purchases")
    if missing:
        raise ValueError(
            f"Ads export is missing required column(s): {missing}. "
            f"Detected: {columns}. Headers found: {list(rows[0].keys())}"
        )


def _extract_ad_metrics(row, columns):
    """Pull one row's numbers, deriving the purchase total when only the split exists."""
    click = parse_number(row.get(columns.get("purch_click"))) if "purch_click" in columns else 0.0
    view = parse_number(row.get(columns.get("purch_view"))) if "purch_view" in columns else 0.0
    if "purchases" in columns:
        purchases = parse_number(row.get(columns["purchases"]))
    else:
        purchases = click + view
    return {
        "purchases": purchases,
        "click": click,
        "view": view,
        "revenue": parse_number(row.get(columns.get("revenue"))) if "revenue" in columns else 0.0,
        "spend": parse_number(row.get(columns.get("spend"))) if "spend" in columns else 0.0,
    }


def _accumulate(target, metrics, keys=None):
    for key in (keys or metrics.keys()):
        target[key] = target.get(key, 0.0) + metrics.get(key, 0.0)


def load_orders(path, timezone_shift_hours=0):
    """Read a store export into per-day order counts, revenue and refund signals."""
    rows = read_csv_rows(path)
    columns = detect_columns(rows[0].keys(), ORDERS_PATTERNS)
    if "created" not in columns:
        raise ValueError(
            f"Orders export has no recognizable date column. Detected: {columns}. "
            f"Headers found: {list(rows[0].keys())}"
        )

    state = {"daily": defaultdict(_empty_orders_day), "seen_ids": set(),
             "has_refunds": False, "has_referrer": False, "currency": None,
             "counted_rows": 0}

    day_first = detect_day_first([row.get(columns["created"]) for row in rows])
    for row in rows:
        _ingest_order_row(row, columns, state, timezone_shift_hours, day_first)
    return _orders_result(columns, rows, state)


def _orders_result(columns, rows, state):
    return {
        "columns_detected": columns,
        "daily": dict(state["daily"]),
        "row_count": len(rows),
        "unique_orders": len(state["seen_ids"]) or None,
        "has_order_id": "order_id" in columns,
        "counted_rows": state["counted_rows"],
        "has_refund_data": state["has_refunds"],
        "has_referrer_data": state["has_referrer"],
        "currency": state["currency"],
    }


def _ingest_order_row(row, columns, state, timezone_shift_hours, day_first=None):
    if is_total_row(row, columns):
        return
    parsed_date = parse_date(row.get(columns["created"]), day_first)
    if not parsed_date:
        return
    if timezone_shift_hours:
        parsed_date = parsed_date + timedelta(hours=timezone_shift_hours)

    if _is_duplicate_line_item(row, columns, state["seen_ids"]):
        return

    bucket = state["daily"][parsed_date.date().isoformat()]
    total = parse_number(row.get(columns.get("total"))) if "total" in columns else 0.0
    bucket["orders"] += 1
    bucket["revenue"] += total
    state["counted_rows"] += 1

    if "currency" in columns and not state["currency"]:
        state["currency"] = (row.get(columns["currency"]) or "").strip() or None

    _record_refund(row, columns, bucket, state, total)
    _record_referrer(row, columns, bucket, state)


def _is_duplicate_line_item(row, columns, seen_ids):
    """Shopify emits one row per line item; keep only the first row of each order."""
    if "order_id" not in columns:
        return False
    order_id = row.get(columns["order_id"])
    if not order_id:
        return False
    if order_id in seen_ids:
        return True
    seen_ids.add(order_id)
    return False


def _record_refund(row, columns, bucket, state, order_total):
    explicit_amount = parse_number(row.get(columns["refunded"])) if "refunded" in columns else 0.0
    if explicit_amount:
        state["has_refunds"] = True
        bucket["refunded_amount"] += explicit_amount
        bucket["refunded_orders"] += 1
        return
    if "financial" not in columns:
        return
    status = (row.get(columns["financial"]) or "").strip().lower()
    if status in REFUNDED_STATUSES:
        state["has_refunds"] = True
        bucket["refunded_orders"] += 1
        bucket["refunded_amount"] += order_total


def _record_referrer(row, columns, bucket, state):
    if "referring" not in columns:
        return
    referrer = (row.get(columns["referring"]) or "").strip()
    if not referrer:
        return
    state["has_referrer"] = True
    if PAID_SOCIAL_REFERRER.search(referrer):
        bucket["referrer_paid_social"] += 1
