#!/usr/bin/env python3
"""
End-to-end tests. No framework, no dependencies: run it and read the output.

    python tests/test_pipeline.py

The two that matter most: multi-channel detection from filenames (a mislabeled
channel silently corrupts a client-facing report), and HTML escaping (the report
is forwarded to a client, so an unescaped value runs in their browser).
"""

import csv
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
EXAMPLES = ROOT / "examples"
sys.path.insert(0, str(SCRIPTS))

RESULTS = []


def check(name, condition, detail=""):
    RESULTS.append((name, bool(condition), detail))
    print(f"  [{'PASS' if condition else 'FAIL'}] {name}"
          + (f"  — {detail}" if detail and not condition else ""))


def _aggregate(*extra):
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "aggregate.py"),
         "--this", str(EXAMPLES / "meta_june.csv"), str(EXAMPLES / "google_june.csv"),
         "--last", str(EXAMPLES / "meta_may.csv"), str(EXAMPLES / "google_may.csv"),
         "--orders", str(EXAMPLES / "shopify_june.csv"),
         "--orders-last", str(EXAMPLES / "shopify_may.csv"), *extra],
        capture_output=True, text=True, check=False)
    return json.loads(result.stdout)


def test_channel_detection():
    print("\nChannel detection and aggregation")
    data = _aggregate()
    names = {row["channel"] for row in data["channels"]}
    check("both channels detected from filenames", names == {"Meta", "Google"},
          f"got {names}")
    for row in data["channels"]:
        check(f"{row['channel']} has a real ROAS",
              row["this"]["roas"] and row["this"]["roas"] > 0,
              f'ROAS is {row["this"]["roas"]} — a column probably went undetected')


def test_period_comparison():
    print("\nPeriod-over-period")
    data = _aggregate()
    moves = data["totals"]["moves"]
    check("spend move is computed", moves and moves["spend"]["pct"] is not None)
    check("headline moves are surfaced", len(data["headline_moves"]) > 0)
    check("a sub-threshold move is not called material",
          all(abs(h["pct"]) >= 0.10 for h in data["headline_moves"]),
          "an immaterial move leaked into the headline list")


def test_single_period():
    print("\nSingle period (no comparison)")
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "aggregate.py"),
         "--this", str(EXAMPLES / "meta_june.csv"),
         "--orders", str(EXAMPLES / "shopify_june.csv")],
        capture_output=True, text=True, check=False)
    data = json.loads(result.stdout)
    check("runs without a comparison period", "error" not in data)
    check("moves are absent rather than fabricated",
          data["totals"]["moves"] is None)


def test_over_attribution_is_visible():
    """The whole wedge: channel revenue should exceed what the store recorded."""
    print("\nOver-attribution shows through")
    data = _aggregate()
    channel_revenue = sum(row["this"]["revenue"] for row in data["channels"])
    store_revenue = data["store"]["revenue"]
    check("summed channel revenue exceeds store revenue",
          channel_revenue > store_revenue,
          f"channels {channel_revenue:.0f} vs store {store_revenue:.0f}")


def test_html_injection():
    """The report is forwarded to a client, so untrusted values must not execute."""
    print("\nHTML injection")
    html = _build_with_payloads()
    check("no raw <script> survives", "<script>" not in html)
    check("no event handler on a real tag",
          not re.search(r"<[a-zA-Z][^>]*\son\w+\s*=", html))
    check("payload is present as escaped text", "&lt;script&gt;" in html)


def _build_with_payloads():
    with tempfile.TemporaryDirectory() as tmp:
        evil = Path(tmp) / "meta_june.csv"
        _inject(EXAMPLES / "meta_june.csv", evil, "<script>alert(1)</script>")
        summary = Path(tmp) / "s.json"
        summary.write_text(subprocess.run(
            [sys.executable, str(SCRIPTS / "aggregate.py"), "--this", str(evil),
             "--orders", str(EXAMPLES / "shopify_june.csv")],
            capture_output=True, text=True, check=False).stdout)
        narrative = Path(tmp) / "n.md"
        narrative.write_text("## <img src=x onerror=alert(1)>\n\nText.\n")
        out = Path(tmp) / "r.html"
        subprocess.run(
            [sys.executable, str(SCRIPTS / "build_report.py"), str(summary),
             "--account", "<script>steal()</script>", "--narrative", str(narrative),
             "--out", str(out)], capture_output=True, text=True, check=False)
        return out.read_text()


def _inject(source, destination, payload):
    rows = list(csv.DictReader(open(source, encoding="utf-8-sig")))
    for row in rows:
        if "Prospecting" in row.get("Campaign name", ""):
            row["Campaign name"] = payload
    with open(destination, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def test_report_build():
    print("\nReport build")
    with tempfile.TemporaryDirectory() as tmp:
        summary = Path(tmp) / "s.json"
        summary.write_text(json.dumps(_aggregate()))
        out = Path(tmp) / "r.html"
        subprocess.run(
            [sys.executable, str(SCRIPTS / "build_report.py"), str(summary),
             "--account", "Test Co", "--out", str(out)],
            capture_output=True, text=True, check=False)
        html = out.read_text()
    check("report builds", "What happened" in html)
    check("honesty section is present", "What these numbers rest on" in html)
    check("metrikia bridge is present", "metrikia.io" in html)
    check("call link is present", "cal.com/gaetanhamel" in html)


def test_total_row_not_doubled():
    """A trailing Total row (Meta/Google add one) must not double the figures."""
    print("\nTotal-row guard")
    sys.path.insert(0, str(SCRIPTS))
    from aggregate import load_channel
    with tempfile.TemporaryDirectory() as tmp:
        plain = Path(tmp) / "meta_a.csv"
        withtotal = Path(tmp) / "meta_b.csv"
        header = "Campaign name,Day,Amount spent (USD),Purchases,Purchases conversion value\n"
        body = "Prospecting,2026-06-01,100,10,1000\nProspecting,2026-06-02,100,10,1000\n"
        plain.write_text(header + body)
        withtotal.write_text(header + body + "Total,,200,20,2000\nTotal,2026-06-02,200,20,2000\n")
        base = load_channel(str(plain))
        withtot = load_channel(str(withtotal))
    check("total row does not change spend", base["spend"] == withtot["spend"],
          f'{base["spend"]} vs {withtot["spend"]}')
    check("total row does not change purchases", base["purchases"] == withtot["purchases"])


def test_zero_revenue_channel_does_not_crash():
    """A channel with spend but zero revenue must not crash the ROAS chart."""
    print("\nZero-revenue channel")
    sys.path.insert(0, str(SCRIPTS))
    from charts import roas_chart
    try:
        roas_chart([{"label": "Meta", "value": 0.0, "emphasis": True}])
        check("roas_chart survives an all-zero series", True)
    except ZeroDivisionError:
        check("roas_chart survives an all-zero series", False, "ZeroDivisionError")


def test_ambiguous_channel_filename_errors():
    """A filename naming two platforms must error, not silently pick one."""
    print("\nChannel-name safety")
    sys.path.insert(0, str(SCRIPTS))
    from aggregate import channel_of
    try:
        channel_of("/tmp/meta_and_google_june.csv")
        check("ambiguous filename raises", False, "it silently picked a channel")
    except ValueError:
        check("ambiguous filename raises", True)
    check("clean filename resolves", channel_of("/tmp/meta_june.csv") == "Meta")


def test_preamble_zero_report_is_refused():
    """A Google-style title preamble must not yield a silent all-zero report."""
    print("\nZero-report guard")
    with tempfile.TemporaryDirectory() as tmp:
        bad = Path(tmp) / "google_june.csv"
        bad.write_text("Campaign report (Jun 1 - Jun 30)\n\n"
                       "Campaign,Day,Cost,Conversions,Conv. value,Clicks\n"
                       "Brand,2026-06-01,50,5,500,20\n")
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "aggregate.py"), "--this", str(bad),
             "--orders", str(EXAMPLES / "shopify_june.csv")],
            capture_output=True, text=True, check=False)
        data = json.loads(result.stdout)
    # Either the preamble is skipped and real numbers appear, or it is refused —
    # never a silent zero report.
    if "error" in data:
        check("preamble is refused rather than zeroed", True)
    else:
        check("preamble is parsed to real numbers",
              data["totals"]["this"]["spend"] > 0,
              "a zero-spend report was emitted from a preambled file")


def main():
    print("client-report-generator test suite")
    for suite in (test_channel_detection, test_period_comparison, test_single_period,
                  test_over_attribution_is_visible, test_html_injection,
                  test_report_build, test_total_row_not_doubled,
                  test_zero_revenue_channel_does_not_crash,
                  test_ambiguous_channel_filename_errors,
                  test_preamble_zero_report_is_refused):
        suite()
    failed = [name for name, ok, _ in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} passed")
    if failed:
        print("Failed: " + ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
