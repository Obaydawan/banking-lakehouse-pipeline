"""
TransactSafe — Data Quality Report Generator
===============================================
Runs `dbt build --select test_type:generic` (or just parses the last dbt
test run's results) and produces a human-readable Markdown report
summarizing test coverage, pass rate, and what each test category protects
against. Meant to be committed as TEST_REPORT.md for portfolio reviewers.

Run from inside dbt_project/transactsafe/:
    python ../../scripts/generate_test_report.py
"""

import json
from datetime import datetime
from pathlib import Path

RUN_RESULTS_PATH = Path("target/run_results.json")
MANIFEST_PATH = Path("target/manifest.json")
OUTPUT_PATH = Path("../../TEST_REPORT.md")

TEST_CATEGORY_EXPLANATIONS = {
    "unique": "Ensures no duplicate primary keys exist — catches upstream retry/dedup failures.",
    "not_null": "Ensures critical fields are never missing — catches incomplete or corrupt source records.",
    "relationships": "Ensures foreign keys always reference a valid parent record — catches orphaned data before it reaches reporting.",
    "accepted_values": "Ensures categorical fields only contain expected values — catches unexpected data drift.",
}


def categorize_test_name(test_name: str) -> str:
    for category in TEST_CATEGORY_EXPLANATIONS:
        if test_name.startswith(category):
            return category
    return "other"


def main():
    if not RUN_RESULTS_PATH.exists():
        print("ERROR: target/run_results.json not found. Run 'dbt test' first.")
        return

    with open(RUN_RESULTS_PATH) as f:
        results = json.load(f)

    test_results = [
        r for r in results.get("results", [])
        if r.get("unique_id", "").startswith("test.")
    ]

    total = len(test_results)
    passed = sum(1 for r in test_results if r["status"] == "pass")
    failed = total - passed

    by_category = {}
    for r in test_results:
        # dbt unique_id format: test.<package>.<test_name>.<hash>
        # The test name (e.g. "not_null_stg_accounts_account_id") is the
        # second-to-last segment, not the last (which is a hash suffix).
        parts = r["unique_id"].split(".")
        test_name = parts[-2] if len(parts) >= 2 else parts[-1]
        category = categorize_test_name(test_name)
        by_category.setdefault(category, {"pass": 0, "fail": 0})
        if r["status"] == "pass":
            by_category[category]["pass"] += 1
        else:
            by_category[category]["fail"] += 1

    lines = []
    lines.append("# TransactSafe — Data Quality Test Report")
    lines.append(f"\n*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n")
    lines.append(f"## Summary\n")
    lines.append(f"- **Total tests:** {total}")
    lines.append(f"- **Passed:** {passed}")
    lines.append(f"- **Failed:** {failed}")
    lines.append(f"- **Pass rate:** {round(passed / total * 100, 1) if total else 0}%\n")

    lines.append("## Coverage by Test Category\n")
    lines.append("| Category | Passed | Failed | What it protects against |")
    lines.append("|---|---|---|---|")
    for category, counts in by_category.items():
        explanation = TEST_CATEGORY_EXPLANATIONS.get(category, "Custom validation logic.")
        lines.append(f"| {category} | {counts['pass']} | {counts['fail']} | {explanation} |")

    lines.append("\n## Why This Matters\n")
    lines.append(
        "In a real fraud detection pipeline, silent data quality failures are worse than "
        "no pipeline at all — a broken foreign key or a duplicated transaction could mean "
        "a fraud case gets missed, or a legitimate account gets wrongly flagged. This test "
        "suite runs automatically as part of the Airflow DAG on every scheduled run, so any "
        "regression is caught immediately rather than discovered downstream in a report."
    )

    OUTPUT_PATH.write_text("\n".join(lines))
    print(f"Report written to {OUTPUT_PATH.resolve()}")
    print(f"\nSummary: {passed}/{total} tests passed ({round(passed/total*100,1) if total else 0}%)")


if __name__ == "__main__":
    main()
