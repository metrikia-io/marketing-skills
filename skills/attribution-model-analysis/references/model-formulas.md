# Model Formulas

Notation for one conversion:

- path `T = [t_1, t_2, ..., t_n]`, ordered by ascending timestamp
- conversion value `V`, conversion time `t_conv`
- `share_i` is the credit share of touchpoint `i`, `credit_i = share_i * V`

Universal invariant: `sum(share_i) = 1` for every path and every model, so
`sum(credit_i) = V` within rounding tolerance. Validate this per path.

## First-touch

```
share_1 = 1
share_i = 0 for i > 1
```

## Last-touch

```
share_n = 1
share_i = 0 for i < n
```

Last non-direct variant: let `k` be the largest index with `channel_k != Direct`.
Assign `share_k = 1`. If every touchpoint is Direct, fall back to `share_n = 1`.

## Linear

```
share_i = 1 / n
```

## Time-decay

Choose a half-life `H` in the same time unit as the ages (days is typical).

```
age_i    = t_conv - t_i                 (>= 0, in days)
w_i      = 0.5 ^ (age_i / H)
share_i  = w_i / sum_j(w_j)
```

The normalization step is mandatory: raw weights do not sum to 1.

Reference points: `age = 0` gives `w = 1`, `age = H` gives `w = 0.5`,
`age = 2H` gives `w = 0.25`.

Half-life guidance: 7 days for impulse purchases, 30 days for considered
purchases, 45 to 90 days for enterprise cycles. Always report `H` with results.

Numerical note: for very long paths relative to `H`, weights underflow toward 0.
Compute in log space or clamp `age_i / H` at a large value (for example 50) to
avoid a zero denominator.

## U-shaped (position-based)

General form with weights `(a, b, c)`, `a + b + c = 1` (standard: 0.4, 0.2, 0.4):

```
n = 1:  share_1 = 1
n = 2:  share_1 = a / (a + c),  share_2 = c / (a + c)      (0.5 / 0.5 by default)
n >= 3: share_1 = a
        share_n = c
        share_i = b / (n - 2) for 1 < i < n
```

The `n = 2` case renormalizes `a` and `c` because there is no middle to receive
`b`. Do not silently drop `b`: that would break the sum-to-1 invariant.

## W-shaped

Requires a milestone flag on touchpoints (lead created, demo booked,
opportunity created). Let `m` be the index of the milestone touchpoint. Weights
`(0.3, 0.3, 0.3)` for first, milestone, last, and `0.1` spread over the rest.

```
if no milestone in path       -> fall back to U-shaped, record the fallback
if multiple milestones        -> use the earliest, record the choice
if m == 1 or m == n           -> the milestone coincides with an end point:
                                 merge the two weights on that touchpoint
                                 (0.6), keep the other end at 0.3, and spread
                                 0.1 over the remaining touchpoints
if n == 1                     -> share_1 = 1
if no touchpoints outside the three anchors:
                                 renormalize the three anchor weights to sum 1
                                 (0.3333 each)
otherwise:
    share_1 = 0.3
    share_m = 0.3
    share_n = 0.3
    share_i = 0.1 / (n - 3) for all other i
```

## Edge cases (apply to every model)

**Single-touch path.** `share_1 = 1` under every model. Report the share of
single-touch paths in the dataset: it caps how different the models can possibly
look.

**Ties at the same timestamp.** Order is ambiguous and the choice changes
first-touch and last-touch results. Apply a deterministic tiebreak, in this
order: (1) a sequence or event id if the source provides one, (2) funnel stage
if known, (3) alphabetical channel name. Never leave ordering to the arbitrary
order of the input file. Under time-decay, tied touchpoints receive identical
weights, so the tiebreak is irrelevant there.

**Duplicate touchpoints after dedupe.** If the same channel appears in
consecutive positions beyond the dedupe window, keep both: that is a genuine
return visit, and it legitimately increases that channel's linear credit.

**Path longer than the lookback window.** Drop touchpoints where
`t_conv - t_i > lookback`. If dropping empties the path, exclude the conversion
from the model comparison and count it under "unattributed". Report unattributed
value as its own row so column totals still reconcile to total revenue.

**Touchpoint after the conversion.** Drop it. It is usually clock skew or a
post-purchase email. Log the count: a large number indicates a timezone bug.

**Zero or missing conversion value.** Run the analysis twice: once on conversion
counts (`V = 1` per conversion), once on value. Count-based and value-based
rankings often disagree, and that disagreement is itself a finding.

**Negative value (refund, cancellation).** Either exclude and note the exclusion,
or net it against the original conversion. Never let a refund distribute negative
credit through a fresh path.

## Comparison table construction

For each model, accumulate `credit_i` by channel across all paths.

```
attributed(channel, model) = sum over all paths, all i where channel_i = channel
                             of share_i(model) * V(path)
```

Check: every model column totals the same value, equal to the sum of `V` over
attributed conversions. If a column differs, a share vector did not sum to 1.

Derived metrics, computed per model:

```
return(channel, model)      = attributed(channel, model) / spend(channel)
cost_per_conv(channel, mdl) = spend(channel) / attributed_conversions(channel, mdl)
```

Compute `attributed_conversions` from the count-based run (`V = 1`), not by
dividing value by an average order value.
