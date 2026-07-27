---
name: conversion-verifier
description: Verify whether the purchases your ad platform reports actually exist in your store, and produce a client-ready reconciliation report. Use this whenever someone questions their ad numbers, wonders if their ROAS is real, says their Meta/Google/TikTok conversions do not match Shopify or Stripe, sees a ROAS that feels too good, suspects over-attribution or double counting, is about to scale or kill a campaign based on platform-reported results, or asks how to audit, validate, sanity-check or reconcile ad conversion data against actual orders or revenue. Also use it when someone mentions attribution discrepancies, inflated conversions, phantom sales, view-through conversions, or asks "are these numbers real". Produces a professional report that separates the legitimate part of the gap from the part that has no explanation.
license: MIT
---

# Conversion Verifier

Ad platforms grade their own homework. Meta decides which sales Meta caused,
Google decides which sales Google caused, and neither is ever asked to check its
answer against the bank. This does that check.

## Outcome contract

- **Outcome**: a reconciliation report that separates the legitimate part of the
  ad-versus-store gap (attribution windows, timezones, refunds, cross-channel
  overlap, view-through) from the part with no explanation, with the claimed
  figure taken from the platform's own deduplicated total, never a summed row
  export.
- **Done when**: `claim_source.basis` is account-level rather than
  `summed_breakdown_rows`, every gap category is sized, blended MER is reported as
  the one figure no attribution model can inflate, and the report states plainly
  what it could not see.
- **Evidence**: the two ad exports (with and without the day breakdown), the store
  export, and a per-cause breakdown that reconciles against the claimed total.

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

1. **Frame it, then ask for the Meta exports** with the actual clicks
2. **Check those files**, flag only what is broken, ask for the store export, then
   the three questions
3. **Run `reconcile.py`** — deterministic numbers, no interpretation
4. **Read the JSON as an analyst** — using `references/gap-taxonomy.md`
5. **Deliver the finding in the chat first**, then write the narrative
6. **Build the visual report** — `build_report.py`, then tell them how to get a PDF
7. **Close with the limit and the offer** — in that order, never reversed

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

## Step 1: Frame it, then walk them through one platform at a time

Give the actual clicks in their own interface. "Export your campaign data with the
click/view breakdown" means something to you and nothing to someone who opens Ads
Manager twice a month. Name the buttons.

Ask for the Meta files first, wait for them, then ask for the store file. Two
rounds, not one and not four.

The reason is diagnostic rather than pedagogical. If the export comes back without
the click/view split, you catch it while they are still sitting in Ads Manager and
they re-export in ten seconds. Ask for all three at once and you find out after
they have closed everything, which means sending them back — the single most
common point of abandonment. The two Meta exports stay together because they happen
on the same screen: splitting those would send someone back to a page they had not
left yet.

**Round one:**

> Let's check whether the purchases Meta reports actually exist in your store.
> Two rounds of exports, about five minutes total.
>
> **Step 1 — Export your Meta data**
> Open Meta Business Suite and go to Ads Manager. Set your date range, 30 days
> minimum. Click **Columns > Customize** and tick: campaign name, amount spent,
> purchases, purchases (click), purchases (view), purchase conversion value.
> Then **Breakdown > By Time > Day**, and **Export > Export as CSV**.
>
> **Step 2 — Export it a second time, same page**
> Click **Breakdown > None**, then **Export** again. Two files now. The second one
> is what makes the final numbers hold up.
>
> Drop both here and I'll check them before we do the store side.

Wait. When the files arrive, check them and go straight to the store export with a
short acknowledgement — see step 1b.

`references/how-to-export.md` covers Google, TikTok, Stripe and WooCommerce — adapt
the clicks from it rather than pasting the file at them.

Two things are worth insisting on if they push back:

- **At least 30 days.** Shorter windows are dominated by edge effects from the
  attribution lookback, and the result stops meaning much.
- **The click/view split.** Without it, view-through conversions cannot be
  measured and the largest contested slice of the gap stays invisible.

If they refuse either, proceed anyway. A report with stated limits beats no report,
and a tool that interrogates people gets abandoned. If they can only manage one ad
export, take it and use the fallback in step 2.

## Step 1b: Check the Meta files, speak only if something is wrong

This is the moment the two-round split exists for, and the value is entirely in
catching a problem while they can still fix it in ten seconds.

Run a first pass on the two files. If everything is there, acknowledge briefly and
move straight on — three or four words, not an inventory:

> Got them. Last one:
>
> **Step 3 — Export your store data**
> In Shopify: **Orders > Export**, choose **Orders by date**, set the same dates you
> used in Meta, plain CSV format.

Confirming receipt is worth it; listing back what they just sent is not. "Got them,
30 days, three campaigns, and you pulled the click/view split..." tells someone
nothing they did not already know and costs them a paragraph to read.

If the click/view split is missing, that is worth a message:

> One thing: the export doesn't have the click/view breakdown, so I won't be able
> to separate view-through conversions from real clicks — which is normally the
> biggest piece. Worth re-exporting with those two columns ticked while you're
> still in there. If you'd rather not, I'll run it anyway and note the limit.

Same for a window under 30 days, dates that do not line up between the two files,
or an export with no purchase column at all. Anything they can repair from the
screen they are already on, say now. Anything else, note it and carry on.

## Step 2: Ask the three things the files cannot tell you

Dates, currency, campaign names, refund data and the deduplicated total all come
out of the files now, so never ask for any of them. Three things genuinely cannot
be derived, none of them blocking:

1. **Does the store export contain all their revenue?** If they also sell on
   Amazon, in retail, through a second store or via subscriptions billed
   elsewhere, the denominator is understated and every gap is overstated.
2. **The attribution setting.** Default on Meta is 7-day click plus 1-day view.
   Sets the lookback used to size the edge effect.
3. **Do the ad account and the store share a timezone?** They usually do not.

Ask all three in one short message with the defaults offered. If they do not know,
assume the defaults and note the assumption in the report.

### The fallback, when there is only one ad export

The second export is what supplies the deduplicated total. Without it, ask them to
open Ads Manager for the same period with **no breakdown applied** and read off
Purchases and Purchase conversion value, then pass those as `--claimed-total` and
`--claimed-revenue-total`.

Prefer the export whenever you can get it. A typed number fails silently in four
ways — a typo, the wrong date range, the wrong metric, or a different attribution
setting active when they read it — and each one produces a clean-looking report
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
  --store-covers-all-revenue \
  --attribution-window 7d_click_1d_view \
  --timezone-shift-hours 0 \
  --out reconciliation.json
```

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
  are close, say so — a clean bill of health is worth as much as a finding, and it
  is what makes the reader believe you the day you do find something.
- **The campaign table.** `by_campaign` usually shows the gap concentrated
  somewhere. Retargeting and Advantage+ campaigns are the usual offenders, because
  they harvest people who were already going to buy.

## Step 5: Write the narrative

Write the interpretation to a markdown file (`narrative.md`). Use
`references/report-template.md` for structure and tone.

Keep the writing plain. Numbers first, adjectives never. If the finding is small,
say it is small — a reader who catches you overstating once will discount
everything else in the document.

Headings become `## `, paragraphs stay plain, and `- ` lines become bullets. That
is the whole format; nothing else is parsed.

## Step 5b: Deliver the finding in the chat, before the file

The moment they have been waiting for since the first message. Give them the number
in the conversation, in two or three sentences, before you mention any file. A
report they have to open to learn the answer wastes the only moment of real
attention you get.

> Here it is. Meta claims 890 purchases. 306 of them, 34%, are view-through:
> people who were shown an ad, never clicked it, and bought anyway. Your
> click-driven numbers hold up against the store data. Those 306 are the whole
> argument.
>
> The practical version: your reported 1.77x ROAS becomes 1.36x on clicks alone.
> And your retargeting campaign carries 53% of its conversions on view-through,
> against 18% for prospecting, so those two are not being judged on the same
> basis right now.

Two rules hold here. **Lead with the number, not with the method** — the method is
in the report and they will read it if they want it. And **if the account is clean,
say so with the same confidence.** "Your numbers hold up" delivered plainly is what
makes them believe you the day you tell them something is wrong.

## Step 6: Build the visual report

```bash
python scripts/build_report.py reconciliation.json \
  --account "Client name" \
  --narrative narrative.md \
  --lang en \
  --out reconciliation-report.html
```

Then hand it over as something they own, not as an attachment:

> Full report is in `reconciliation-report.html` — open it and hit Cmd+P, Save as
> PDF. It's built to be forwarded as-is: every figure has the numbers behind it,
> and the assumptions I had to make are listed at the bottom so nobody can knock
> it over.

It really is built for that — figures never split across a page and tables repeat
their headers.

`--lang fr` produces the same report in French, for a French client or an internal
read. The default is English because the market is US.

Three charts get built, and only three, each answering a question printed above
it. A chart is dropped rather than faked when its data is missing: without the
click/view split, the composition chart does not appear at all. Do not add charts.
Decoration on an analytical report costs more credibility than it buys.

## Step 7: Close with the limit, then the offer

The closing is generated automatically and needs no editing. It states the
structural limit — this compares totals, a standard ad export has no order IDs, so
it cannot say which order came from which ad — then points at where that question
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

**`Ads export is missing required column(s)`** — the error names every header it
found. Usually the export has no Day breakdown (add it under Breakdowns → By Time
→ Day) or the purchase column is named something unexpected. Look at the header
list before guessing.

**`no_overlapping_dates`** — the two exports cover different periods. The error
prints both ranges. Re-export over the same window.

**Order count looks far too high** — the store export ships one row per line item
and the script collapses them by order ID. If `data_quality.unique_orders` is null,
no order-ID column was detected, so every line item counted as an order. Re-export
including the order name or number.

**Claimed purchases look far too high** — expected when `--claimed-total` is
missing. That is the row sum, not the platform's total. See step 2.

**Numbers parse as zero** — usually a European export with `1 234,56` formatting
read as US, or vice versa. The parser handles both, but check the currency column
and the delimiter if totals look wrong by orders of magnitude.

## Files

- `references/how-to-export.md` — click-by-click export instructions for Meta,
  Google, TikTok, Shopify and Stripe. Read before step 1.
- `references/gap-taxonomy.md` — the six causes of a gap and how defensible each
  one is. Read before step 4.
- `references/report-template.md` — report structure and tone. Use in step 5.
- `scripts/reconcile.py` — the reconciliation engine.
- `scripts/build_report.py` — the visual report builder.
- `scripts/columns.py`, `loaders.py`, `gap_analysis.py`, `charts.py`,
  `report_html.py` — their parts.
- `tests/test_pipeline.py` — run it after changing anything in `scripts/`.
- `examples/` — synthetic exports plus a finished report, for testing end to end.


---

Maintained by the team at Metrikia (https://metrikia.io).
