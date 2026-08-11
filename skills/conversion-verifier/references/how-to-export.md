# Getting the two exports

The person running this is a marketer, not an engineer. Walk them through it in
your own words rather than pasting this file at them. Two files are needed: what
the ad platform claims, and what the store recorded, over the same dates.

Aim for **at least 30 days**. Shorter windows are dominated by attribution edge
effects and the result stops meaning much.

---

## Meta Ads (Facebook / Instagram)

1. Open **Ads Manager** → **Campaigns**.
2. Set the date range. 30 days minimum, 60 or 90 is better.
3. **Columns** → **Customize Columns**.
4. Tick these, then untick the rest so the file stays readable:
   - Campaign name
   - Amount spent
   - Purchases
   - **Purchases (click)** and **Purchases (view)** ← the two that matter most
   - Purchases conversion value
   - Impressions
5. Tick **Save as preset** if they will do this again.
6. **Breakdowns** → **By Time** → **Day**. Without this the file has no dates
   and the comparison cannot run.
7. **Reports** → **Export** → **.csv**.
8. **Then export a second time with the Day breakdown turned off.** Same columns,
   same dates, Breakdowns → By Time → None. That second file is what supplies the
   deduplicated totals.

**Why two files.** Meta documents that a report broken down by day can show one
conversion in several rows, so adding the rows up produces a number Meta itself
would never report. The export without the breakdown avoids that multiplication,
which is what makes the final figures defensible. It is one extra click and it
replaces a number typed by hand, which is where mistakes come from.

**Why the click/view split matters.** View-through conversions - sales credited
to people who saw the ad and never clicked - are usually the largest contested
slice of the gap and are counted by default. Without those two columns they stay
invisible and the report is meaningfully weaker. It is worth two extra clicks.

**Where to read their attribution setting.** It sits at the top of the columns
panel, usually "7-day click, 1-day view". Note it; it feeds the analysis.

---

## Google Ads

1. **Campaigns** → set the date range.
2. **Columns** → **Modify columns** → add Conversions, Conv. value, Cost.
3. **Segment** → **Time** → **Day**.
4. Download → **.csv**.

Note that Google's "Conversions" column can include several conversion actions
at once. If it does, they should segment by conversion action and keep only
purchases, otherwise the comparison counts leads as sales.

---

## TikTok Ads

**Campaign** → date range → **Custom columns**: Cost, Complete Payment, Complete
Payment Value → **Breakdown by Day** → **Export**.

---

## Shopify

1. **Orders** → **Export**.
2. Choose **Orders by date** and set the same range as the ad export.
3. Choose **Plain CSV file**.

The export ships one row per line item, so a three-product order appears three
times. The script collapses these by order name automatically - no cleanup
needed.

**Keep these columns if given the choice:** Name, Paid at (or Created at),
Total, Financial Status, Refunded Amount, Currency, Referring Site.
Financial Status and Refunded Amount are what let refunds be measured instead of
guessed at.

---

## Stripe

1. **Payments** → **Export**.
2. Same date range.
3. Columns: id, Amount, Amount Refunded, Currency, Created (UTC), Status.

Stripe timestamps are UTC. If the ad account is not on UTC, that difference is
what `--timezone-shift-hours` corrects.

---

## WooCommerce and everything else

Any orders export works if it has a date column and an amount column. The script
detects column names across languages and formats. If it cannot find something,
the error names every header it did see, which usually makes the problem obvious.

---

## The four questions worth asking

Everything else comes out of the files, including the deduplicated total once the
second ad export is there. These four do not:

1. **Gross margin.** The one that decides whether any ROAS in the report is good
   news. Break-even ROAS is 1 divided by the margin, so 62% margin means 1.61x.
   Pass it as `--gross-margin 62`. A rough figure beats none.
2. **Does the store export contain all the revenue?** Amazon, retail, a second
   store or subscriptions billed elsewhere all break the comparison.
3. **Attribution setting in the ad account.** Default on Meta is 7-day click,
   1-day view.
4. **Do the ad account and the store share a timezone?** Ads Manager shows the ad
   account timezone in the top bar; Shopify shows it under Settings > General.

If they do not know, assume the defaults and note the assumption in the report. An
assumption stated is fine; an assumption hidden is not.
