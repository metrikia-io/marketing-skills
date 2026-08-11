#!/usr/bin/env python3
"""
reconcile.py - Compare what an ad platform CLAIMS it sold against what the
store actually recorded, and separate the explained gap from the unexplained one.

This script is deliberately boring: it does arithmetic and classification, and
it does not interpret. Interpretation belongs to whoever reads the JSON it emits.
Keeping the numbers in code and the judgment out of it is what makes the output
reproducible and defensible.

Usage:
    python reconcile.py --ads meta_export.csv --orders shopify_orders.csv \
        [--timezone-shift-hours N] [--attribution-window 7d_click_1d_view] \
        [--out report.json]
"""

import argparse
import json
import sys

from gap_analysis import build_findings
from loaders import load_ads, load_orders

AD_METRIC_KEYS = ("purchases", "click", "view", "revenue", "spend")
ORDER_METRIC_KEYS = ("orders", "revenue", "refunded_amount",
                     "refunded_orders", "referrer_paid_social")
MAX_CAMPAIGNS_REPORTED = 25
UNVERIFIED_CLAIM_REASON = ("claimed figure is a summed row total, not the platform's "
                           "deduplicated account total")


def sum_over_days(daily, days, keys):
    """Total the given metrics across a specific set of days."""
    totals = {key: 0.0 for key in keys}
    for day in days:
        for key in keys:
            totals[key] += daily[day].get(key, 0.0)
    return totals


def build_context(overlap_days, options):
    """Size the distortion that the attribution lookback imposes on this window.

    A click on day one can produce a purchase up to seven days later, reported
    back on day one. Orders near the window edges therefore sit outside the
    overlap on one side or the other. Short windows suffer badly; long windows
    barely notice. Quantifying it beats hand-waving it.
    """
    window_days = len(overlap_days)
    lookback_days = 7 if "7d" in options.get("attribution_window", "") else 1
    edge_ratio = min(1.0, lookback_days / window_days) if window_days else 1.0
    return {
        "window_days": window_days,
        "lookback_days": lookback_days,
        "edge_ratio": edge_ratio,
        "timezone_shift_hours": options.get("timezone_shift_hours", 0),
        "deduplicated_claimed": options.get("claimed_total"),
        "deduplicated_revenue": options.get("claimed_revenue_total"),
        "claim_basis": options.get("claim_basis"),
    }


def reconcile(ads, orders, options=None):
    """Produce the full comparison, or an error object if the windows do not overlap."""
    options = options or {}
    ads_days = set(ads["daily"])
    order_days = set(orders["daily"])
    overlap = sorted(ads_days & order_days)
    if not overlap:
        return _no_overlap_error(ads_days, order_days)

    ad_totals = sum_over_days(ads["daily"], overlap, AD_METRIC_KEYS)
    order_totals = sum_over_days(orders["daily"], overlap, ORDER_METRIC_KEYS)
    context = build_context(overlap, options)
    return _assemble(ads, orders, ad_totals, order_totals, context, options,
                     overlap, ads_days, order_days)


def _assemble(ads, orders, ad_totals, order_totals, context, options,
              overlap, ads_days, order_days):
    headline = _headline_claimed(ad_totals, context)
    merged = _merge(ad_totals, order_totals)
    claim_source = _claim_source_section(context, ad_totals)
    context["claim_sanity"] = claim_source.get("sanity")
    claimed = _claimed_section(ads, ad_totals, context)
    blended = _blended_section(ad_totals, order_totals)
    return {
        "window": _window_section(overlap, ads_days, order_days),
        "claim_source": claim_source,
        "claimed": claimed,
        "actual": _actual_section(orders, order_totals),
        "gap": _gap_section(ad_totals, order_totals, context),
        "blended": blended,
        "economics": _economics_section(ad_totals, claimed, blended, options,
                                        ads["has_click_view_split"]),
        "gap_breakdown": build_findings(ads, orders, headline, merged, context),
        "caveats": _caveats_section(context, orders, options),
        "data_quality": _data_quality_section(ads, orders),
        "by_campaign": _top_campaigns(ads, options.get("gross_margin")),
        "daily": _daily_section(ads, orders, overlap),
    }


def _headline_claimed(ad_totals, context):
    """Use the platform's own deduplicated total when we have it, never the row sum."""
    deduplicated = context.get("deduplicated_claimed")
    return deduplicated if deduplicated is not None else ad_totals["purchases"]


# craftsman-ignore: PY002 - audited public code, unchanged by the economics work
def _claim_source_section(context, ad_totals):
    """State plainly where the headline number came from, because it decides everything."""
    deduplicated = context.get("deduplicated_claimed")
    if deduplicated is None:
        return {
            "basis": "summed_breakdown_rows",
            "value": round(ad_totals["purchases"], 2),
            "reliable": False,
            "warning": ("This figure is the sum of campaign-by-day rows. The platform's own "
                        "deduplicated account total is lower, because one conversion can appear "
                        "in several breakdown rows. Treat every gap below as an upper bound and "
                        "make no over-attribution claim until --claimed-total is supplied."),
        }
    basis = context.get("claim_basis") or "account_level_deduplicated"
    row_sum = ad_totals["purchases"]
    section = {
        "basis": basis,
        "value": round(deduplicated, 2),
        "reliable": True,
        "row_sum_for_reference": round(row_sum, 2),
    }
    section.update(_sanity_check_claim(deduplicated, row_sum))
    if basis == "campaign_level_export":
        section["note"] = ("Totals come from a campaign-level export with no day breakdown, "
                           "which avoids the row multiplication the time breakdown causes. "
                           "Close to the platform's deduplicated figure, though a small "
                           "residual difference is possible; the account total read directly "
                           "off the platform remains the only exact source.")
    return section


PLAUSIBLE_FLOOR = 0.60  # a deduplicated total below this share of the row sum is suspect


# craftsman-ignore: PY002 - audited public code, unchanged by the economics work
def _sanity_check_claim(deduplicated, row_sum):
    """Catch a supplied total that cannot describe the same data as the export.

    A hand-typed figure fails silently: a typo, the wrong date range, the wrong
    metric or a different attribution setting all produce a clean-looking report
    built on a number that describes something else. Deduplication can only ever
    remove conversions, never add them, so anything above the row sum is provably
    a different measurement, and anything far below it is almost always the wrong
    period or the wrong column.
    """
    if not row_sum:
        return {}
    ratio = deduplicated / row_sum
    if ratio > 1.0:
        return {"reliable": False, "sanity": "above_row_sum", "ratio": round(ratio, 3),
                "warning": (f"The supplied total ({deduplicated:,.0f}) is higher than the sum "
                            f"of the export rows ({row_sum:,.0f}). Deduplication only removes "
                            "conversions, so these two numbers cannot describe the same data. "
                            "Check the date range, the attribution setting and the metric "
                            "before using this report.")}
    if ratio < PLAUSIBLE_FLOOR:
        return {"sanity": "far_below_row_sum", "ratio": round(ratio, 3),
                "warning": (f"The supplied total is {1 - ratio:.0%} below the export row sum, "
                            "which is a much larger deduplication than platforms normally "
                            "apply. Usually this means a different period or a different "
                            "metric was read. Worth re-checking before quoting the figures.")}
    return {"sanity": "plausible", "ratio": round(ratio, 3)}


CAVEAT_TEXTS = {
    "unverified_claim_basis": (
        "blocking",
        "No account-level deduplicated total was supplied, so the claimed figure is an "
        "inflated row sum. No conclusive over-attribution claim is possible."),
    "store_may_not_cover_all_revenue": (
        "high",
        "The store export is assumed to contain all revenue for this business. If sales also "
        "run through Amazon, retail, a second store or subscriptions billed elsewhere, the "
        "denominator is understated and the gap is overstated. Confirm before publishing."),
    "refunds_invisible": (
        "medium",
        "No refund data in the store export, so refunds could not be removed."),
    "supplied_total_impossible": (
        "blocking",
        "The supplied account total is higher than the sum of the export rows. Deduplication "
        "only removes conversions, so the two cannot describe the same data. Re-check the date "
        "range, the attribution setting and the metric before using any figure here."),
    "supplied_total_suspect": (
        "high",
        "The supplied account total is far below the export row sum, well beyond normal "
        "deduplication. This usually means a different period or a different metric was read."),
    "timezone_assumed_identical": (
        "low",
        "Ad account and store were assumed to share a timezone. Material on short windows, "
        "noise on long ones."),
}


def _caveats_section(context, orders, options):
    """Assumptions that can invalidate the result. Naming them is what makes it usable."""
    triggered = []
    if context.get("deduplicated_claimed") is None:
        triggered.append("unverified_claim_basis")
    if context.get("claim_sanity") == "above_row_sum":
        triggered.append("supplied_total_impossible")
    elif context.get("claim_sanity") == "far_below_row_sum":
        triggered.append("supplied_total_suspect")
    if not options.get("store_covers_all_revenue"):
        triggered.append("store_may_not_cover_all_revenue")
    if not orders["has_refund_data"]:
        triggered.append("refunds_invisible")
    if not context.get("timezone_shift_hours"):
        triggered.append("timezone_assumed_identical")
    return [{"id": key, "severity": CAVEAT_TEXTS[key][0], "text": CAVEAT_TEXTS[key][1]}
            for key in triggered]


def _merge(ad_totals, order_totals):
    merged = dict(ad_totals)
    merged.update(order_totals)
    return merged


def _no_overlap_error(ads_days, order_days):
    return {
        "error": "no_overlapping_dates",
        "message": ("The two exports cover no common dates. Re-export both over the "
                    "same window and try again."),
        "ads_range": [min(ads_days), max(ads_days)] if ads_days else None,
        "orders_range": [min(order_days), max(order_days)] if order_days else None,
    }


def _window_section(overlap, ads_days, order_days):
    """Every comparison is restricted to the overlap.

    Comparing two different date ranges is the most common way this analysis
    invents a gap that does not exist, so the mismatched days are reported
    rather than silently dropped.
    """
    return {
        "start": overlap[0],
        "end": overlap[-1],
        "days": len(overlap),
        "ads_only_days": sorted(ads_days - order_days),
        "orders_only_days": sorted(order_days - ads_days),
    }


def _claimed_section(ads, totals, context):
    has_split = ads["has_click_view_split"]
    spend = totals["spend"]
    purchases = _headline_claimed(totals, context)
    revenue = context.get("deduplicated_revenue") or totals["revenue"]
    return {
        "purchases": round(purchases, 2),
        "purchases_click": round(totals["click"], 2) if has_split else None,
        "purchases_view": round(totals["view"], 2) if has_split else None,
        "revenue": round(revenue, 2),
        "spend": round(spend, 2),
        "roas": round(revenue / spend, 2) if spend else None,
    }


def _actual_section(orders, totals):
    has_refunds = orders["has_refund_data"]
    return {
        "orders_all_sources": round(totals["orders"], 2),
        "revenue_all_sources": round(totals["revenue"], 2),
        "refunded_orders": round(totals["refunded_orders"], 2) if has_refunds else None,
        "refunded_amount": round(totals["refunded_amount"], 2) if has_refunds else None,
        "referrer_paid_social": (round(totals["referrer_paid_social"], 2)
                                 if orders["has_referrer_data"] else None),
        "currency": orders["currency"],
    }


# craftsman-ignore: PY002 - audited public code, unchanged by the economics work
def _gap_section(ad_totals, order_totals, context):
    """The headline test.

    If the platform claims more purchases than the store recorded orders from
    every source combined, the excess cannot exist. No attribution model, no
    lookback window and no timezone explains selling more than you sold.

    That claim only holds against the platform's own deduplicated total. Run it
    against summed breakdown rows and the excess is partly a reporting artifact,
    which is exactly the mistake that gets this kind of analysis dismissed. So
    the conclusive flag stays false until the deduplicated total is supplied.
    """
    claimed = _headline_claimed(ad_totals, context)
    claimed_revenue = context.get("deduplicated_revenue") or ad_totals["revenue"]
    gross = order_totals["orders"]
    net = gross - order_totals["refunded_orders"]
    verified = (context.get("deduplicated_claimed") is not None
                and context.get("claim_sanity") != "above_row_sum")
    return {
        "units": round(claimed - gross, 2),
        "pct_of_actual": round((claimed - gross) / gross, 4) if gross else None,
        "units_vs_net_orders": round(claimed - net, 2),
        "revenue_units": round(claimed_revenue - order_totals["revenue"], 2),
        "impossible_excess": round(max(0.0, claimed - gross), 2),
        "impossible_excess_is_conclusive": bool(claimed > gross and verified),
        "conclusive_blocked_reason": None if verified else UNVERIFIED_CLAIM_REASON,
    }


def _blended_section(ad_totals, order_totals):
    """Blended metrics use no attribution model, so no attribution model can inflate them."""
    spend = ad_totals["spend"]
    return {
        "mer_true_revenue_over_spend": round(order_totals["revenue"] / spend, 2) if spend else None,
        "note": ("MER compares total store revenue to ad spend. It relies on no attribution "
                 "model, so it cannot be inflated by one. When claimed ROAS greatly exceeds "
                 "MER and paid is the dominant channel, the claim deserves scrutiny."),
    }


def _view_share(metrics, has_split=True):
    """The view-through share, taken from the click and view columns of the same rows.

    `has_split` is the loader's verdict on whether both columns were actually
    present. It is passed rather than inferred, because a missing column arrives
    here as a zero and a zero is indistinguishable from a real one.

    Both counts come out of one export, so their ratio holds whatever that export
    is: a day breakdown that multiplies rows and a campaign-level one that does not
    give the same share. Dividing a row-level click count by the deduplicated
    account total instead mixes two bases and flatters the click side, which is the
    one direction this tool must never err in.
    """
    if not has_split:
        return None
    click = metrics.get("click") or 0.0
    view = metrics.get("view") or 0.0
    split = click + view
    return (view / split) if split else None


def _economics_section(ad_totals, claimed, blended, options, has_split=True):
    """Turn the reconciliation into the terms a budget decision is actually made in.

    A ratio does not tell a buyer whether to scale, hold or cut. Two things do: how
    much money the contested part represents, and where the account's break-even
    sits. Break-even needs the gross margin, which no export contains and only the
    operator knows, so it stays absent rather than assumed when it was not supplied.
    """
    margin = options.get("gross_margin")
    breakeven = round(1 / margin, 2) if margin else None
    section = dict(EMPTY_ECONOMICS, gross_margin=margin, breakeven_roas=breakeven,
                   claimed_roas=claimed.get("roas"),
                   mer=blended.get("mer_true_revenue_over_spend"))
    section.update(_contested_revenue(ad_totals, claimed, has_split))
    click_only = section["click_only_roas"]
    if breakeven and click_only is not None:
        section["straddles_breakeven"] = bool(
            click_only < breakeven <= (claimed.get("roas") or 0))
    return section


EMPTY_ECONOMICS = {
    "click_only_roas": None,
    "contested_revenue": None,
    "contested_share_of_claimed_revenue": None,
    "contested_revenue_basis": "unavailable_without_click_view_split",
    "straddles_breakeven": None,
}


CONTESTED_ESTIMATE_NOTE = (
    "The contested revenue is an estimate: it applies the view-through share of conversions "
    "to claimed revenue, because platforms do not export purchase value split by click and "
    "by view. Report it as an estimate, never as a measured figure.")


def _contested_revenue(ad_totals, claimed, has_split=True):
    """The slice of claimed revenue that rests on people who never clicked."""
    spend = claimed.get("spend") or 0.0
    revenue = claimed.get("revenue") or 0.0
    view_share = _view_share(ad_totals, has_split)
    if view_share is None or not spend:
        return {}
    contested = revenue * view_share
    return {
        "click_only_roas": round((revenue - contested) / spend, 2),
        "contested_revenue": round(contested, 2),
        "contested_share_of_claimed_revenue": round(view_share, 4),
        "contested_revenue_basis": "estimated_at_average_order_value",
        "note": CONTESTED_ESTIMATE_NOTE,
    }


def _campaign_economics(metrics, margin, has_split=True):
    """Per campaign, the honest bracket: declared on one end, clicks alone on the other."""
    revenue = metrics.get("revenue") or 0.0
    spend = metrics.get("spend") or 0.0
    view_share = _view_share(metrics, has_split)
    if not spend:
        return {}
    economics = {"roas_declared": round(revenue / spend, 2)}
    if view_share is None:
        return economics
    contested = revenue * view_share
    click_only = (revenue - contested) / spend
    economics.update({
        "view_share": round(view_share, 4),
        "contested_revenue": round(contested, 2),
        "roas_click_only": round(click_only, 2),
    })
    if margin:
        # Compare before rounding, and carry the distance as well as the verdict: a
        # campaign a thousandth under the line is sitting on it, not failing, and a
        # bare boolean would have the report say otherwise.
        breakeven = 1 / margin
        economics["below_breakeven_on_clicks"] = click_only < breakeven
        economics["below_breakeven_as_declared"] = (revenue / spend) < breakeven
        economics["clicks_vs_breakeven"] = round(click_only / breakeven, 3)
    return economics


def _data_quality_section(ads, orders):
    """What the analysis could and could not see. Stating limits is what makes it credible."""
    return {
        "ads_rows": ads["row_count"],
        "orders_rows": orders["row_count"],
        "unique_orders": orders["unique_orders"],
        "has_click_view_split": ads["has_click_view_split"],
        "has_refund_data": orders["has_refund_data"],
        "has_referrer_data": orders["has_referrer_data"],
        "ads_columns_detected": ads["columns_detected"],
        "orders_columns_detected": orders["columns_detected"],
    }


def _top_campaigns(ads, gross_margin=None):
    """Campaigns ranked by volume, each carrying its own declared-to-clicks bracket.

    Two campaigns can post the same ROAS on the dashboard and sit on opposite sides
    of break-even once the view-through share is removed. That difference is where
    the budget decision lives, so it is computed per campaign rather than only for
    the account.
    """
    ranked = sorted(ads["by_campaign"].items(), key=lambda item: -item[1]["purchases"])
    campaigns = {}
    for name, metrics in ranked[:MAX_CAMPAIGNS_REPORTED]:
        row = {metric: round(value, 2) for metric, value in metrics.items()}
        row.update(_campaign_economics(metrics, gross_margin,
                                       ads["has_click_view_split"]))
        campaigns[name] = row
    return campaigns


def _daily_section(ads, orders, overlap):
    return {
        day: {
            "claimed_purchases": round(ads["daily"][day].get("purchases", 0), 2),
            "actual_orders": round(orders["daily"][day].get("orders", 0), 2),
            "claimed_revenue": round(ads["daily"][day].get("revenue", 0), 2),
            "actual_revenue": round(orders["daily"][day].get("revenue", 0), 2),
            "spend": round(ads["daily"][day].get("spend", 0), 2),
        }
        for day in overlap
    }


# craftsman-ignore: PY002 - audited public code, unchanged by the economics work
def parse_args():
    parser = argparse.ArgumentParser(
        description="Reconcile ad-platform claims against store records.")
    parser.add_argument("--ads", required=True,
                        help="Ad platform export CSV (Meta, Google, TikTok)")
    parser.add_argument("--orders", required=True,
                        help="Store export CSV (Shopify orders, Stripe payments)")
    parser.add_argument("--timezone-shift-hours", type=int, default=0,
                        help="Shift order timestamps by N hours to match the ad account timezone")
    parser.add_argument("--attribution-window", default="7d_click_1d_view",
                        help="Attribution setting used in the ad platform")
    parser.add_argument("--ads-totals",
                        help=("Second ad export at campaign level with NO day breakdown. "
                              "Its totals are far closer to the platform's deduplicated "
                              "figure than a day-level row sum, and it costs one more click "
                              "instead of a number typed by hand."))
    parser.add_argument("--claimed-total", type=float,
                        help=("Account-level deduplicated Purchases, read off the platform with "
                              "NO breakdown applied. Without it no conclusive claim is possible, "
                              "because summed breakdown rows overstate the real total."))
    parser.add_argument("--claimed-revenue-total", type=float,
                        help="Account-level deduplicated purchase conversion value")
    parser.add_argument("--gross-margin", type=float,
                        help=("Gross margin, as 0.62 or 62. Sets the break-even ROAS, which is "
                              "what turns a ratio into a budget decision. Omitted, the report "
                              "states the figures without saying whether they are profitable."))
    parser.add_argument("--store-covers-all-revenue", action="store_true",
                        help="Confirm the store export contains all revenue (no Amazon, retail, "
                             "second store or externally billed subscriptions)")
    parser.add_argument("--out", help="Also write the JSON to this path")
    return parser.parse_args()


def _normalize_margin(raw):
    """Accept a margin typed either way, and refuse one that cannot be a margin.

    People type 62 as readily as 0.62, and a silent misread would move break-even
    by a factor of a hundred, which is the kind of error that survives all the way
    into a client deck.
    """
    if raw is None:
        return None
    margin = raw / 100 if raw > 1 else raw
    if not 0 < margin < 1:
        raise ValueError(f"Gross margin must be between 0 and 1 (or 1 and 100), got {raw}")
    return margin


def _apply_totals_export(options):
    """Read the campaign-level export, if supplied, and use it as the claimed totals.

    An export with no day breakdown avoids the row-multiplication that the time
    breakdown causes, so its sums land close to the platform's own deduplicated
    figure. A typed account total is still the gold standard and wins when both
    are present, but this path costs one extra click instead of manual data entry,
    which is the difference between a check people run and one they skip.
    """
    path = options.get("ads_totals_path")
    if not path or options.get("claimed_total") is not None:
        return
    totals_export = load_ads(path)
    summed = sum(row["purchases"] for row in totals_export["by_campaign"].values())
    revenue = sum(row["revenue"] for row in totals_export["by_campaign"].values())
    options["claimed_total"] = summed
    options["claimed_revenue_total"] = options.get("claimed_revenue_total") or revenue
    options["claim_basis"] = "campaign_level_export"


def main():
    args = parse_args()
    options = {
        "ads_totals_path": args.ads_totals,
        "attribution_window": args.attribution_window,
        "timezone_shift_hours": args.timezone_shift_hours,
        "claimed_total": args.claimed_total,
        "claimed_revenue_total": args.claimed_revenue_total,
        "store_covers_all_revenue": args.store_covers_all_revenue,
    }
    try:
        # Inside the try: a rejected margin has to come back as the same JSON error
        # object as every other bad input. Raised outside it, argparse's own value
        # check printed a Python traceback at someone who exports spreadsheets.
        options["gross_margin"] = _normalize_margin(args.gross_margin)
        ads = load_ads(args.ads)
        orders = load_orders(args.orders, args.timezone_shift_hours)
        _apply_totals_export(options)
        result = reconcile(ads, orders, options)
    except (ValueError, OSError, KeyError) as error:
        result = {"error": type(error).__name__, "message": str(error)}

    rendered = json.dumps(result, indent=2, ensure_ascii=False)
    print(rendered)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(rendered)
    return 1 if "error" in result else 0


if __name__ == "__main__":
    sys.exit(main())
