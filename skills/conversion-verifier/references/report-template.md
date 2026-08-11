# Narrative template

This file describes **only the narrative** you write to `narrative.md`. It is not
the whole report.

That distinction is the point. `build_report.py` already renders the header, the
contested amount, the break-even tile, the campaign bracket, the composition chart,
the corroboration strip, the caveats and the closing. Everything in this file lands
*between* the figures and the caveats. An earlier version of this template described
a full standalone document, so the narrative duplicated the generated tables and the
report ran to a thousand words. A media buyer who tested it said he had to hunt for
the information. Do not restate a number the figures already show unless you are
using it to make a claim.

## The shape

Two sections. Nothing else is parsed and nothing else belongs.

```markdown
## What this means

**[Claim one, one bold sentence.]**
[At most three lines of support. Every number traceable to the JSON.]

**[Claim two.]**
[At most three lines.]

**[Claim three, if there is a third worth making.]**
[At most three lines.]

## The decision

- **[Instruction naming a campaign and an amount.]** [One line of reasoning.]
- **[Instruction.]** [One line.]
- **[Instruction.]** [One line.]
```

**Hard ceiling: 250 words total.** Three claims maximum, three bullets maximum.
Under is fine. Over is not, and "the account was complicated" is not an exception:
a complicated account needs the three claims that matter picked more carefully, not
a fourth added.

## Choosing the three claims

Rank by what changes a decision, not by what is interesting.

1. **The money and where it sits against break-even.** Lead with
   `economics.contested_revenue` and `economics.breakeven_roas`. If
   `straddles_breakeven` is true, that is almost always claim one: the account is
   profitable or not depending on which figure you believe, and saying so is both
   honest and the most useful sentence in the document.
2. **The campaign that decides.** Find the campaign whose `roas_click_only` falls
   furthest below break-even while carrying real spend. Name it, name the spend.
   If several do, name the largest and say the pattern holds for the others.
3. **Whether the measurement itself is sound.** `claimed.purchases_click` against
   `actual.referrer_paid_social` says whether the tracking holds up. When it does,
   say so: it separates "your tool is broken" from "the platform counts things you
   would not count", and only the second is true most of the time.

If `impossible_excess_is_conclusive` is true, it displaces all of this and becomes
claim one. The platform claimed more purchases than the store recorded orders from
every source combined, which no attribution model can explain.

## Choosing the three instructions

A buyer decides in campaigns and in money. An instruction that names neither is not
an instruction.

- **Good:** "Cut retargeting on half the audience for two weeks. It is the only
  test that settles the 53%, and it puts 22,787 $ at stake either way."
- **Not an instruction:** "Switch reporting to 7-day click." That is a reporting
  change. It may be worth one line inside a claim, never one of the three bullets.
- **Not an instruction:** "Monitor performance closely." Says nothing.

One bullet should usually be what *not* to touch. Telling a buyer which campaigns
are fine is as valuable as telling them which one is not, and it stops the report
reading as an alarm.

## Rules that hold throughout

- **Numbers first, adjectives never.** "31% of claimed revenue" beats "a shocking
  share".
- **Every number traceable to the JSON**, and nothing estimated without being
  labelled as an estimate. The contested amount is already labelled in the report,
  so do not label it a second time in the narrative: once is honest, twice is
  hedging.
- **A campaign within 2% of break-even is at break-even.** Check
  `clicks_vs_breakeven` before writing that something is unprofitable. Calling a
  campaign a loser by a thousandth of a point is exactly the error that makes an
  experienced reader stop trusting the document.
- **If a finding is small, say it is small.** A reader who catches one
  overstatement discounts everything else.
- **No exclamation marks, no urgency language, no bold on scary numbers.** The
  figures above the narrative carry the weight already.

## On the closing

The closing is generated and needs no editing, but the reasoning is worth knowing
so you do not undermine it.

**The offer comes after the value, never instead of it.** Someone who never books
should still be better off for having run the tool.

**The wording does not change when the analysis finds nothing wrong.** A clean
account still cannot answer which order came from which ad, so the same limit and
the same offer apply. Bending a finding to justify the call is the one thing that
would destroy this asset, and an experienced reader spots it instantly.
