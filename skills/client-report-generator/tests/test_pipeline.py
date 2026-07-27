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


def main():
    print("client-report-generator test suite")
    for suite in (test_channel_detection, test_period_comparison, test_single_period,
                  test_over_attribution_is_visible, test_html_injection,
                  test_report_build):
        suite()
    failed = [name for name, ok, _ in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} passed")
    if failed:
        print("Failed: " + ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
