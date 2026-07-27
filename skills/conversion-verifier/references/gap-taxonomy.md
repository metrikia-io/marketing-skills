# The six causes of a conversion gap

Read this before interpreting any reconciliation output. A gap between what an
ad platform claims and what a store recorded is normal and expected. What
matters is which cause produced it, because the causes are not equally
defensible, and only one of them is worth acting on.

Ordered from most legitimate to least.

---

## 1. Cross-channel overlap (structural)

**What happens.** A store's total orders include organic search, email, direct,
affiliate, SMS and everything else. The ad platform only claims a subset.

**Why it matters here.** It means store total > platform claim is the *normal*
state. Comparing a platform's claimed purchases against the store TOTAL is
therefore the friendliest possible benchmark for that platform - you are letting
it take credit for every sale from every channel.

**The consequence that makes this the sharpest test available.** If claimed
purchases still exceed the store total, the excess cannot exist. The platform
claims to have sold more than the business sold in total. No attribution model
produces that, no window explains it, no timezone shifts it. This is the finding
nobody can argue with, so when it appears it leads the report.

`gap.impossible_excess_is_conclusive` flags this case.

---

## 2. Attribution date shifting (legitimate)

**What happens.** The platform stamps a conversion on the day of the *click*,
not the day of the *purchase*. Someone clicks on the 3rd and buys on the 9th;
the platform reports that sale on the 3rd. The store reports it on the 9th.

**Size.** Proportional to lookback divided by window length. Over a 30-day
window with a 7-day lookback, roughly 23% of the comparison sits in the
distorted zone at the edges. Over a 7-day window it is 100% and the comparison
is close to meaningless.

**What to do.** Never run this on a short window and present it as conclusive.
The script sizes the effect in `gap_breakdown[].estimated_max_share` - quote it
rather than ignoring it.

---

## 3. Timezone mismatch (legitimate)

**What happens.** The ad account runs on one timezone, the store on another. Up
to a full day of orders slides across the window boundary.

**Size.** Bounded by roughly one day of volume, so on a 30-day window it is
noise, and on a 7-day window it matters.

**What to do.** Ask for both timezones and pass `--timezone-shift-hours`. If
they do not know, note the assumption in the report and move on.

---

## 4. Refunds and cancellations (legitimate)

**What happens.** The purchase event fires once, at checkout. The refund happens
days later and is never sent back to the platform. Claimed revenue stays
inflated permanently.

**Size.** Typically 3 to 10% of orders in DTC, higher in apparel.

**Why it is worth naming even though it is legitimate.** It is legitimate as a
*mechanism* and still real as a *loss*. The buyer is optimizing toward revenue
that was returned. Measured whenever the store export includes a refund amount
or a financial status column.

---

## 5. View-through conversions (contested)

**What happens.** Someone is served the ad, does not click, buys within 24 hours
through some other path, and the platform claims the sale. Meta counts these by
default under its 1-day view setting.

**Size.** Commonly 10 to 30% of claimed purchases. Retargeting campaigns run far
higher, because they serve ads to people who were already going to buy.

**Why it is contested rather than legitimate.** The mechanism is real -
impressions do influence people. But the platform is grading its own homework on
a claim it cannot substantiate, and the counterfactual is untested: many of
those buyers were converting regardless. This is the single largest lever a
platform has to inflate its own numbers, and it is enabled by default.

**How to handle it.** If the export includes the click/view split, report the
measured share and let it speak. If not, say it could not be measured and give
the typical range - do not invent a figure for this account.

---

## 6. The unexplained residual

**What it is.** What remains after subtracting everything above. Over-attributed
conversions with no defensible mechanism behind them.

**Why it is the only number worth acting on.** The first five have explanations
a buyer can accept and work around. This one does not. It is the part of the
claimed performance that has nothing behind it, and it is the part that leads to
scaling a campaign that is not working.

**How to state it.** Show the arithmetic. Claimed, minus refunds, minus measured
view-through, minus the edge allowance, equals residual. A reader who can follow
the subtraction will trust the remainder. A reader handed a number without the
path to it will not.

---

## The cross-check that survives every objection

Blended MER - total store revenue divided by total ad spend - uses no
attribution model at all. Nothing in this taxonomy can distort it.

When claimed ROAS sits far above MER and paid is the dominant channel, the
platform is claiming credit that the business as a whole does not show. When
they sit close together, the account is broadly honest, and saying so is a real
finding worth reporting with the same confidence as a problem.

---

## What this analysis structurally cannot do

A standard ad export is aggregated by campaign and day. It contains no order
IDs. So this can prove that claimed sales exceed real ones, and it can size the
categories of gap. It cannot tell you which specific order came from which
specific ad.

That requires order-level identity resolution reconciled against money actually
collected, which is a different class of tool. Say so in the report. Naming the
boundary of a method is what separates an analysis from a sales pitch.
