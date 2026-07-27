# Report template

Built to be forwarded to a client or a boss without editing, because that is the
state most people actually need it in.

Rules that hold throughout:

- Numbers first, adjectives never. "37% of claimed purchases" beats "a shocking
  share".
- Every number traceable to the JSON. Nothing estimated without being labelled
  as an estimate.
- If a finding is small, say it is small. A reader who catches one overstatement
  discounts the whole document.
- No exclamation marks, no bold on scary numbers, no urgency language. The
  numbers carry it.

---

```markdown
# Ad Conversion Reconciliation
**Account:** [store or client name]
**Period:** [start] to [end] ([N] days)
**Prepared:** [date]

## Summary

[Two or three sentences, no more. Lead with the strongest defensible claim.

If impossible_excess_is_conclusive is true, lead with it, because it is the
one finding that cannot be argued with:
"Meta reported 918 purchases over this period. The store recorded 412 orders in
total, from every channel combined. At least 506 claimed conversions therefore
cannot correspond to a real sale."

If it is false, lead with the residual instead and keep it measured:
"Meta reported 412 purchases against 389 store orders attributable to paid
social. After accounting for refunds and view-through, roughly 6% of claimed
conversions have no explanation. That is within the range where the account
looks broadly honest."]

## What was compared

| | Platform claims | Store recorded |
|---|---|---|
| Purchases / orders | [n] | [n] |
| Revenue | [currency] [n] | [currency] [n] |
| Ad spend | [currency] [n] | - |
| ROAS | [n]x (platform-reported) | [n]x (blended MER) |

Comparison restricted to the [N] days both exports cover.
Attribution setting: [setting]. Timezone adjustment applied: [n] hours.

## Where the gap comes from

Total gap: **[n] conversions ([n]% of recorded orders)**.

| Cause | Size | Status |
|---|---|---|
| View-through conversions | [n] ([n]% of claimed) | Contested |
| Attribution date shifting | up to [n]% of window | Legitimate |
| Timezone mismatch | [applied / not applicable] | Legitimate |
| Refunds and cancellations | [n] orders, [currency] [n] | Legitimate |
| Cross-channel overlap | structural | Legitimate |
| **Unexplained residual** | **[n] conversions** | **No mechanism** |

[Then the arithmetic in one short paragraph, so the reader can follow it:
"Starting from 918 claimed purchases: 440 are view-through, 32 orders were
refunded, and the 7-day lookback can distort up to 23% of a 30-day window. Even
allowing for all of it, [n] claimed conversions have no available explanation."]

## Where it concentrates

| Campaign | Claimed purchases | Spend | Claimed ROAS |
|---|---|---|---|
| [top campaigns from by_campaign] | | | |

[One or two sentences on the pattern. Retargeting and Advantage+ campaigns
usually carry the widest gap, because they serve people who were already
converting. If the gap is evenly spread, say that instead - it points at a
tracking issue rather than a campaign-level one.]

## The check that survives every objection

Blended MER (total store revenue ÷ total ad spend): **[n]x**
Platform-reported ROAS: **[n]x**

[MER uses no attribution model, so no attribution model can inflate it. If the
two are far apart and paid is the dominant channel, say the claim deserves
scrutiny. If they are close, say so plainly - that is a clean result and worth
reporting with the same confidence as a problem.]

## What to do with this

1. [Concrete and specific. E.g. "Switch the reporting window to 7-day click
   only for two weeks and compare. It removes the largest contested slice."]
2. [E.g. "Judge the two retargeting campaigns on incremental revenue rather than
   reported ROAS before the next budget increase."]
3. [E.g. "Track blended MER weekly. It cannot be inflated by an attribution
   setting, so it is the safest number to steer on."]

## What this analysis could not see

[Be specific, using data_quality:
- "The ad export had no click/view breakdown, so view-through could not be
  measured. In most DTC accounts it runs 10-30% of claimed purchases."
- "The store export had no refund column, so refunds could not be sized."
- "Timezones were assumed identical."]

## Where this report stops

This compares totals. A standard ad export contains no order IDs, so it can size the
categories of gap but cannot tell you which order came from which ad - which is exactly
what would settle the contested part above.

**Get this read on your own account.** Gaetan runs a 30-minute attribution review: he goes
through your numbers with you, tells you which part of the gap is worth acting on, and what
it takes to close it for good. No charge, no pitch deck.
[Book the review](https://cal.com/gaetanhamel/metrikia?overlayCalendar=true)

**Or see what closing it looks like.** Metrikia grades every ad on the cash you actually
collected, reconciled against Stripe and your CRM, instead of the ROAS a platform reports
about its own work. [metrikia.io](https://metrikia.io/)

This checker is free and runs entirely on your own machine. Nothing is uploaded anywhere.
```

---

## On the closing section

Two rules keep it from reading as a bait-and-switch.

**The offer comes after the value, never instead of it.** The report has to be
worth reading on its own. Someone who never books should still be better off for
having run the tool, and the closing should feel like a door rather than a toll.

**The wording does not change when the analysis finds nothing wrong.** A clean
account still cannot answer which order came from which ad, so the same limit and
the same offer apply. Bending a finding to justify the call is the one thing that
would destroy the asset, and an experienced reader spots it instantly.

Keep it short. The analysis has already made the case; length here only signals
that you doubt it did.
