---
name: attribution-model-analysis
description: Compare and interpret multi-touch attribution models (first-touch, last-touch, linear, time-decay, U-shaped, W-shaped, and position-based variants) on campaign and conversion data. Use when analyzing which channels or campaigns drive conversions, when last-click numbers look suspicious, or when choosing an attribution model for reporting.
license: MIT
---

# Attribution Model Analysis

This skill turns a raw touchpoint log into a defensible read of which channels
actually contribute to conversions, by computing several attribution models
side by side and interpreting the differences between them.

## When to use this skill

Reach for it in these situations:

- **Channel credit disputes.** Paid social claims the conversions, paid search
  claims the same conversions, and the sum of platform-reported conversions is
  larger than the number of orders or deals that actually closed.
- **Last-click looks suspicious.** Branded search, direct, and email absorb
  almost all credit, while the channels that generate demand show a poor return.
  That is the classic signature of a single-touch model, not a real result.
- **Choosing a reporting model.** The team needs one model for the monthly
  dashboard and has to justify the choice to finance or to a client.
- **Sanity-checking platform ROAS.** Each ad platform reports on its own
  attribution rules and lookback window. A neutral, path-based recomputation
  tells you how much of that reported return is shared with other channels.
- **Diagnosing a funnel shape.** You want to know which channels introduce new
  buyers and which ones close them, before deciding where incremental budget
  goes.

Do not use it to prove that a channel caused revenue. See the guardrails.

## Input data expected

The ideal input is a **touchpoint log**: one row per marketing interaction that
can be tied to a converting entity. Minimum columns:

| Column | Meaning |
| --- | --- |
| `conversion_id` (or `lead_id`, `order_id`, `deal_id`) | The identifier that groups touchpoints into one path |
| `timestamp` | When the touchpoint happened, ISO 8601, single timezone |
| `channel` | Grouping level for reporting (Paid Social, Paid Search, Email, Organic, Direct, Referral) |
| `campaign` (optional) | Finer grain for the same analysis |
| `conversion_value` | Revenue or deal value of the conversion, repeated on each row of the path or supplied in a separate conversions table |
| `converted_at` (optional) | Conversion timestamp, used to enforce the lookback window |

CSV, TSV, spreadsheet export, or a query result all work. One file with all
touchpoints plus one file with conversions and values also works: join on the
conversion identifier.

**If only aggregate platform reports are available**, say so explicitly in the
output and stay honest about the limits. With per-channel spend, clicks, and
platform-reported conversions you can still:

- compare each platform's reported conversions against the true total from the
  order or CRM system, and quantify the overlap (the gap is double counting),
- compute blended efficiency: total revenue divided by total spend across all
  channels, which is immune to attribution disputes,
- rank channels by cost per reported conversion for a rough triage.

You cannot compute first-touch, linear, time-decay, or any positional model
without path-level data. Do not fabricate paths from aggregates. State the
missing input and describe what export would unlock the full analysis.

## The models

Notation: a path is an ordered list of touchpoints `t1, t2, ..., tn` for one
conversion of value `V`. Every model distributes exactly `V` across the path,
so credit shares always sum to 1.

### First-touch

All credit goes to `t1`. Share: `1.0` for the first touchpoint, `0` for the
rest.

*Ideal use case*: understanding demand generation and discovery. Answers "what
brought this person into the market for us?" Useful for prospecting budget
decisions and for measuring top-of-funnel channels that will never appear in a
last-click report.

*Bias*: ignores everything that happened after discovery, so it flatters
awareness channels and makes nurture, retargeting, and sales-assist channels
look worthless. It also over-rewards whichever channel happens to be cheapest at
reaching cold audiences, regardless of the quality of the traffic.

### Last-touch

All credit goes to `tn`. Share: `1.0` for the last touchpoint, `0` for the rest.
This is the default in most analytics tools, usually as "last non-direct click",
which skips direct visits when assigning the final credit.

*Ideal use case*: short, impulse-driven purchase cycles with one or two
touchpoints, and quick operational decisions where you need a stable, cheap,
universally understood number.

*Bias*: systematically over-credits the bottom of the funnel: branded search,
email, retargeting, direct. It creates a self-reinforcing loop where budget
moves to channels that harvest existing demand, demand generation is cut, and
the harvesting channels quietly decay a quarter later.

### Linear

Every touchpoint receives the same share: `1/n` each.

*Ideal use case*: long, consultative cycles with many meaningful interactions,
and as a neutral baseline when nobody can agree on a weighting. It is the model
that assumes the least about the funnel.

*Bias*: treats a passive impression and a high-intent demo request as equally
valuable. Channels that fire often per path (email, retargeting, organic) gain
credit purely through frequency, so path length becomes a hidden weighting
factor.

### Time-decay

Credit increases the closer a touchpoint is to the conversion, following an
exponential decay controlled by a **half-life**: a touchpoint that happened one
half-life before the conversion gets half the weight of one that happened at the
moment of conversion. Raw weight for touchpoint `i`:

```
w_i = 0.5 ^ (age_i / half_life)
```

where `age_i` is the elapsed time between `t_i` and the conversion, expressed in
the same unit as the half-life. Normalize: `share_i = w_i / sum(w)`. A 7-day
half-life suits short cycles, 30 days suits considered purchases, 45 to 90 days
suits enterprise sales.

*Ideal use case*: cycles where recency genuinely reflects intent, and
retargeting or nurture sequences that build toward a decision.

*Bias*: a softer last-touch. It structurally penalizes the first contact, which
is the one that had no predecessor to rely on. The half-life is a judgment call
that changes the ranking, so it must be declared alongside any result.

### U-shaped (position-based, 40/20/40)

The first and last touchpoints get 40% each. The remaining 20% is split equally
among the middle touchpoints. Degenerate cases: a single-touch path gives 100%
to that touchpoint, a two-touch path gives 50/50 (there is no middle to fund).

*Ideal use case*: businesses where discovery and the closing moment are both
clearly decisive, and the middle is real but supporting. It is the most common
compromise model for lead generation.

*Bias*: the 40/20/40 split is a convention, not a measurement. Long paths dilute
the middle to near zero, so a nurture-heavy funnel with ten touchpoints will look
like a two-touch funnel.

### W-shaped (30/30/30/10)

An extension of U-shaped for funnels with a named milestone in the middle, such
as lead creation, demo booked, or opportunity created. The first touchpoint, the
touchpoint at the milestone, and the last touchpoint get 30% each. The remaining
10% is split equally among all other touchpoints. If a path has no milestone
touchpoint, fall back to U-shaped and record the fallback.

*Ideal use case*: B2B and high-ticket funnels with a real qualification stage,
where the interaction that produced the qualified opportunity deserves explicit
credit.

*Bias*: requires a reliable milestone flag. If the milestone is mislabeled or
missing on part of the dataset, the model quietly becomes inconsistent across
paths. It also assumes exactly one milestone per path.

### Other position-based variants

Any `(a, b, c)` split with `a + b + c = 1` follows the same rule as U-shaped:
`a` to the first touchpoint, `c` to the last, `b` spread across the middle. A
30/40/30 variant is worth computing when the middle of the funnel is where the
real work happens. Always state the weights used.

## Methodology (step-by-step)

### 1. Validate and dedupe the touchpoint log

- Check that every touchpoint has a conversion identifier, a parseable
  timestamp, and a channel. Report the row counts dropped and why.
- Normalize all timestamps to a single timezone before ordering anything.
- **Session dedupe**: collapse consecutive touchpoints of the same channel and
  campaign that fall within a dedupe window (30 minutes is a sane default, 24
  hours for low-frequency channels). Without this, one browsing session inflates
  a channel across every path-length-sensitive model.
- **Direct traffic**: decide and declare one policy. Either keep Direct as a
  channel (honest, but it will absorb credit it did not earn), or drop direct
  touchpoints and reassign to the previous known channel (the "last non-direct"
  convention). Compute the headline model both ways if direct exceeds roughly
  15% of touchpoints.
- Filter obvious non-humans and internal traffic before anything else.

### 2. Reconstruct per-conversion paths

Group by conversion identifier, sort by timestamp ascending, and drop
touchpoints older than the lookback window relative to the conversion time.
Report the distribution of path lengths and the share of single-touch paths:
if most paths have one touchpoint, model comparison will show almost nothing
and the tracking setup is the real finding.

### 3. Compute credit per model

For each path and each model, produce a share per touchpoint, multiply by the
conversion value, and accumulate by channel. Verify per path that shares sum to
1 and that credited value sums to the conversion value within a rounding cent.
This check catches most implementation errors immediately.

### 4. Build the comparison table

Rows are channels (or campaigns), columns are models, cells are attributed
value. Add a spend column when available, and a derived return column per model.
Every column must total the same overall conversion value: that identity is the
proof the computation is sound.

### 5. Read the deltas

- **First-touch much greater than last-touch** for a channel: it is an
  **introducer**. It creates demand that another channel harvests. Cutting it
  produces a delayed, hard-to-attribute drop elsewhere.
- **Last-touch much greater than first-touch**: it is a **closer**. It converts
  demand that already existed. Scaling it rarely creates new demand, and its
  apparent return depends on the introducers upstream.
- **Similar across all models**: a self-contained channel, usually short paths.
  Its numbers are the most trustworthy of the set.
- **Linear much greater than both single-touch models**: the channel appears
  often mid-path. Check whether that is genuine nurture or a tracking artifact
  from missing dedupe.
- Rank channels by the spread across models. Wide spread means the reported
  performance is model-dependent and any single number is fragile.

### 6. Recommend a model

Base the recommendation on observable properties of the data, and say so:

- Median path length of 1 to 2 and a sales cycle under a week: last-touch is
  adequate. A multi-touch model would add ceremony without information.
- Median path length of 3 or more, cycle of a few weeks: U-shaped, or time-decay
  with a half-life close to the median time from first touch to conversion.
- Long B2B cycle with a reliable qualification milestone: W-shaped.
- No consensus available and a mixed funnel: linear as a neutral baseline, with
  first-touch and last-touch reported alongside as bounds.

Always present the recommended model together with first-touch and last-touch.
Those two are the extremes, and the gap between them is the honest error bar on
any channel's contribution.

## Interpretation guardrails

- **Attribution redistributes credit, it never measures incrementality.** Every
  model here answers "which touchpoints were present on converting paths?", not
  "what would have happened without this channel?" Only a holdout test,
  geo-experiment, or incrementality study answers the second question. Never
  present attributed value as incremental revenue.
- **Non-converting paths are invisible.** These models only look at paths that
  converted. A channel with huge volume and terrible quality can still look fine.
  Pair the analysis with volume and conversion rate per channel.
- **Long sales cycles need long lookback windows.** If the window is shorter
  than the typical time from first touch to conversion, early touchpoints are
  truncated and every model collapses toward last-touch. Set the window from the
  observed distribution, not from a habit.
- **Walled-garden numbers double-count each other.** Each platform sees only its
  own touchpoints and claims the conversion under its own rules and window. The
  sum of platform-reported conversions routinely exceeds real orders. Reconcile
  against the system of record, never sum across platforms.
- **Small volumes make comparisons noisy.** Below roughly a few hundred
  conversions in the period, differences between models are mostly sampling
  noise, especially at campaign grain. Aggregate to channel level, widen the
  period, or state the uncertainty rather than ranking channels confidently.
- **Modeled and privacy-restricted conversions.** Platform-modeled conversions
  and consent-limited tracking mean part of the path is simply absent. Report
  coverage (share of conversions with at least one tracked touchpoint) next to
  the results.
- **The model is a reporting convention.** Changing models changes the numbers
  without changing reality. Pick one, document it, and keep it stable so trends
  remain comparable over time.

## Worked example

Six conversions, channel-level paths, total value 2700.

| Conversion | Path (ordered) | Value |
| --- | --- | --- |
| C1 | Paid Social, Paid Search, Direct | 500 |
| C2 | Organic, Email | 300 |
| C3 | Paid Search | 200 |
| C4 | Paid Social, Email, Organic, Paid Search | 1000 |
| C5 | Organic, Paid Social, Email, Direct | 600 |
| C6 | Direct | 100 |

Per-path credit for U-shaped, as an illustration of the rule: C4 has four
touchpoints, so Paid Social (first) gets 400, Paid Search (last) gets 400, and
Email and Organic split the middle 200 into 100 each. C1 has three touchpoints:
200 / 100 / 200. C2 has two, so 150 / 150. C3 and C6 are single-touch, so 200
and 100 to their only channel.

**Attributed value by channel and model**

| Channel | First-touch | Last-touch | Linear | U-shaped |
| --- | --- | --- | --- | --- |
| Paid Social | 1500 | 0 | 566.67 | 660 |
| Paid Search | 200 | 1200 | 616.67 | 700 |
| Organic | 900 | 0 | 550 | 490 |
| Email | 0 | 300 | 550 | 310 |
| Direct | 100 | 1200 | 416.67 | 540 |
| **Total** | **2700** | **2700** | **2700** | **2700** |

(Linear column totals 2700 exactly, the displayed cents are rounded from thirds
of 500.)

**Interpretation.** Paid Social is the clearest introducer in this dataset: it
takes 1500 under first-touch and zero under last-touch, so it never closes a
conversion but it opens more than half of them by value. Paid Search and Direct
are the closers, and Direct in particular is suspicious: 1200 of last-touch
credit on a channel that by definition has no acquisition cost usually means
untracked referrers or missing campaign tags, so the last-touch column overstates
it. Organic behaves like a secondary introducer, while Email lives almost
entirely mid-path, which is why it appears only under the multi-touch models. For
a funnel with this shape (median path length 3, meaningful middle, two decisive
ends), U-shaped is the reasonable reporting model, with first-touch and
last-touch published alongside as the bounds: any statement about Paid Social's
contribution has to live somewhere between 0 and 1500 until an incrementality
test narrows it.

## References

- `references/model-formulas.md`: exact credit formulas and edge cases,
  computation-ready.
- `references/data-preparation.md`: export checklist, joining ad clicks to CRM
  outcomes, and the pitfalls that quietly corrupt an attribution analysis.

Maintained by the team at Metrikia (https://metrikia.io).
