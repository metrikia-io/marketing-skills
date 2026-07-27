#!/usr/bin/env python3
"""
End-to-end tests. No framework, no dependencies: run it and read the output.

    python tests/test_pipeline.py

These cover the failure modes that actually cost credibility rather than the ones
that are easy to test. The most important is the deduplication guard: a report
built on summed breakdown rows is wrong in a way an experienced reader spots
immediately, so the guard has a test that fails loudly if anyone removes it.
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
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {name}" + (f"  - {detail}" if detail and not condition else ""))


def run_reconcile(*args):
    """Invoke the CLI the way a user does, so argument wiring is covered too."""
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "reconcile.py"),
         "--ads", str(EXAMPLES / "meta_export.csv"),
         "--orders", str(EXAMPLES / "shopify_orders.csv"), *args],
        capture_output=True, text=True, check=False)
    return json.loads(result.stdout), result.returncode


def test_dedup_guard():
    """Without the account-level total, no conclusive claim may be made.

    This is the guard that keeps the tool from repeating the mistake it exists to
    expose. If it ever regresses, every report the skill produces becomes
    dismissible by anyone who opens their own Ads Manager.
    """
    print("\nDeduplication guard")
    _check_unverified_state()
    _check_verified_state()


def _check_unverified_state():
    data, _ = run_reconcile()
    check("row sum is flagged as unreliable",
          data["claim_source"]["basis"] == "summed_breakdown_rows"
          and data["claim_source"]["reliable"] is False)
    check("conclusive claim is blocked",
          data["gap"]["impossible_excess_is_conclusive"] is False,
          "a gap was declared conclusive from summed rows")
    check("blocking caveat is present",
          any(item["id"] == "unverified_claim_basis" and item["severity"] == "blocking"
              for item in data["caveats"]))


def _check_verified_state():
    data, _ = run_reconcile("--claimed-total", "890")
    check("supplied total replaces the row sum",
          data["claimed"]["purchases"] == 890.0,
          f'got {data["claimed"]["purchases"]}')
    check("row sum is kept for reference",
          data["claim_source"]["row_sum_for_reference"] > 890.0)
    check("inflation is measured",
          data["gap_breakdown"][0]["cause"] == "breakdown_sum_inflation"
          and data["gap_breakdown"][0]["measured"] is True)


def test_parsing():
    """Real exports arrive in several languages and number formats."""
    print("\nParsing")
    from columns import parse_date, parse_number

    cases = [("1,234.56", 1234.56), ("1 234,56", 1234.56), ("€1.234,56", 1234.56),
             ("1234", 1234.0), ("", 0.0), ("-", 0.0), ("N/A", 0.0)]
    for raw, expected in cases:
        check(f"number {raw!r} -> {expected}", abs(parse_number(raw) - expected) < 0.01,
              f"got {parse_number(raw)}")

    for raw in ("2026-06-01", "06/01/2026", "2026-06-01 14:30:00",
                "2026-06-01T14:30:00Z", "2026-06-01 14:30:00 +0200"):
        check(f"date {raw!r} parses", parse_date(raw) is not None)
    check("garbage date returns None", parse_date("not a date") is None)


def test_line_item_dedup():
    """Shopify emits one row per line item; counting them as orders inflates everything."""
    print("\nStore export handling")
    from loaders import load_orders

    orders = load_orders(str(EXAMPLES / "shopify_orders.csv"))
    check("line items collapse into orders",
          orders["unique_orders"] is not None
          and orders["unique_orders"] < orders["row_count"],
          f'{orders["unique_orders"]} unique from {orders["row_count"]} rows')
    check("refund signal detected", orders["has_refund_data"] is True)
    check("referrer signal detected", orders["has_referrer_data"] is True)


def test_window_handling():
    print("\nWindow handling")
    with tempfile.TemporaryDirectory() as tmp:
        shifted = Path(tmp) / "orders_next_year.csv"
        _shift_year(EXAMPLES / "shopify_orders.csv", shifted)
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "reconcile.py"),
             "--ads", str(EXAMPLES / "meta_export.csv"), "--orders", str(shifted)],
            capture_output=True, text=True, check=False)
        data = json.loads(result.stdout)
        check("non-overlapping windows error clearly",
              data.get("error") == "no_overlapping_dates")
        check("both ranges are reported back",
              data.get("ads_range") and data.get("orders_range"))
        check("failure exits non-zero", result.returncode == 1)


def _shift_year(source, destination):
    rows = list(csv.DictReader(open(source, encoding="utf-8-sig")))
    with open(destination, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        for row in rows:
            row["Paid at"] = row["Paid at"].replace("2026-", "2027-")
            writer.writerow(row)


def test_missing_split_drops_chart():
    """A chart with no data behind it is dropped, never filled with an average."""
    print("\nChart honesty")
    from build_report import build_composition_rows
    from report_html import STRINGS

    with_split = json.loads(_reconcile_json("--claimed-total", "890"))
    rows = build_composition_rows(with_split)
    check("composition rows use real per-campaign figures",
          rows and len({round(row["view"] / (row["click"] + row["view"]), 3)
                        for row in rows}) > 1,
          "every campaign shows the same ratio, which means it was averaged")

    stripped = {**with_split, "by_campaign": {
        name: {key: value for key, value in metrics.items() if key not in ("click", "view")}
        for name, metrics in with_split["by_campaign"].items()}}
    check("chart is dropped when the split is missing",
          build_composition_rows(stripped) is None)
    check("both languages expose every string key",
          set(STRINGS["en"]) == set(STRINGS["fr"]),
          str(set(STRINGS["en"]) ^ set(STRINGS["fr"])))


def _reconcile_json(*args):
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "reconcile.py"),
         "--ads", str(EXAMPLES / "meta_export.csv"),
         "--orders", str(EXAMPLES / "shopify_orders.csv"), *args],
        capture_output=True, text=True, check=False)
    return result.stdout


def test_report_build():
    """The report has to build in both languages without leaking the other one."""
    print("\nReport build")
    with tempfile.TemporaryDirectory() as tmp:
        recon = Path(tmp) / "recon.json"
        recon.write_text(_reconcile_json("--claimed-total", "890",
                                         "--claimed-revenue-total", "121000"))
        for lang, marker, foreign in (("en", "The figures", "Les chiffres"),
                                      ("fr", "Les chiffres", "The figures")):
            out = Path(tmp) / f"report-{lang}.html"
            subprocess.run(
                [sys.executable, str(SCRIPTS / "build_report.py"), str(recon),
                 "--lang", lang, "--out", str(out)],
                capture_output=True, text=True, check=False)
            html = out.read_text()
            check(f"{lang} report builds", marker in html)
            check(f"{lang} report has no {foreign!r} leak", foreign not in html)
            check(f"{lang} report carries both links",
                  "cal.com/gaetanhamel" in html and "metrikia.io" in html)
            check(f"{lang} report has a table twin per figure",
                  html.count("<table>") >= html.count("<figure>"))


def test_html_injection():
    """Untrusted inputs must render as text, never execute.

    The report is built to be forwarded to a client or a boss, so an unescaped
    value runs in the recipient's browser, not the author's. Campaign names come
    from the ad export, the account name from the command line, and the narrative
    quotes both, so all three are attacker-reachable and all three are tested.
    """
    print("\nHTML injection")
    with tempfile.TemporaryDirectory() as tmp:
        html = _build_report_with_payloads(Path(tmp))

    check("no raw <script> from any input", "<script>" not in html,
          f'{html.count("<script>")} raw <script> tags survived')
    check("no active <img onerror> tag", "<img src=x onerror" not in html)
    check("no event handler on a real tag",
          not re.search(r"<[a-zA-Z][^>]*\son\w+\s*=", html),
          "an active event-handler attribute survived on a real tag")
    check("the payload is present as escaped text",
          "&lt;script&gt;" in html,
          "escaping removed the text entirely instead of neutralising it")


def _build_report_with_payloads(tmp):
    """Run the full pipeline with a hostile campaign name, account and narrative."""
    evil_ads = tmp / "evil.csv"
    _inject_campaign_name(EXAMPLES / "meta_export.csv", evil_ads,
                          "<script>alert(document.cookie)</script>")
    recon = tmp / "recon.json"
    recon.write_text(subprocess.run(
        [sys.executable, str(SCRIPTS / "reconcile.py"),
         "--ads", str(evil_ads),
         "--ads-totals", str(EXAMPLES / "meta_export_totals.csv"),
         "--orders", str(EXAMPLES / "shopify_orders.csv")],
        capture_output=True, text=True, check=False).stdout)
    narrative = tmp / "n.md"
    narrative.write_text("## <img src=x onerror=alert(1)>\n\n"
                         "Text with <script>fetch('//evil')</script> in it.\n")
    report = tmp / "r.html"
    subprocess.run(
        [sys.executable, str(SCRIPTS / "build_report.py"), str(recon),
         "--account", "<script>steal()</script>", "--narrative", str(narrative),
         "--out", str(report)], capture_output=True, text=True, check=False)
    return report.read_text()


def _inject_campaign_name(source, destination, payload):
    rows = list(csv.DictReader(open(source, encoding="utf-8-sig")))
    for row in rows:
        if "Prospecting" in row["Campaign name"]:
            row["Campaign name"] = payload
    with open(destination, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def test_escaping_preserves_formatting():
    """Escaping must not eat the legitimate bold/italic the narrative relies on."""
    print("\nEscaping keeps real formatting")
    sys.path.insert(0, str(SCRIPTS))
    from safe_html import esc, narrative_to_html

    check("plain text is escaped", esc("<b>&") == "&lt;b&gt;&amp;")
    out = narrative_to_html("This is **bold** and *italic*.")
    check("bold survives", "<strong>bold</strong>" in out)
    check("italic survives", "<em>italic</em>" in out)
    evil = narrative_to_html("**<script>x</script>**")
    check("bold around a payload stays inert",
          "<strong>&lt;script&gt;" in evil and "<script>" not in evil)


def test_eu_number_and_total_row():
    """European number formats and a trailing Total row must not corrupt totals."""
    print("\nEU numbers and total-row guard")
    from columns import parse_number
    from loaders import load_ads
    cases = [("1.234", 1234.0), ("1,234", 1234.0), ("1,23", 1.23),
             ("1.234,56", 1234.56), ("(1,234)", -1234.0)]
    for raw, expected in cases:
        check(f"parse_number({raw!r}) == {expected}",
              abs(parse_number(raw) - expected) < 0.01, f"got {parse_number(raw)}")
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "meta.csv"
        path.write_text(
            "Campaign name,Day,Amount spent (USD),Purchases,Purchases conversion value\n"
            "Prospecting,2026-06-01,100,10,1000\nProspecting,2026-06-02,100,10,1000\n"
            "Total,,200,20,2000\nTotal,2026-06-02,200,20,2000\n")
        ads = load_ads(str(path))
    total_purchases = sum(day["purchases"] for day in ads["daily"].values())
    check("total rows (dated and undated) are skipped", total_purchases == 20.0,
          f"got {total_purchases}")
    check("no phantom Total campaign", "Total" not in ads["by_campaign"])


def test_sanity_check_uses_full_row_sum():
    """A legit total must not be blocked when orders cover fewer days than ads."""
    print("\nSanity check against full row sum")
    from loaders import load_ads, load_orders
    from reconcile import reconcile
    with tempfile.TemporaryDirectory() as tmp:
        ads_path = Path(tmp) / "meta.csv"
        rows = ["Campaign,Day,Amount spent,Purchases,Purchases conversion value"]
        for day in range(1, 11):  # 10 days, 10 purchases each -> full row sum 100
            rows.append(f"P,2026-06-{day:02d},100,10,1000")
        ads_path.write_text("\n".join(rows) + "\n")
        orders_path = Path(tmp) / "orders.csv"
        order_rows = ["Name,Paid at,Total"]
        for day in range(1, 4):  # orders cover only 3 of the 10 days
            order_rows.append(f"#{day},2026-06-{day:02d} 12:00:00,90")
        orders_path.write_text("\n".join(order_rows) + "\n")
        result = reconcile(load_ads(str(ads_path)), load_orders(str(orders_path)),
                           {"claimed_total": 80})  # 80 <= full sum 100, legal
    check("legit total is not falsely blocked",
          result["claim_source"]["reliable"] is True,
          f'sanity={result["claim_source"].get("sanity")}')


def main():
    print("conversion-verifier test suite")
    for suite in (test_dedup_guard, test_parsing, test_line_item_dedup,
                  test_window_handling, test_missing_split_drops_chart,
                  test_report_build, test_html_injection,
                  test_escaping_preserves_formatting,
                  test_eu_number_and_total_row,
                  test_sanity_check_uses_full_row_sum):
        suite()
    failed = [name for name, ok, _ in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} passed")
    if failed:
        print("Failed: " + ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
