# Unit and automated test report — Part 3

**Scope: partial testing, not final acceptance.** Source: testing commit `d6e377d3ba361730841f51e0fe48720cce0c056f`; executed 17 November 2026 against a clean source export and a disposable PostgreSQL 16.16 test database. Coverage.py 7.17.3 collected branch data. Tests are synthetic and include unit, API and integration-oriented Django classes; they are not presented as 103 pure unit tests.

| Execution | Result | Scope |
| --- | --- | --- |
| Focused Django run | **103 passed, 0 failed, 0 skipped**; 200.890 s test time | accounts login; donor evaluator; request issue and tracking; inventory intake/stock; activity reports; notification provider |
| Frontend Node suite | **109 passed, 0 failed, 0 skipped** | All `tests/*.test.mjs`; DOM/API mocks, not browser walkthroughs |
| Reduced broad Django run | **770 run: 760 passed, 2 errors, 8 skipped**; 927.331 s | Eight fixed-size seeder tests excluded; dashboard provider modules unmerged; seven donor-integration cases and one dashboard case skipped |
| Full current testing-branch browser run | **NOT RUN** | Local browser-control initialization failed |

Django command (from repository root, with private PostgreSQL test environment and coverage):

```text
python -m coverage run --branch --source=backend --omit=*/tests/*,*/migrations/*,*/acceptance/* backend/manage.py test accounts.tests.test_login donors.tests.test_evaluation blood_requests.tests.test_issue_integration blood_requests.tests.test_tracking_api inventory.tests.test_intake inventory.tests.test_stock_orm reporting.tests.test_activity notification_adapter.tests.test_provider --noinput --verbosity 2
```

Frontend command: `node --test tests/*.test.mjs`. The reduced-run log has 765 readable test-result lines in `BACKEND_EXECUTED_TESTS.txt`; five other lines were interleaved with other output and are not listed. The runner summary is authoritative; frontend outcomes are in `FRONTEND_EXECUTED_TESTS.txt`. The earlier 103-test focused run has its own outcome in this table. The prior 53-test uninstrumented focused run overlaps this suite and must not be added to the 103 as new unique cases. The original unlabeled discovery command found zero tests and is not counted.

Inventory tests can use test-only URL configuration; real app routing was independently checked and inventory API/page routes are missing from testing. Separate code/branch coverage and system validation reports contain the limits and next steps. Cases not mapped individually remain NOT ASSESSED in the test-case document.

## Reduced run errors and exclusions

Two `inventory.tests.test_domain_consumers` tests error because `reporting.selectors.dashboard` and `reporting.providers.dashboard` are not in testing until BB23 is integrated. Eight cases were skipped (seven require the BB21 donor tranche; one requires the camp-summary provider). The fixed-size 515-account seeder class (eight tests) was excluded entirely; small per-test role fixtures remain. The 770-test run is **FAILED**, not a complete pass.
