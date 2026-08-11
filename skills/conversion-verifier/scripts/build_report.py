from safe_html import esc
#!/usr/bin/env python3
"""
build_report.py - Turn reconciliation JSON into a print-ready HTML report.

Open it and print to PDF (Cmd+P on macOS, Ctrl+P elsewhere, Save as PDF). No
dependencies, no toolchain, no install. That constraint is deliberate: this tool
is handed to marketers, and anything that needs a build step never gets run.

Usage:
    python build_report.py reconciliation.json --account "Client name" --out report.html
    python build_report.py reconciliation.json --narrative narrative.md --out report.html

The narrative file is optional. Supply the interpretation written from the JSON
and it lands in the report body; leave it out and the report ships as figures plus
tables, which is still readable but says less.
"""

import argparse
import json
import sys

from charts import bracket_chart, composition_chart
from report_html import STRINGS, render_page


def _localized(value, strings):
    """Thousands separator follows the report language, not Python's default."""
    return f"{value:,.0f}".replace(",", strings["thou"])


def build_composition_rows(data):
    """Split each campaign's claimed purchases into click-attributed and view-through.

    Only real per-campaign figures are used. Spreading the account-level ratio
    across campaigns would print the same percentage on every row, which reads as
    an analysis while carrying no information, so if the split is missing the
    chart is dropped instead of faked.
    """
    campaigns = [
        {"label": name, "click": metrics.get("click", 0.0), "view": metrics.get("view", 0.0)}
        for name, metrics in list(data["by_campaign"].items())[:6]
    ]
    usable = [row for row in campaigns if (row["click"] + row["view"]) > 0]
    return usable or None





def build_bracket_rows(data, strings):
    """One row per campaign: clicks alone at one end, the declared figure at the other.

    Dropped rather than approximated when the click/view split is missing, for the
    same reason the composition chart is: a bracket with no width would assert that
    the declared figure is uncontested, which is the opposite of what is known.
    """
    rows = []
    for name, metrics in list(data["by_campaign"].items())[:6]:
        low, high = metrics.get("roas_click_only"), metrics.get("roas_declared")
        if low is None or high is None:
            continue
        rows.append({
            "label": name,
            "sub": strings["spend_sub"].format(
                spend=_localized(metrics.get("spend", 0), strings)),
            "low": low,
            "high": high,
            "below_breakeven": bool(metrics.get("below_breakeven_on_clicks")),
            "view_share": metrics.get("view_share"),
        })
    return rows or None


def build_figures(data, strings):
    """Assemble only the charts the data actually supports."""
    figures = []
    brackets = build_bracket_rows(data, strings)
    if brackets:
        figures.append({
            "id": "bracket",
            "title": strings["fig_bracket"],
            "question": strings["q_bracket"],
            "svg": bracket_chart(brackets, data.get("economics", {}).get("breakeven_roas"),
                                 decimal=strings["dec"]),
            "table": _bracket_table(brackets, strings),
        })
    composition = build_composition_rows(data)
    if composition:
        figures.append({
            "id": "composition",
            "title": strings["fig_composition"],
            "question": strings["q_composition"],
            "svg": composition_chart(composition, share_label=strings["share_label"],
                                     pct_space=strings["pct_space"]),
            "table": _composition_table(composition, strings),
        })
    return figures


def _bracket_table(rows, strings):
    header = (f'<tr><th>{strings["th_campaign"]}</th><th>{strings["th_spend"]}</th>'
              f'<th>{strings["th_share"]}</th><th>{strings["bar_click"]}</th>'
              f'<th>{strings["bar_reported"]}</th></tr>')
    body = "".join(
        f"<tr><td>{esc(row['label'])}</td><td>{row['sub']}</td>"
        f"<td>{row['view_share']:.0%}</td>"
        f"<td>{row['low']:.2f}x</td><td>{row['high']:.2f}x</td></tr>"
        for row in rows)
    return header + body


def _composition_table(rows, strings):
    header = (f'<tr><th>{strings["th_campaign"]}</th><th>{strings["leg_click"]}</th>'
              f'<th>{strings["leg_view"]}</th><th>{strings["th_share"]}</th></tr>')
    body = "".join(
        f"<tr><td>{esc(row['label'])}</td><td>{row['click']:.0f}</td>"
        f"<td>{row['view']:.0f}</td>"
        f"<td>{row['view'] / (row['click'] + row['view']):.0%}</td></tr>"
        for row in rows if (row["click"] + row["view"]))
    return header + body




def parse_args():
    parser = argparse.ArgumentParser(description="Build a print-ready HTML report.")
    parser.add_argument("json_path", help="Output of reconcile.py")
    parser.add_argument("--account", default="", help="Client or store name for the header")
    parser.add_argument("--narrative", help="Markdown file holding the written interpretation")
    parser.add_argument("--lang", default="en", choices=["en", "fr"],
                        help="Report language. The tool ships in English (US market); "
                             "French is available for internal review and French clients.")
    parser.add_argument("--out", default="reconciliation-report.html")
    return parser.parse_args()


def main():
    args = parse_args()
    with open(args.json_path, encoding="utf-8") as handle:
        data = json.load(handle)
    if "error" in data:
        print(f"Reconciliation failed: {data.get('message')}", file=sys.stderr)
        return 1

    narrative = ""
    if args.narrative:
        with open(args.narrative, encoding="utf-8") as handle:
            narrative = handle.read()

    strings = STRINGS[args.lang]
    html = render_page(data, build_figures(data, strings), args.account, narrative, args.lang)
    with open(args.out, "w", encoding="utf-8") as handle:
        handle.write(html)
    print(f"Wrote {args.out}. Open it and print to PDF.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
