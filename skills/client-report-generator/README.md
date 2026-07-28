# Client Report Generator

**Turn a month of ad exports into a client-ready report - numbers, a written
explanation of what changed and why, and an honest note on what the numbers can be
trusted for.**

The monthly client report is done by hand almost everywhere: a VA pulls numbers
into a deck, the buyer writes the insights. This automates the pull and the
period-over-period comparison, and helps you write the part that actually matters.

Two months of CSV exports, no account, no signup. Python 3.9+, zero dependencies.

---

## What this competes with

Not Looker Studio. Looker already draws the charts, connects to the APIs, and does
it for free.

The manual work is not the charts. It is the two things a person does after the
charts exist: comparing this month to last, and **writing what changed and why in
language a client understands.** The second is what a client pays an agency for,
and it is the part this tool is built to produce well - the write-up reads like a
senior media buyer wrote it, because it is written from the actual figures.

---

## Quick start

```bash
git clone https://github.com/metrikia/client-report-generator.git
cd client-report-generator

python scripts/aggregate.py \
  --this   examples/meta_june.csv examples/google_june.csv \
  --last   examples/meta_may.csv  examples/google_may.csv \
  --orders examples/shopify_june.csv --orders-last examples/shopify_may.csv \
  --label "June 2026" --label-last "May 2026" \
  --out summary.json

python scripts/build_report.py summary.json --account "Example Co" --out report.html
```

Open `report.html` and print to PDF. A finished example, narrative included, is in
[`examples/sample-report.html`](examples/sample-report.html).

### With Claude Code

```bash
cp -r client-report-generator ~/.claude/skills/
```

Then ask: *"build my client report for June"*. Claude asks for the two months of
exports, aggregates them, **writes the analysis from the numbers**, and produces
the report.

---

## What you need

Two months of exports - the reporting period and the one before it - so the report
can show what changed.

- **Ad channels** - Meta, Google and/or TikTok, one CSV per channel per month. The
  channel is detected from the filename, so one command can mix platforms.
- **Store** - Shopify orders or Stripe payments, one CSV per month.

Weekly reporting works the same way: two weeks instead of two months.

Export clicks for every platform:
[`references/how-to-export.md`](references/how-to-export.md).

---

## What you get

A three-section report, built to forward to a client without editing:

1. **What happened** - spend, revenue, blended ROAS and orders, each with its
   change against last period; a per-channel table; a channel ROAS chart.
2. **What we did, and why** - the written analysis. Generated from the numbers when
   run through Claude Code, or write it yourself and pass it with `--narrative`.
3. **What these numbers rest on** - a short, honest note: channel revenue overlaps
   because each platform counts its own sales, blended ROAS is the one figure no
   attribution model can inflate, and order-level reconciliation is what closes the
   gap.

That third section is not a disclaimer to bury. A client already suspects the
platform numbers are generous. Naming it first, in your own report, is what makes
you the trustworthy one in the room.

---

## What it does not do

It reports what the platforms claim, per channel, and how that moved. It does not
tell you which specific sale came from which specific ad - channel revenue overlaps
and adds up to more than the store took, which the report says plainly. Closing
that needs order-level attribution reconciled against money actually collected,
which is what [Metrikia](https://metrikia.io/) does.

Want a read on your own account? Gaetan runs a 30-minute review, no charge:
[book it here](https://cal.com/gaetanhamel/metrikia?overlayCalendar=true).

---

## Contributing

```bash
python tests/test_pipeline.py
```

16 checks, no framework, no dependencies. Two are load-bearing: channel detection
(a mislabeled channel corrupts a client-facing report) and HTML escaping (the
report is forwarded, so an unescaped value runs in the client's browser). The
`columns.py`, `loaders.py`, `charts.py` and `safe_html.py` modules are shared with
the conversion-verifier tool and carry its audit.

## License

MIT - use it, fork it, ship it inside your own tooling.
