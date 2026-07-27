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

from charts import composition_chart, daily_chart, roas_chart
from report_html import STRINGS, render_page


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


def build_roas_values(data, strings):
    """Reported ROAS, ROAS on clicks alone, and blended MER, on one axis."""
    claimed = data["claimed"]
    reported = claimed.get("roas")
    mer = data["blended"].get("mer_true_revenue_over_spend")
    if not reported:
        return None
    values = [{"label": strings["bar_reported"], "value": reported}]
    click_only = _click_only_roas(claimed, reported)
    if click_only:
        values.append({"label": strings["bar_click"], "value": click_only,
                       "emphasis": True})
    if mer:
        values.append({"label": strings["bar_mer"], "value": mer})
    return values


def _click_only_roas(claimed, reported):
    click = claimed.get("purchases_click")
    total = claimed.get("purchases")
    if not click or not total:
        return None
    return round(reported * click / total, 2)


def build_daily_series(data, max_points=60):
    """Claimed purchases against recorded orders, day by day."""
    days = [{"date": date, "claimed": values["claimed_purchases"],
             "actual": values["actual_orders"]}
            for date, values in sorted(data["daily"].items())]
    return days[:max_points] if len(days) > max_points else days


def build_figures(data, strings):
    """Assemble only the charts the data actually supports."""
    figures = []
    composition = build_composition_rows(data)
    if composition:
        figures.append({
            "id": "composition",
            "title": strings["fig_composition"],
            "question": strings["q_composition"],
            "svg": composition_chart(composition),
            "table": _composition_table(composition, strings),
        })
    figures.extend(_value_figures(data, strings))
    return figures


def _value_figures(data, strings):
    figures = []
    roas = build_roas_values(data, strings)
    if roas:
        figures.append({
            "id": "roas",
            "title": strings["fig_roas"],
            "question": strings["q_roas"],
            "svg": roas_chart(roas),
            "table": _roas_table(roas, strings),
        })
    days = build_daily_series(data)
    if len(days) > 2:
        figures.append({
            "id": "daily",
            "title": strings["fig_daily"],
            "question": strings["q_daily"],
            "svg": daily_chart(days),
            "table": _daily_table(days, strings),
        })
    return figures


def _composition_table(rows, strings):
    header = (f'<tr><th>{strings["th_campaign"]}</th><th>{strings["leg_click"]}</th>'
              f'<th>{strings["leg_view"]}</th><th>{strings["th_share"]}</th></tr>')
    body = "".join(
        f"<tr><td>{esc(row['label'])}</td><td>{row['click']:.0f}</td>"
        f"<td>{row['view']:.0f}</td>"
        f"<td>{row['view'] / (row['click'] + row['view']):.0%}</td></tr>"
        for row in rows if (row["click"] + row["view"]))
    return header + body


def _roas_table(values, strings):
    header = f'<tr><th>{strings["th_measure"]}</th><th>{strings["th_value"]}</th></tr>'
    body = "".join(f"<tr><td>{esc(item['label'].replace('|', ' '))}</td>"
                   f"<td>{item['value']:.2f}x</td></tr>" for item in values)
    return header + body


def _daily_table(days, strings):
    header = (f'<tr><th>{strings["th_date"]}</th><th>{strings["th_claimed"]}</th>'
              f'<th>{strings["th_orders"]}</th></tr>')
    body = "".join(f"<tr><td>{esc(day['date'])}</td><td>{day['claimed']:.0f}</td>"
                   f"<td>{day['actual']:.0f}</td></tr>" for day in days)
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
