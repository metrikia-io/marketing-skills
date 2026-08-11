#!/usr/bin/env python3
"""
build_report.py - Turn the channel summary into a client-ready HTML report.

Open it and print to PDF. No dependencies, no toolchain: the person sending this
to a client should not have to install anything to produce it.

The report has three sections, in the order that matters to the reader:

  1. What happened     - the numbers, this period against last
  2. What we did        - the narrative, written from those numbers (the part a
                          person writes by hand today)
  3. What it rests on    - how much of the reported performance can be trusted,
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

from charts import channel_mix_chart
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


METRIC_WORDS = {
    "spend": ("spend", "$"),
    "roas": ("ROAS", "x"),
    "purchases": ("purchases", ""),
}


def _hero(summary):
    """The answer to the question the client opens the file to ask.

    Blended ROAS, because it is the one figure no attribution model can inflate and
    the one a client repeats out loud, followed by the single biggest move of the
    period. Both are read off the summary rather than written, so the report says
    something specific before anyone has written a word of narrative.
    """
    now = summary["totals"]["this"]
    moves = summary["totals"].get("moves") or {}
    roas = now.get("roas")
    if not roas:
        return ""
    lede = (f'blended return on {_fmt(now["spend"], "$")} of spend '
            f'over {esc(summary["period"]["label"])}')
    return (f'<div class="hero"><div class="top">'
            f'<div class="n">{roas:.2f}x</div>'
            f'<div class="lede">{lede} {_delta_badge(moves.get("roas"))}</div></div>'
            f'{_headline_sentence(summary)}</div>')


def _headline_sentence(summary):
    """The biggest material move of the period, stated in one line.

    A channel that did not exist last period has no percentage to move by: the
    aggregator returns `pct: None` and marks it material, which is correct. Reading
    that as a number crashed the whole build the first month anyone launched a new
    channel, which is the most ordinary thing a media buyer does.
    """
    moves = summary.get("headline_moves") or []
    if not moves:
        return ""
    top = moves[0]
    word, unit = METRIC_WORDS.get(top["metric"], (top["metric"], ""))
    size = _fmt(abs(top["absolute"] or 0), "$" if unit == "$" else "",
                2 if unit == "x" else 0)
    tail = size if unit == "$" else f"{size}{unit}"
    if top.get("pct") is None:
        headline = f'{esc(top["channel"])} is new this period'
        return f'<div class="cap">The move of the period: <b>{headline}</b> ({tail} {word}).</div>'
    direction = "up" if top["pct"] > 0 else "down"
    headline = f'{esc(top["channel"])} {word} {direction} {abs(top["pct"]):.0%}'
    return f'<div class="cap">The move of the period: <b>{headline}</b> ({tail}).</div>'


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
    """Ranked by spend, because that is the order a budget conversation follows."""
    spending = sorted((channel for channel in channels if channel["this"]["spend"] > 0),
                      key=lambda channel: -channel["this"]["spend"])
    if not spending:
        return ""
    biggest = spending[0]["channel"]
    rows = [{
        "label": channel["channel"],
        "spend": channel["this"]["spend"],
        "value_label": _mix_label(channel["this"]),
        "emphasis": channel["channel"] == biggest,
    } for channel in spending]
    return channel_mix_chart(rows)


def _mix_label(now):
    roas = f'{now["roas"]:.2f}x' if now.get("roas") else "n/a"
    return f'{_fmt(now["spend"], "$")} spent, {roas} back' 


def _rests_on(store):
    """Section 3: the honesty note, and the bridge, earned by being useful first."""
    refund_line = ""
    if store and not store.get("has_refund_data"):
        refund_line = (" Refunds were not in the store export this period, so revenue is "
                       "gross of returns.")
    return (
        '<div class="rests"><h2>What these numbers rest on</h2>'
        '<p>Every revenue figure above is what the ad platforms claim they produced, and '
        'each platform counts the sales it believes it caused. Those counts overlap, so '
        f'channel revenue adds up to more than the store actually took.{refund_line} '
        'Blended ROAS is the one figure no attribution model can inflate: trust it first.</p>'
        '<p>Crediting each channel against the cash actually collected takes reconciling at '
        'the order level, which is what <a href="https://metrikia.io/">Metrikia</a> does.</p>'
        '<a class="cta" href="https://cal.com/gaetanhamel/metrikia?overlayCalendar=true">'
        'Book a 30-minute review with Gaetan</a></div>')


STYLES = """
:root{--ink:#0b0b0b;--ink2:#3d3c39;--muted:#8a8880;--grid:#e6e5de;
--surface:#ffffff;--panel:#f7f6f2;--up:#0a7d33;--down:#c0392b;
--blue:#2a78d6;--rule:rgba(11,11,11,.12)}
*{box-sizing:border-box}
body{margin:0 auto;padding:40px 32px 56px;background:var(--surface);color:var(--ink);
font:15px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif;
max-width:820px;-webkit-font-smoothing:antialiased}
h1{font-size:22px;margin:0 0 4px;letter-spacing:-.01em;font-weight:600}
h2{margin:42px 0 14px;font-size:11.5px;font-weight:600;letter-spacing:.07em;
text-transform:uppercase;color:var(--muted)}
p{margin:0 0 18px;color:var(--ink2);max-width:65ch}
/* A narrative claim opens with its bold sentence on its own line: the claim is
   the finding, the lines under it are only support. */
p>strong:first-child{display:block;color:var(--ink);font-size:15.5px;margin-bottom:2px}
.meta{color:var(--muted);font-size:13px;margin-bottom:26px}
.hero{border:1px solid var(--rule);border-radius:12px;padding:24px 26px;
background:var(--panel);margin:0 0 10px}
.hero .top{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap}
.hero .n{font-size:50px;font-weight:600;line-height:1;letter-spacing:-.025em}
.hero .lede{color:var(--muted);font-size:15px;max-width:36ch}
.hero .cap{color:var(--ink2);font-size:15px;margin-top:16px;max-width:62ch}
.hero .cap b{color:var(--ink);font-weight:600}
.tiles{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:10px 0 34px}
.tile{border:1px solid var(--rule);border-radius:9px;padding:13px 14px}
.tile .k{font-size:10.5px;color:var(--muted);text-transform:uppercase;
letter-spacing:.05em;line-height:1.35;min-height:28px}
.tile .v{font-size:22px;font-weight:600;margin-top:4px;letter-spacing:-.015em}
.d{font-size:12px;font-weight:600;margin-left:2px}
.d.up{color:var(--up)} .d.down{color:var(--down)} .d.flat{color:var(--muted)}
table{border-collapse:collapse;width:100%;font-size:12.5px;margin:10px 0 0;
font-variant-numeric:tabular-nums}
th,td{text-align:left;padding:6px 10px;border-bottom:1px solid var(--grid)}
th{color:var(--muted);font-weight:500;font-size:10.5px;text-transform:uppercase;
letter-spacing:.04em}
td:not(:first-child),th:not(:first-child){text-align:right}
figure{margin:0 0 18px;break-inside:avoid}
ul{padding-left:0;margin:0;list-style:none;max-width:65ch}
li{margin-bottom:10px;font-size:14.5px;color:var(--ink2);padding-left:16px;position:relative}
li::before{content:"";position:absolute;left:0;top:9px;width:5px;height:5px;
border-radius:50%;background:var(--muted)}
.rests{margin-top:38px;padding-top:18px;border-top:1px solid var(--grid);max-width:65ch}
.rests p{font-size:13.5px}
.cta{display:inline-block;margin-top:6px;font-weight:600;color:var(--blue)}
a{color:var(--blue)}
@media print{body{padding:0;max-width:none;font-size:10.5pt}
@page{size:letter;margin:15mm} h2{margin-top:26px}
figure,.tile,.hero{break-inside:avoid}
thead{display:table-header-group}}
"""


def render(summary, account, narrative):
    period = summary["period"]
    subtitle = period["label"]
    if period.get("compared_to"):
        subtitle += f' vs {period["compared_to"]}'
    channels = summary["channels"]
    body = "".join([
        f'<h1>Performance report{" - " + esc(account) if account else ""}</h1>',
        f'<div class="meta">{esc(subtitle)}</div>',
        _hero(summary),
        _tiles(summary["totals"], summary.get("store")),
        '<h2>What happened</h2>',
        f'<figure>{_channel_chart(channels)}</figure>',
        f'<table>{_channel_table(channels)}</table>',
        '<h2>What we did, and why</h2>',
        narrative_to_html(narrative) or
        '<p style="color:#898781">[Narrative goes here - written from the numbers above.]</p>',
        _rests_on(summary.get("store")),
    ])
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>Performance report{" - " + esc(account) if account else ""}</title>'
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
