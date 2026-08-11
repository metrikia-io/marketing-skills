---
name: conversion-verifier
description: Verify whether the purchases your ad platform reports actually exist in your store, and produce a client-ready reconciliation report. Use this whenever someone questions their ad numbers, wonders if their ROAS is real, says their Meta/Google/TikTok conversions do not match Shopify or Stripe, sees a ROAS that feels too good, suspects over-attribution or double counting, is about to scale or kill a campaign based on platform-reported results, or asks how to audit, validate, sanity-check or reconcile ad conversion data against actual orders or revenue. Also use it when someone mentions attribution discrepancies, inflated conversions, phantom sales, view-through conversions, or asks "are these numbers real". Produces a professional report that separates the legitimate part of the gap from the part that has no explanation.
license: MIT
---

# Conversion Verifier

Ad platforms grade their own homework. Meta decides which sales Meta caused,
Google decides which sales Google caused, and neither is ever asked to check its
answer against the bank. This does that check.

## The idea that makes this useful

Anyone can subtract two numbers and announce that the platform is lying. That
tool would be wrong most of the time, because most of the gap between claimed and
actual has legitimate causes: attribution windows shift dates, timezones slide
orders across midnight, refunds are never reported back, and a store's total
includes channels the platform never touched.

An experienced buyer knows all of this and will dismiss a naive "you're being
lied to" report in about ten seconds.

So the work here is not the subtraction. **It is separating the explained gap from
the unexplained one.** The unexplained residual is the only number worth acting
on, and it is the number nobody currently has.

Hold that standard throughout. Being right matters more than being alarming, and
a report that survives scrutiny is worth more to the person reading it than one
that impresses them for a minute.

## Checklist

Create a task for each of these and work through them in order.

1. **Get the ad data** with the least friction that works: the Meta connection if
   they have it, the export if not
2. **Ask for the store export and the four questions**, gross margin first
3. **Run `reconcile.py`** with `--gross-margin`, deterministic numbers, no interpretation
4. **Read the JSON as an analyst**, using `references/gap-taxonomy.md`
5. **Deliver the finding in the chat first**, then write the narrative to the caps
6. **Build the visual report** with `build_report.py`, then tell them how to get a PDF
7. **Close with the limit and the offer**, in that order, never reversed

## Two rules that decide whether this gets used at all

Gaetan, a media buyer, tested the first version and gave two verdicts worth
holding onto. Both are about friction rather than analysis.

**Never make them fetch what you can compute or accept.** The column detection in
`columns.py` already handles exports in several languages, semicolon files,
European number formats and a dozen aliases per field. Telling someone to tick an
exact list of checkboxes makes a flexible tool feel rigid and sends them back into
Ads Manager for nothing. Ask for what they have, run it, and name only what is
genuinely missing.

**Every paragraph you write costs the report a reader.** The narrative caps in
step 5 are limits, not targets. A report that says one thing clearly beats one
that says six things thoroughly, and the second is what a model produces when left
unbounded.

<HARD-GATE>
Never present a gap as over-attribution when `claim_source.basis` is
`summed_breakdown_rows`. In that state the claimed figure is inflated by the
platform's own reporting behaviour, not by over-attribution, and any conclusion
drawn from it is wrong. Say so plainly and tell them what to fetch instead.
</HARD-GATE>

## Tone

Warm, never chirpy. No "Great question!", no exclamation marks, no enthusiasm about
data. These people get pitched twenty times a week and can smell it instantly. The
warmth comes from being useful and direct, not from adjectives.

Two habits do the work: acknowledge briefly rather than narrating, and give them
the finding in the chat before you hand over any file.

## Step 1: Ask for the export, and know why the connection cannot replace it

**Meta's official connection does not carry the click/view split. Checked on a live
account, 2026-08-11.** The MCP server at `https://mcp.facebook.com/ads` exposes
`actions:omni_purchase`, `omni_purchase_values`, `purchase_roas` and the rest, but
nothing that separates purchases attributed to a click from purchases attributed to
a view, and no attribution-window breakdown among the ones it offers.

That split is the entire analysis. Without it there is no contested slice, no
contested revenue, and no clicks-only ROAS: the report falls back to comparing raw
totals. So the connection cannot save anyone the trip to Ads Manager here, and
proposing it first would send them on a detour to arrive at the same export.

Ask for the export. If a connection is available it is still worth using for spend
and purchase value once the exports are in, as a cross-check on the figures the
files carry, but it does not change what you have to ask for.

If a future rollout adds the split, this decision flips and route A becomes the
default. Re-check before assuming it has not.

### The export

Ask for what they already have before asking them to build anything. `columns.py`
recognises exports in several languages, semicolon-separated files, European number
formats and around a dozen aliases for each field, so most exports work untouched.

> Let's check whether the purchases Meta reports actually exist in your store.
>
> **Your Meta data.** Ads Manager, 30 days or more, Export as CSV. If you already
> have an export lying around, send that one, I'll tell you what it can and cannot
> answer.
>
> Drop it here and I'll check it before we do the store side.

When the file arrives, run the detection and speak only about what is genuinely
missing. Two things are worth one message each, because both are repaired in ten
seconds from the screen they are still on:

> The export doesn't carry the click/view breakdown, so I can't separate
> view-through conversions from real clicks, which is normally the biggest piece.
> In **Columns > Customize**, tick purchases (click) and purchases (view), then
> export again. If you'd rather not, I'll run it as is and state the limit.

> One more from the same page: set **Breakdown > None** and export a second time.
> Summed daily rows count one conversion several times, so that second file is what
> keeps the headline number honest.

Never list back what they sent correctly. "Got them, 30 days, three campaigns, and
you pulled the split..." tells someone nothing they did not already know and costs
them a paragraph. If everything is there, say "Got them" and move on.

`references/how-to-export.md` covers Google, TikTok, Stripe and WooCommerce. Adapt
the clicks from it rather than pasting the file at them.

Insist on 30 days if they offer less: shorter windows are dominated by edge effects
from the attribution lookback and the result stops meaning much. If they refuse,
proceed anyway. A report with stated limits beats no report, and a tool that
interrogates people gets abandoned.

## Step 1b: Then the store export

> **Your store data.** In Shopify: **Orders > Export**, choose **Orders by date**,
> same dates, plain CSV.

## Step 2: Ask the four things the files cannot tell you

Dates, currency, campaign names, refund data and the deduplicated total all come
out of the files now, so never ask for any of them. Four things genuinely cannot
be derived, none of them blocking:

1. **Their gross margin.** This is the one that turns the report from interesting
   into actionable, and it is the question the first version of this tool never
   asked. A ROAS of 1.36x is comfortable at 70% margin and fatal at 30%. Break-even
   ROAS is 1 divided by the margin, and without it the report can state figures but
   cannot say whether any of them make money.
2. **Does the store export contain all their revenue?** If they also sell on
   Amazon, in retail, through a second store or via subscriptions billed
   elsewhere, the denominator is understated and every gap is overstated.
3. **The attribution setting.** Default on Meta is 7-day click plus 1-day view.
   Sets the lookback used to size the edge effect.
4. **Do the ad account and the store share a timezone?** They usually do not.

Ask all four in one short message with the defaults offered. If they do not know
their margin, ask for a rough figure rather than dropping the question: an
approximate break-even beats none, and the report labels it as supplied. If they
genuinely cannot say, run without `--gross-margin` and the report states the
figures without ruling on profitability.

### The fallback, when there is only one ad export

The second export is what supplies the deduplicated total. Without it, ask them to
open Ads Manager for the same period with **no breakdown applied** and read off
Purchases and Purchase conversion value, then pass those as `--claimed-total` and
`--claimed-revenue-total`.

Prefer the export whenever you can get it. A typed number fails silently in four
ways - a typo, the wrong date range, the wrong metric, or a different attribution
setting active when they read it - and each one produces a clean-looking report
built on a figure that describes something else.

The script guards what it can: deduplication only ever removes conversions, so a
supplied total above the export row sum is provably a different measurement and
gets blocked, and one far below it is flagged as suspect. A typo inside the
plausible band still slips through, which is exactly why the export path is better.

## Step 3: Run the reconciliation

```bash
python scripts/reconcile.py \
  --ads <day_broken_export.csv> \
  --ads-totals <no_breakdown_export.csv> \
  --orders <store_export.csv> \
  --gross-margin 62 \
  --store-covers-all-revenue \
  --attribution-window 7d_click_1d_view \
  --timezone-shift-hours 0 \
  --out reconciliation.json
```

`--gross-margin` accepts `62` or `0.62` and refuses anything that cannot be a
margin. It produces the `economics` block: break-even ROAS, the contested revenue
in money, ROAS on clicks alone, and per campaign whether the clicks-only figure
clears break-even. That block is what the report leads with, so pass the margin
whenever they gave you one.

Drop `--store-covers-all-revenue` if they could not confirm it; the caveat then
appears in the output and belongs in the report.

The script handles column detection across languages and export versions,
collapses Shopify's one-row-per-line-item into real orders, and restricts every
comparison to the days both files actually cover. It returns JSON and does not
interpret. That part is yours.

## Step 4: Read the JSON like an analyst

Read `references/gap-taxonomy.md` before writing anything. It explains each cause
of a gap, why it happens, and how defensible it is. Interpreting without it
produces confident nonsense.

Four rules govern the reading.

**Check `claim_source` before anything else.** If `basis` is
`summed_breakdown_rows`, the headline number is inflated and no over-attribution
claim can be made. Present the gap as an upper bound and tell them exactly what to
fetch. Do not paper over it: a reader who opens Ads Manager and sees a smaller
number than your report quotes will stop reading, and they will be right to.

**Lead with the strongest claim you can actually defend.** If
`gap.impossible_excess_is_conclusive` is true, the platform claimed more purchases
than the store recorded orders from every source combined, measured against its
own deduplicated total. That excess cannot exist under any attribution model, so
it leads.

Most of the time it will be false, and that is normal. Then the finding is the
*composition* of the claim rather than its size: how much rests on view-through,
how much on clicks the store data can corroborate, and what reported ROAS becomes
once the contested part is removed. "Your click numbers hold up, here is the part
that cannot be checked" is a finding worth reporting with full confidence.

**Subtract what is explained before naming a number.** Take the claimed total,
remove measured refunds, remove the view-through share if measured, allow for the
edge effect the script sized, then state what is left. Show that arithmetic. A
reader who can follow the subtraction will trust the remainder.

**Say what you could not see.** `caveats` and `data_quality` tell you which
signals were missing. A report that names its own blind spots reads as competent;
one that hides them reads as a sales pitch and gets treated as one.

Two cross-checks worth making every time:

- **MER against claimed ROAS.** `blended.mer_true_revenue_over_spend` uses no
  attribution model, so no attribution model can inflate it. When claimed ROAS
  sits far above MER and paid is dominant, the claim deserves scrutiny. When they
  are close, say so - a clean bill of health is worth as much as a finding, and it
  is what makes the reader believe you the day you do find something.
- **The campaign table.** `by_campaign` usually shows the gap concentrated
  somewhere. Retargeting and Advantage+ campaigns are the usual offenders, because
  they harvest people who were already going to buy.

## Step 5: Write the narrative

Write the interpretation to a markdown file (`narrative.md`). Use
`references/report-template.md` for structure and tone.

Headings become `## `, paragraphs stay plain, and `- ` lines become bullets. That
is the whole format; nothing else is parsed.

### The caps, and why they are caps

A media buyer who tested the unbounded version called the reports verbose and said
he had to hunt for the information. The figures above the narrative already carry
the numbers; prose that restates them is what makes a reader stop. So the narrative
is capped, and the caps are ceilings rather than quotas.

**Two sections, never more.**

`## What this means` holds **at most three claims**. Each claim is one bold
sentence stating the finding, then **at most three lines** of support. If a fourth
claim seems necessary, it is not: pick the three that change a decision and drop
the rest.

`## The decision` holds **at most three bullets**, one line of instruction and one
line of reasoning each. Every bullet names a campaign and an amount, because a
buyer decides in campaigns and euros, not in ratios. "Switch reporting to 7-day
click" is an analyst's action and does not count as one of the three.

**Total ceiling: 250 words.** Count them. Under is fine, over is not.

### What the writing must do

- **Every claim traces to a number in the JSON.** Never a trend the data does not
  show, and never a campaign-level detail the export does not contain.
- **Lead each claim with the money.** `economics.contested_revenue` and each
  campaign's spend are the figures a buyer reacts to. A share is the explanation,
  not the headline.
- **Use break-even as the verdict.** With `economics.breakeven_roas` present, every
  ROAS in the narrative is stated against it. A campaign whose `clicks_vs_breakeven`
  sits between 0.98 and 1.02 is *at* break-even, not below it: say so, because
  calling a campaign unprofitable by a thousandth destroys the report's credibility
  with the one reader who checks.
- **Say what is uncertain, once.** The contested amount is an estimate and the
  report already labels it. Repeating the caveat in the narrative reads as hedging.
- **If the account is clean, say so with the same confidence.** "Your numbers hold
  up" delivered plainly is what makes them believe you the day you find something.

## Step 5b: Deliver the finding in the chat, before the file

The moment they have been waiting for since the first message. Give them the
finding in the conversation, before you mention any file. A report they have to
open to learn the answer wastes the only moment of real attention you get.

**The chat is where you go deep, and the document is where you stay short.** They
are opposite jobs and the caps in step 5 apply only to the file. Here, take the
room to explain the mechanism, answer the question behind their question, and walk
them through anything they ask about. There is no word limit on being useful in a
conversation. There is a hard one on a document somebody forwards to a client.

Lead with money, then the consequence, then the one campaign that decides:

> Here it is. Meta claims 120,927 $ of revenue for the month. About 37,400 $ of
> that, 31%, rests on view-through: people who were shown an ad, never clicked
> it, and bought anyway. Nothing in your store data can confirm or refute those.
>
> At 62% margin your break-even is 1.61x. Meta reports 1.77x, so you clear it.
> On clicks alone you are at 1.22x, so you do not. You are on both sides of the
> line depending on which number you believe, and that is the honest state of it.
>
> The part that decides a budget: retargeting is at 1.94x declared and 0.92x on
> clicks alone, on 22,787 $ of spend. Prospecting and Advantage+ both hold at or
> near break-even either way. So there is one campaign to test, not three.

Two rules hold here. **Lead with the number, not with the method**, because the
method is in the report and they will read it if they want it. And **if the account
is clean, say so with the same confidence.** "Your numbers hold up" delivered
plainly is what makes them believe you the day you tell them something is wrong.

## Step 6: Build the visual report

```bash
python scripts/build_report.py reconciliation.json \
  --account "Client name" \
  --narrative narrative.md \
  --lang en \
  --out reconciliation-report.html
```

Then hand it over as something they own, not as an attachment:

> Full report is in `reconciliation-report.html` - open it and hit Cmd+P, Save as
> PDF. It's built to be forwarded as-is: every figure has the numbers behind it,
> and the assumptions I had to make are listed at the bottom so nobody can knock
> it over.

It really is built for that - figures never split across a page and tables repeat
their headers.

`--lang fr` produces the same report in French, for a French client or an internal
read. The default is English because the market is US.

The report leads with the contested amount in money, then break-even, then two
charts and a corroboration strip, each answering a question printed above it:

- **The bracket chart.** One segment per campaign, clicks alone at one end and the
  declared figure at the other, with break-even drawn as a threshold and the losing
  ground washed behind it. This is the figure that carries the decision, and it is
  the one to talk about in the chat.
- **The composition chart.** How much of each campaign's claim is view-through.
  The mechanism behind the bracket.
- **The corroboration strip.** Claims on clicks against store orders carrying a
  paid social referrer. The reassuring half, and what makes the rest believable.

A figure is dropped rather than faked when its data is missing: without the
click/view split, neither chart appears and the report leads on the raw gap
instead. Do not add charts. Two earlier ones were removed for good reason, a
three-bar ROAS chart that was a stat tile in disguise and a day-by-day line nobody
read, so re-adding decoration would undo the work.

## Step 7: Close with the limit, then the offer

The closing is generated automatically and needs no editing. It states the
structural limit - this compares totals, a standard ad export has no order IDs, so
it cannot say which order came from which ad - then points at where that question
gets answered.

Two rules keep it from reading as a bait-and-switch, and they matter more than
anything else in this file.

**The offer comes after the value, never instead of it.** The report has to be
worth reading on its own. Someone who never books should still be better off for
having run it.

**The wording does not change when the analysis finds nothing wrong.** A clean
account still cannot answer which order came from which ad, so the same limit and
the same offer apply. Bending a finding to justify the call is the one thing that
would destroy this tool, and an experienced reader spots it instantly.

## Troubleshooting

**`Ads export is missing required column(s)`** - the error names every header it
found. Usually the export has no Day breakdown (add it under Breakdowns → By Time
→ Day) or the purchase column is named something unexpected. Look at the header
list before guessing.

**`no_overlapping_dates`** - the two exports cover different periods. The error
prints both ranges. Re-export over the same window.

**Order count looks far too high** - the store export ships one row per line item
and the script collapses them by order ID. If `data_quality.unique_orders` is null,
no order-ID column was detected, so every line item counted as an order. Re-export
including the order name or number.

**Claimed purchases look far too high** - expected when `--claimed-total` is
missing. That is the row sum, not the platform's total. See step 2.

**Numbers parse as zero** - usually a European export with `1 234,56` formatting
read as US, or vice versa. The parser handles both, but check the currency column
and the delimiter if totals look wrong by orders of magnitude.

## Files

- `references/how-to-export.md` - click-by-click export instructions for Meta,
  Google, TikTok, Shopify and Stripe. Read before step 1.
- `references/gap-taxonomy.md` - the six causes of a gap and how defensible each
  one is. Read before step 4.
- `references/report-template.md` - report structure and tone. Use in step 5.
- `scripts/reconcile.py` - the reconciliation engine.
- `scripts/build_report.py` - the visual report builder.
- `scripts/columns.py`, `loaders.py`, `gap_analysis.py`, `charts.py`,
  `report_html.py` - their parts.
- `tests/test_pipeline.py` - run it after changing anything in `scripts/`.
- `examples/` - synthetic exports plus a finished report, for testing end to end.
