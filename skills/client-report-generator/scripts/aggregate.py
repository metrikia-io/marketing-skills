#!/usr/bin/env python3
"""
Aggregate ad exports by channel, this period against last, and pull out what moved.

The manual work this replaces is not making charts - Looker already does that. It
is the two things a person does by hand after the charts exist: comparing this
month to last and writing what changed and why. This module does the first half
(compute what moved); the model does the second (say what it means). Splitting it
that way is what keeps the numbers reproducible and the words adapted to them.

Usage:
    python aggregate.py --this meta_june.csv google_june.csv \\
        --last meta_may.csv google_may.csv \\
        --orders shopify_june.csv [--orders-last shopify_may.csv] \\
        [--out summary.json]
"""

import argparse
import json
import sys

from columns import ADS_PATTERNS, detect_columns, parse_number, read_csv_rows
from loaders import load_orders

# A change smaller than this is noise, not a story. Reported, never narrated.
MATERIAL_MOVE = 0.10


def channel_of(path):
    """Name the channel from the file, so one --this list can mix platforms."""
    name = path.lower()
    if "google" in name or "gads" in name or "adwords" in name:
        return "Google"
    if "tiktok" in name or "ttk" in name:
        return "TikTok"
    if "meta" in name or "facebook" in name or "fb" in name or "insta" in name:
        return "Meta"
    return "Other"


def load_channel(path):
    """Sum an ad export to channel totals. Day breakdown optional here: we want totals."""
    rows = read_csv_rows(path)
    columns = detect_columns(rows[0].keys(), ADS_PATTERNS)
    totals = {"spend": 0.0, "purchases": 0.0, "revenue": 0.0, "clicks": 0.0,
              "impressions": 0.0}
    for row in rows:
        totals["spend"] += _num(row, columns, "spend")
        totals["purchases"] += _num(row, columns, "purchases")
        totals["revenue"] += _num(row, columns, "revenue")
        totals["clicks"] += _num(row, columns, "clicks")
        totals["impressions"] += _num(row, columns, "impressions")
    return totals


def _num(row, columns, field):
    return parse_number(row.get(columns.get(field))) if field in columns else 0.0


def combine(paths):
    """Merge a list of ad exports into per-channel and total figures."""
    channels = {}
    for path in paths:
        name = channel_of(path)
        totals = load_channel(path)
        existing = channels.setdefault(name, {k: 0.0 for k in totals})
        for key, value in totals.items():
            existing[key] += value
    return channels


def derived(channel):
    """The ratios a media buyer reads first, computed once here so nothing drifts."""
    spend = channel["spend"]
    purchases = channel["purchases"]
    return {
        **channel,
        "roas": round(channel["revenue"] / spend, 2) if spend else None,
        "cpa": round(spend / purchases, 2) if purchases else None,
        "cpc": round(spend / channel["clicks"], 2) if channel["clicks"] else None,
    }


def delta(now, before):
    """Signed change and percentage, or None when there is nothing to compare to."""
    if before in (None, 0):
        return {"absolute": now, "pct": None, "material": now not in (None, 0)}
    if now is None:
        return {"absolute": None, "pct": None, "material": False}
    change = now - before
    pct = change / before
    return {"absolute": round(change, 2), "pct": round(pct, 4),
            "material": abs(pct) >= MATERIAL_MOVE}


def compare_channels(this_channels, last_channels):
    """Line up every channel present in either period and compute the moves."""
    names = sorted(set(this_channels) | set(last_channels))
    rows = []
    for name in names:
        now = derived(this_channels.get(name, _zero()))
        before = derived(last_channels.get(name, _zero())) if last_channels else None
        rows.append({
            "channel": name,
            "this": now,
            "last": before,
            "moves": _moves(now, before) if before else None,
        })
    return rows


def _zero():
    return {"spend": 0.0, "purchases": 0.0, "revenue": 0.0, "clicks": 0.0,
            "impressions": 0.0}


def _moves(now, before):
    return {metric: delta(now.get(metric), before.get(metric))
            for metric in ("spend", "purchases", "revenue", "roas", "cpa")}


def build_summary(args):
    """Assemble the full period-over-period picture the report is written from."""
    this_channels = combine(args.this)
    last_channels = combine(args.last) if args.last else {}
    orders = load_orders(args.orders) if args.orders else None
    orders_last = load_orders(args.orders_last) if args.orders_last else None

    totals_now = _sum_channels(this_channels)
    totals_before = _sum_channels(last_channels) if last_channels else None

    return {
        "period": {"label": args.label or "This period",
                   "compared_to": args.label_last or ("Last period" if last_channels else None)},
        "totals": {
            "this": derived(totals_now),
            "last": derived(totals_before) if totals_before else None,
            "moves": _moves(derived(totals_now), derived(totals_before)) if totals_before else None,
        },
        "channels": compare_channels(this_channels, last_channels),
        "store": _store_section(orders, orders_last),
        "headline_moves": _headline(compare_channels(this_channels, last_channels)),
    }


def _sum_channels(channels):
    total = _zero()
    for channel in channels.values():
        for key in total:
            total[key] += channel.get(key, 0.0)
    return total


def _store_section(orders, orders_last):
    if not orders:
        return None
    revenue = sum(day["revenue"] for day in orders["daily"].values())
    revenue_last = (sum(day["revenue"] for day in orders_last["daily"].values())
                    if orders_last else None)
    return {
        "orders": orders["unique_orders"] or sum(day["orders"] for day in orders["daily"].values()),
        "revenue": round(revenue, 2),
        "revenue_last": round(revenue_last, 2) if revenue_last is not None else None,
        "revenue_move": delta(revenue, revenue_last) if revenue_last is not None else None,
        "has_refund_data": orders["has_refund_data"],
    }


def _headline(channel_rows):
    """The two or three moves worth leading with: material, ranked by spend impact."""
    material = []
    for row in channel_rows:
        moves = row.get("moves")
        if not moves:
            continue
        for metric in ("spend", "roas", "purchases"):
            move = moves.get(metric, {})
            if move.get("material"):
                material.append({"channel": row["channel"], "metric": metric,
                                 "pct": move["pct"], "absolute": move["absolute"]})
    material.sort(key=lambda item: -abs(item.get("pct") or 0))
    return material[:4]


def parse_args():
    parser = argparse.ArgumentParser(description="Aggregate ad channels period over period.")
    parser.add_argument("--this", nargs="+", required=True,
                        help="Ad exports for the reporting period (any mix of platforms)")
    parser.add_argument("--last", nargs="+",
                        help="Ad exports for the comparison period")
    parser.add_argument("--orders", help="Store export for the reporting period")
    parser.add_argument("--orders-last", help="Store export for the comparison period")
    parser.add_argument("--label", help="Name of the reporting period, e.g. 'June 2026'")
    parser.add_argument("--label-last", help="Name of the comparison period")
    parser.add_argument("--out", help="Also write the JSON here")
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        summary = build_summary(args)
    except (ValueError, OSError, KeyError) as error:
        summary = {"error": type(error).__name__, "message": str(error)}
    rendered = json.dumps(summary, indent=2, ensure_ascii=False)
    print(rendered)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(rendered)
    return 1 if "error" in summary else 0


if __name__ == "__main__":
    sys.exit(main())
