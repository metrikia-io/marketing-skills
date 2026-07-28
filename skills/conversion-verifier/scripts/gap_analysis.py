#!/usr/bin/env python3
"""
Gap classification.

A gap between what an ad platform claims and what a store recorded is normal.
Most of it has legitimate causes. A tool that subtracts two numbers and shouts
"the platform is lying" is wrong often enough to be worthless, and any
experienced buyer will dismiss it in seconds.

So the job here is not the subtraction. It is separating the part of the gap
that is explained from the part that is not. The unexplained residual is the
only number worth acting on.
"""

VIEW_THROUGH_TYPICAL_RANGE = "10-30%"


def build_findings(ads, orders, claimed, totals, context):
    """Return one entry per known cause of a gap, measured where the data allows."""
    return [
        _breakdown_inflation_finding(context, totals),
        _view_through_finding(ads, claimed, totals),
        _date_shift_finding(context),
        _timezone_finding(context),
        _refund_finding(orders, totals),
        _cross_channel_finding(orders, totals),
    ]


def _breakdown_inflation_finding(context, totals):
    """Summed breakdown rows overstate the platform's own deduplicated total.

    This is the trap that invalidates most homemade versions of this analysis.
    Meta documents it plainly: when a report is broken down by campaign, placement
    or time, one conversion can appear in more than one row, so adding the rows up
    produces a number the platform itself would never report. Building a headline
    finding on that sum means the whole analysis collapses the moment anyone opens
    Ads Manager and reads the real total.
    """
    row_sum = totals["purchases"]
    deduplicated = context.get("deduplicated_claimed")
    if deduplicated is None:
        return _unverified_row_sum(row_sum)
    return _verified_row_sum(row_sum, deduplicated)


def _unverified_row_sum(row_sum):
    return {
        "cause": "breakdown_sum_inflation",
        "legitimacy": "measurement_artifact",
        "measured": False,
        "blocks_conclusive_claim": True,
        "row_sum": round(row_sum, 2),
        "note": ("The claimed figure here is the sum of campaign-by-day rows, which overstates "
                 "the platform's own deduplicated total. Ask for the account-level Purchases "
                 "figure with no breakdown applied and pass it as --claimed-total. Until then "
                 "no over-attribution claim can be made, because part of this gap is a "
                 "reporting artifact rather than a real one."),
    }


def _verified_row_sum(row_sum, deduplicated):
    inflation = row_sum - deduplicated
    return {
        "cause": "breakdown_sum_inflation",
        "legitimacy": "measurement_artifact",
        "measured": True,
        "blocks_conclusive_claim": False,
        "row_sum": round(row_sum, 2),
        "deduplicated_total": round(deduplicated, 2),
        "inflation_units": round(inflation, 2),
        "inflation_share": round(inflation / row_sum, 4) if row_sum else None,
        "note": (f"Summed campaign rows exceed the account-level deduplicated total by "
                 f"{inflation:.0f} conversions. That difference is a reporting artifact, not "
                 "over-attribution. Every figure below uses the deduplicated total."),
    }


def _view_through_finding(ads, claimed, totals):
    """Conversions credited to people who never clicked. Contested, and often large."""
    if not ads["has_click_view_split"] or not claimed:
        return {
            "cause": "view_through",
            "legitimacy": "contested",
            "measured": False,
            "note": ("Not measurable from this export. Re-export with the 'Purchases (click)' "
                     "and 'Purchases (view)' breakdown to size it. In most DTC accounts "
                     f"view-through is {VIEW_THROUGH_TYPICAL_RANGE} of claimed purchases."),
        }
    return {
        "cause": "view_through",
        "legitimacy": "contested",
        "measured": True,
        "units": totals["view"],
        "share_of_claimed": round(totals["view"] / claimed, 4),
        "note": ("Credited to people who saw the ad but never clicked. Counted by default "
                 "under a 1-day view setting. A large share of these would have bought anyway."),
    }


def _date_shift_finding(context):
    """The platform stamps a conversion on the click date, not the purchase date."""
    return {
        "cause": "attribution_date_shift",
        "legitimacy": "legitimate",
        "measured": False,
        "estimated_max_share": round(context["edge_ratio"], 4),
        "note": (f"A conversion is reported on the day of the click, not the day of the purchase. "
                 f"With a {context['lookback_days']}-day lookback across a {context['window_days']}-day "
                 f"window, up to about {context['edge_ratio']:.0%} of this comparison can be distorted "
                 f"by orders falling outside the window. Longer windows shrink this."),
    }


def _timezone_finding(context):
    """Ad account and store rarely share a timezone; a full day can slide across."""
    shift = context["timezone_shift_hours"]
    return {
        "cause": "timezone_mismatch",
        "legitimacy": "legitimate",
        "measured": shift != 0,
        "applied_shift_hours": shift,
        "note": (f"A {shift}h shift was applied to order timestamps to match the ad account."
                 if shift else
                 "Ad account timezone versus store timezone. Can slide up to a full day of "
                 "orders across the window boundary. Pass --timezone-shift-hours to correct it."),
    }


def _refund_finding(orders, totals):
    """The purchase event fires once; the refund that follows is never sent back."""
    if not orders["has_refund_data"]:
        return {
            "cause": "refunds_and_cancellations",
            "legitimacy": "legitimate",
            "measured": False,
            "note": ("No refund or financial-status column in the orders export. "
                     "Re-export including it to size this."),
        }
    return {
        "cause": "refunds_and_cancellations",
        "legitimacy": "legitimate",
        "measured": True,
        "units": totals["refunded_orders"],
        "amount": round(totals["refunded_amount"], 2),
        "note": ("The platform counts the purchase event. Refunds happen later and are "
                 "never reported back, so claimed revenue stays inflated."),
    }


def _cross_channel_finding(orders, totals):
    """Store totals include every source, which makes them the friendliest denominator."""
    return {
        "cause": "cross_channel_overlap",
        "legitimacy": "structural",
        "measured": orders["has_referrer_data"],
        "referrer_paid_social_orders": (totals["referrer_paid_social"]
                                        if orders["has_referrer_data"] else None),
        "note": ("Store totals include organic, email, direct and every other source. "
                 "Comparing claimed purchases against the store TOTAL is therefore the most "
                 "generous possible benchmark for the platform, which is exactly why "
                 "exceeding it cannot be argued away."),
    }
