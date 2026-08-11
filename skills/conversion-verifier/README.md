# Conversion Verifier

**Check whether the purchases your ad platform reports actually exist in your store.**

Meta decides which sales Meta caused. Google decides which sales Google caused.
Neither is ever asked to check its answer against the bank. This does that check,
and it tells you which part of the difference is legitimate and which part has no
explanation at all.

Three CSV exports, about ten minutes, no account, no pixel, no signup. Python 3.9+,
zero dependencies.

---

## What makes this different from subtracting two numbers

Most of the gap between claimed and actual conversions has legitimate causes:
attribution windows shift dates, timezones slide orders across midnight, refunds
are never reported back, and your store total includes channels the platform never
touched.

A tool that ignores all that and announces "the platform is lying" is wrong most of
the time, and any experienced buyer will say so.

This one separates the explained gap from the unexplained one. **The unexplained
residual is the only number worth acting on**, and it is the number nobody
currently has.

### The trap it avoids

Meta documents that summing breakdown rows overstates its own deduplicated total:
one conversion can appear in several rows. Most homemade versions of this analysis
add up a campaign-by-day export and build their headline on a number Meta itself
would never report - which collapses the moment the reader opens their own account.

This tool refuses to make any conclusive claim until it has a total that is not a
day-broken row sum, and it measures the inflation for you once it does.

---

## Quick start

```bash
git clone https://github.com/metrikia-io/marketing-skills.git
cd marketing-skills/skills/conversion-verifier

# see what a finding looks like, on synthetic data
python scripts/reconcile.py \
  --ads examples/meta_export.csv \
  --ads-totals examples/meta_export_totals.csv \
  --orders examples/shopify_orders.csv \
  --out recon.json

python scripts/build_report.py recon.json --account "Example Store" --out report.html
```

Open `report.html` and print to PDF. A finished example ships in
[`examples/sample-report.html`](examples/sample-report.html)
([French version](examples/sample-report-FR.html)).

### With Claude Code

```bash
cp -r conversion-verifier ~/.claude/skills/
```

Then ask: *"check whether my Meta conversions are real"*. Claude walks you through
the exports, asks the three questions that matter, runs the analysis and writes the
report.

---

## What you need

Three CSV exports covering the same dates, **30 days minimum**.

**From your ad platform** - campaign name, day, spend, purchases, purchase value.
Also tick **Purchases (click)** and **Purchases (view)**: that split is what lets
view-through conversions be measured instead of guessed at.

**The same ad export again, with the day breakdown turned off** - one extra click, and it is what supplies the
deduplicated totals. Pass it as `--ads-totals`. Without it the tool still runs, but it refuses to draw any
conclusion, because a day-broken row sum is not what the platform actually claims.

If you would rather type the number than export twice, `--claimed-total` accepts it
and the tool sanity-checks it: deduplication only removes conversions, so a figure
above the row sum is blocked outright and one far below it is flagged.

**From your store** - Shopify orders export, Stripe payments export, or any orders
CSV with a date and an amount. Line-item duplication is handled automatically.

Click-by-click instructions for Meta, Google, TikTok, Shopify and Stripe:
[`references/how-to-export.md`](references/how-to-export.md).

---

## What you get

A report you can forward to a client or a boss without editing:

- **The headline**, stated only as strongly as the data supports
- **Three figures**, each answering a question printed above it: what the claimed
  number is made of, what ROAS becomes once the contested part is removed, and
  whether the gap is steady or spikes on particular days
- **The gap broken down by cause**, each marked legitimate, contested, or
  unexplained
- **Blended MER against reported ROAS** - MER uses no attribution model, so no
  attribution model can inflate it
- **What the analysis could not see**, stated plainly

Every figure has a table twin, so no value is reachable only through a chart. A
figure whose data is missing is dropped rather than filled with an average.

English by default; `--lang fr` for French.

---

## The causes of a gap

| Cause | Status | Typical size |
|---|---|---|
| Breakdown row inflation | Measurement artifact | 5-15% of the row sum |
| Cross-channel overlap | Structural | varies |
| Attribution date shifting | Legitimate | lookback ÷ window |
| Timezone mismatch | Legitimate | up to 1 day of volume |
| Refunds and cancellations | Legitimate | 3-10% of orders |
| View-through conversions | **Contested** | 10-30% of claimed |
| Unexplained residual | **No mechanism** | what you act on |

Full explanation, with what makes each one defensible:
[`references/gap-taxonomy.md`](references/gap-taxonomy.md).

---

## What it cannot do

A standard ad export is aggregated by campaign and day and contains no order IDs.
This can size the categories of gap and prove claimed sales exceed real ones. **It
cannot tell you which specific order came from which specific ad** - which is
exactly what settles the contested part.

That needs order-level attribution reconciled against money actually collected.
It is what [Metrikia](https://metrikia.io/) does, and this checker works entirely
without it.

If you want a read on your own account first, Gaetan runs a call on it:
[book it here](https://cal.com/gaetanhamel/metrikia?overlayCalendar=true).

---

## Repo layout

```
SKILL.md                  the workflow, for Claude Code
references/
  how-to-export.md        click-by-click, five platforms
  gap-taxonomy.md         the causes and how defensible each one is
  report-template.md      report structure and tone
scripts/
  reconcile.py            the engine - CLI entry point
  build_report.py         the report builder - CLI entry point
  columns.py              column detection, number and date parsing
  loaders.py              per-day and per-campaign aggregation
  gap_analysis.py         gap classification
  charts.py               inline SVG, no dependencies
  report_html.py          HTML shell, en/fr strings
tests/test_pipeline.py    run after changing anything in scripts/
examples/                 synthetic exports (both ad variants) and a finished report
```

## Contributing

```bash
python tests/test_pipeline.py
```

36 checks, no framework, no dependencies. The deduplication guard has its own
tests: if they fail, every report this tool produces becomes dismissible, so treat
them as load-bearing rather than optional.

Two rules for changes:

**A figure must answer a question a reader actually has.** If you cannot write the
question above the chart, the chart does not go in.

**No number without a path to it.** Every figure has a table twin, and every claim
in a report shows the arithmetic behind it.

## License

MIT - use it, fork it, ship it inside your own tooling.
