# TransactSafe — Data Quality Test Report

*Generated: 2026-07-30 13:15*

## Summary

- **Total tests:** 18
- **Passed:** 18
- **Failed:** 0
- **Pass rate:** 100.0%

## Coverage by Test Category

| Category | Passed | Failed | What it protects against |
|---|---|---|---|
| not_null | 9 | 0 | Ensures critical fields are never missing — catches incomplete or corrupt source records. |
| accepted_values | 1 | 0 | Ensures categorical fields only contain expected values — catches unexpected data drift. |
| relationships | 2 | 0 | Ensures foreign keys always reference a valid parent record — catches orphaned data before it reaches reporting. |
| unique | 6 | 0 | Ensures no duplicate primary keys exist — catches upstream retry/dedup failures. |

## Why This Matters

In a real fraud detection pipeline, silent data quality failures are worse than no pipeline at all — a broken foreign key or a duplicated transaction could mean a fraud case gets missed, or a legitimate account gets wrongly flagged. This test suite runs automatically as part of the Airflow DAG on every scheduled run, so any regression is caught immediately rather than discovered downstream in a report.