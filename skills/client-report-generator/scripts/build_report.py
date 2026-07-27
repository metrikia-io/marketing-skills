#!/usr/bin/env python3
"""
build_report.py - Turn the channel summary into a client-ready HTML report.

Open it and print to PDF. No dependencies, no toolchain: the person sending this
to a client should not have to install anything to produce it.

The report has three sections, in the order that matters to the reader:

  1. What happened     — the numbers, this period against last
  2. What we did        — the narrative, written from those numbers (the part a
                          person writes by hand today)
  3. What it rests on    — how much of the reported performance can be trusted,
                          which is the honest note nobody else includes

Section 2 is the whole point. Looker already draws section 1. The work being
replaced is the write-up, and the reason a client keeps an agency is that the
write-up makes the numbers make sense to someone who does not live in Ads Manager.

Usage:
    python build_report.py summary.json --account "Client name" \\
        --narrative narrative.md --out report.html
"""

import argparse
import json
import sys

from charts import roas_chart
from safe_html import esc, narrative_to_html


def _fmt(value, prefix="", digits=0):
    if value is None:
        return "n/a"
    return f"{prefix}{value:,.{digits}f}"


def _delta_badge(move, invert=False):
    """A small up/down badge. invert=True for metrics where down is good (CPA)."""
    if not move or move.get("pct") is None:
        return '<span class="d flat">new</span>' if move and move.get("material") else ""
    pct = move["pct"]
    good = (pct < 0) if invert else (pct > 0)
    arrow = "▲" if pct > 0 else "▼"
    cls = "up" if good else "down"
    return f'<span class="d {cls}">{arrow} {abs(pct):.0%}</span>'


def _tiles(totals, store):
    now = totals["this"]
    moves = totals.get("moves") or {}
    cells = [
        ("Ad spend", _fmt(now["spend"], "$"), _delta_badge(moves.get("spend"))),
        ("Attributed revenue", _fmt(now["revenue"], "$"), _delta_badge(moves.get("revenue"))),
        ("Blended ROAS", f'{now["roas"]:.2f}x' if now.get("roas") else "n/a",
         _delta_badge(moves.get("roas"))),
        ("Store orders", _fmt(store["orders"]) if store else "n/a",
         _delta_badge(store.get("revenue_move")) if store else ""),
    ]
    tiles = "".join(
        f'<div class="tile"><div class="k">{esc(label)}</div>'
        f'<div class="v">{value} {badge}</div></div>'
        for label, value, badge in cells)
    return f'<div class="tiles">{tiles}</div>'


def _channel_table(channels):
    header = ("<tr><th>Channel</th><th>Spend</th><th>Revenue</th><th>ROAS</th>"
              "<th>CPA</th><th>ROAS vs last</th></tr>")
    return header + "".join(_channel_row(channel) for channel in channels)


def _channel_row(channel):
    now = channel["this"]
    moves = channel.get("moves") or {}
    roas = f'{now["roas"]:.2f}x' if now.get("roas") else "n/a"
    cpa = _fmt(now["cpa"], "$") if now.get("cpa") else "n/a"
    return (f'<tr><td>{esc(channel["channel"])}</td>'
            f'<td>{_fmt(now["spend"], "$")}</td>'
            f'<td>{_fmt(now["revenue"], "$")}</td>'
            f'<td>{roas}</td><td>{cpa}</td>'
            f'<td>{_delta_badge(moves.get("roas"))}</td></tr>')


def _channel_chart(channels):
    values = [{"label": c["channel"], "value": c["this"]["roas"] or 0,
               "emphasis": c["this"]["roas"] == max((x["this"]["roas"] or 0)
                                                     for x in channels)}
              for c in channels if c["this"]["spend"] > 0]
    return roas_chart(values) if values else ""


def _rests_on(store):
    """Section 3: the honesty note, and the bridge, earned by being useful first."""
    refund_line = ""
    if store and not store.get("has_refund_data"):
        refund_line = (" Refunds were not in the store export this period, so revenue is "
                       "gross of returns.")
    return (
        '<h2>What these numbers rest on</h2>'
        '<p>Every revenue figure above is what the ad platforms claim they produced. '
        'Platforms grade their own homework: each one counts the sales it believes it '
        'caused, and those counts overlap, so channel revenue adds up to more than the '
        f'store actually took.{refund_line} Blended ROAS is the one figure here that no '
        'attribution model can inflate, because it compares total store revenue to total '
        'spend — trust it first.</p>'
        '<p>To credit each channel against the cash actually collected in Stripe and the '
        'CRM, rather than against what the platform says about its own work, the numbers '
        'have to be reconciled at the order level. That is what '
        '<a href="https://metrikia.io/">Metrikia</a> does, and it is what turns a report '
        'a client half-believes into one they can act on.</p>'
        '<p style="color:#898781;font-size:13px">Want this read on the account with you? '
        'Gaetan, media buying, runs a 30-minute review of the numbers and what to do next, '
        'no charge. <a href="https://cal.com/gaetanhamel/metrikia?overlayCalendar=true">'
        'Book it here</a>.</p>')


STYLES = """
:root{--ink:#0b0b0b;--ink2:#52514e;--muted:#898781;--grid:#e1e0d9;
--surface:#fcfcfb;--up:#0ca30c;--down:#d03b3b;--rule:rgba(11,11,11,.10)}
*{box-sizing:border-box}
body{margin:0;padding:32px;background:var(--surface);color:var(--ink);
font:15px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif;
max-width:820px;margin-inline:auto;-webkit-font-smoothing:antialiased}
h1{font-size:25px;margin:0 0 4px;letter-spacing:-.01em}
h2{font-size:17px;margin:36px 0 12px}
.meta{color:var(--muted);font-size:13px;margin-bottom:24px}
.tiles{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:18px 0}
.tile{border:1px solid var(--rule);border-radius:8px;padding:12px 13px}
.tile .k{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em}
.tile .v{font-size:19px;font-weight:600;margin-top:3px}
.d{font-size:12px;font-weight:600;margin-left:2px}
.d.up{color:var(--up)} .d.down{color:var(--down)} .d.flat{color:var(--muted)}
table{border-collapse:collapse;width:100%;font-size:13px;margin:8px 0;
font-variant-numeric:tabular-nums}
th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--grid)}
th{color:var(--muted);font-weight:500;font-size:11px;text-transform:uppercase;letter-spacing:.04em}
td:not(:first-child),th:not(:first-child){text-align:right}
figure{margin:14px 0;break-inside:avoid}
p{margin:0 0 12px;color:var(--ink2)}
a{color:#2a78d6}
@media print{body{padding:0;max-width:none;font-size:11pt}
@page{size:letter;margin:16mm} h2{margin-top:22px} figure,.tile{break-inside:avoid}
thead{display:table-header-group}}
"""


def render(summary, account, narrative):
    period = summary["period"]
    subtitle = period["label"]
    if period.get("compared_to"):
        subtitle += f' vs {period["compared_to"]}'
    channels = summary["channels"]
    body = "".join([
        f'<h1>Performance report{" — " + esc(account) if account else ""}</h1>',
        f'<div class="meta">{esc(subtitle)}</div>',
        '<h2>What happened</h2>',
        _tiles(summary["totals"], summary.get("store")),
        f'<figure>{_channel_chart(channels)}</figure>',
        f'<table>{_channel_table(channels)}</table>',
        '<h2>What we did, and why</h2>',
        narrative_to_html(narrative) or
        '<p style="color:#898781">[Narrative goes here — written from the numbers above.]</p>',
        _rests_on(summary.get("store")),
    ])
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>Performance report{" — " + esc(account) if account else ""}</title>'
            f'<style>{STYLES}</style></head><body>{body}</body></html>')


def main():
    parser = argparse.ArgumentParser(description="Build a client-ready HTML report.")
    parser.add_argument("summary_path", help="Output of aggregate.py")
    parser.add_argument("--account", default="", help="Client name for the header")
    parser.add_argument("--narrative", help="Markdown file with the write-up")
    parser.add_argument("--out", default="client-report.html")
    args = parser.parse_args()

    with open(args.summary_path, encoding="utf-8") as handle:
        summary = json.load(handle)
    if "error" in summary:
        print(f"Aggregation failed: {summary.get('message')}", file=sys.stderr)
        return 1
    narrative = ""
    if args.narrative:
        with open(args.narrative, encoding="utf-8") as handle:
            narrative = handle.read()

    with open(args.out, "w", encoding="utf-8") as handle:
        handle.write(render(summary, args.account, narrative))
    print(f"Wrote {args.out}. Open it and print to PDF.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
