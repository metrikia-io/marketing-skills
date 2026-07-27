# Data Preparation

A model comparison is only as good as the path reconstruction underneath it.
Work through this checklist before computing anything.

## Required columns

| Column | Required | Notes |
| --- | --- | --- |
| `conversion_id` | yes | Stable key grouping touchpoints into one path. Order id, deal id, or lead id. |
| `timestamp` | yes | Touchpoint time, ISO 8601 with an explicit offset. |
| `channel` | yes | Reporting-level grouping. Keep the vocabulary closed and small. |
| `source` / `medium` | recommended | Lets you rebuild channel groupings later without a new export. |
| `campaign` | recommended | Enables campaign-grain analysis. |
| `conversion_value` | yes for value analysis | Net of tax and shipping, one currency. |
| `converted_at` | yes for time-decay and lookback | Conversion timestamp. |
| `click_id` | recommended | Platform click identifier, the strongest join key to ad data. |
| `milestone` | only for W-shaped | Boolean or stage label marking qualification. |
| `is_bot` / `user_agent` | helpful | Enables filtering without a second export. |

## Timestamp and timezone normalization

- Convert everything to a single timezone (UTC for computation, the business
  timezone for reporting boundaries) before sorting.
- Reject rows with unparseable or null timestamps and report the count.
- Check for clock skew: client-side timestamps can drift or be manipulated.
  Any touchpoint dated after its conversion, or absurdly far in the past, is a
  skew symptom. Drop and count.
- Watch daylight saving transitions if the export mixes local times without
  offsets. An hour of duplicated or missing local time reorders short paths.

## Session dedupe

- Collapse consecutive touchpoints sharing the same channel and campaign within
  a window. 30 minutes is a reasonable default; use 24 hours for channels that
  should not legitimately fire twice in a day.
- Keep the earliest timestamp of the collapsed group, and record how many raw
  touchpoints it represents.
- Dedupe before path reconstruction, never after: linear and position-based
  models are highly sensitive to path length.

## Bot and internal traffic filtering

- Drop known crawler user agents and datacenter IP ranges.
- Drop internal traffic: office IPs, employee identifiers, staging hosts.
- Drop paths whose touchpoint count is implausible (for example above 100 in a
  day) and inspect them separately rather than silently keeping them.
- Drop link-scanner hits on email: security scanners open every link within
  seconds of delivery, which fabricates email touchpoints. A common signature is
  a click timestamp within a second or two of the send.

## Unknown and direct traffic

- Do not merge "unknown" (no referrer information captured) with "direct" (a
  genuine typed-in or bookmarked visit). Keep them distinct if the data allows.
- Pick one direct policy for the whole analysis and state it: keep Direct as a
  channel, or apply the last non-direct convention. Compute the headline model
  both ways when direct exceeds roughly 15% of touchpoints.
- A large direct share is usually a tracking defect, not customer behavior.
  Investigate: missing tags on internal links, stripped referrers on redirects,
  app-to-browser transitions, and untagged QR or offline campaigns.

## Joining ad clicks to CRM outcomes

Preferred join order, most to least reliable:

1. **Click identifier.** Each ad platform appends a click id to the landing URL.
   Capture it on the landing page, persist it with the lead or order, and join
   ad data on it. This survives UTM loss on later navigation and is the only key
   that maps a touchpoint back to an exact ad.
2. **UTM parameters.** Capture the full set (source, medium, campaign, content,
   term) on first landing and store the first and last values separately. Join
   on campaign naming, which requires a naming convention that is actually
   enforced.
3. **Timestamp plus landing page.** Last resort, approximate, and prone to
   collisions in high volume. Use only for triage, never for a published number.

Persist identifiers in first-party storage with a lifetime at least as long as
the lookback window, and carry them into the CRM record at creation time. A
click id captured but never written to the lead is invisible to this analysis.

## Common pitfalls

- **Missing UTMs on branded search.** Branded campaigns are often untagged or
  overlap with organic listings, so credit lands on organic or direct and the
  closer role of branded search disappears from the table.
- **Offline conversions arriving late.** Phone orders, sales-closed deals, and
  in-store purchases are recorded days or weeks after the touchpoints. If the
  export window is cut by touchpoint date, those conversions are missing. Cut by
  conversion date and pull touchpoints back across the full lookback window.
- **Lookback shorter than the sales cycle.** Truncated paths push every model
  toward last-touch. Measure the observed distribution of first-touch-to-
  conversion time and set the window above its 80th percentile.
- **Identity resets.** Cookie expiry, browser privacy limits, and cross-device
  journeys split one real path into several fragments, inflating the count of
  single-touch paths. Prefer a deterministic identifier (a hashed email captured
  at login or form submit) as the path key when available.
- **Currency and tax inconsistency.** Mixed currencies or a value field that
  sometimes includes tax makes channel comparisons meaningless. Normalize to one
  currency at a fixed rate for the period and document it.
- **Duplicate conversions.** The same order exported twice, or a lead and its
  resulting order both counted, doubles a path's value. Deduplicate on the
  business key and reconcile the total against the system of record before
  running any model.
- **Test and internal orders.** Filter them out explicitly. They usually carry a
  Direct or Unknown path and quietly inflate the closers.
- **Consent-limited tracking.** Where consent is refused, touchpoints are absent
  but the conversion may still be recorded. Report coverage (share of
  conversions having at least one tracked touchpoint) alongside every result.

## Pre-flight validation

Before computing models, confirm and report:

- row count in, row count after each filter, and the reason for each drop,
- number of conversions, total value, and reconciliation against the system of
  record,
- distribution of path length, including the share of single-touch paths,
- distribution of first-touch-to-conversion time, used to set lookback and
  half-life,
- channel mix by touchpoint count, with Direct and Unknown called out,
- coverage percentage.

If reconciliation against the system of record is off by more than a few
percent, fix the export before interpreting any model. A clean comparison table
built on a broken join is worse than no analysis, because it looks credible.
