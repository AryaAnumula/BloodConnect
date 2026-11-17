# BloodConnect system validation report — Part 3

**Status: INCOMPLETE; do not interpret as release acceptance.** Prepared 17 November 2026 for the College Software Engineering mini-project, using the submitted Team5 STP v1.1 and the official Part-3 PDF. Measured source is testing commit `d6e377d3ba361730841f51e0fe48720cce0c056f`; it does not include unmerged BB20 #45, BB21 #51 or BB23 #60. Actual execution results are separated from planned or teammate-reported work.

| Area | Evidence and actual result | Status |
| --- | --- | --- |
| Request, issue, owner tracking | On exact testing source, the targeted PostgreSQL16.16 run covering `blood_requests.tests.test_issue_integration` and `test_tracking_api` passed as part of 53 tests, zero skips. Actual unit/service/API tests are not a complete visual system walkthrough. | Bounded automated checks PASS; full UI flow NOT RUN |
| Inventory routes and access | `inventory.tests.test_intake` and `test_stock_orm` passed within the same run using test-specific URL configurations. A direct resolver inspection of real `config.urls` found `/api/v1/blood-units` and `/staff/inventory` NOT MOUNTED. | FAIL/BLOCKED for public route system validation; apply and verify the existing integration patch |
| Dashboard | `/api/v1/dashboard` NOT MOUNTED; BB23 #60 remains unmerged and conflicts in the shared request reporting selector. | BLOCKED on this build |
| Activity reports | `reporting.tests.test_activity` passed in the 53-test run and `/api/v1/reports` resolves. Does not prove every production-like data case or a browser walkthrough. | Bounded checks PASS; complete system validation NOT RUN |
| Security | Existing focused test modules and frontend tests exercise some ownership, invalid input and role boundaries. Full SEC-TC-01–20 mapping, TLS/staging checks and security exit review are not yet complete. | PARTIAL; remaining cases NOT ASSESSED |
| Browser/system end-to-end | No actual end-to-end browser walkthrough was run by this agent for the current testing commit. Browser-control initialization failed due to missing local kernel assets. A local demo was launched for Arya with separate synthetic accounts; no user's test outcome is assumed. | NOT RUN |
| Unit/UI automated checks | Node frontend suite: 109 tests passed, 0 failed/skipped on the exact source. PostgreSQL focused backend run: 53 passed, 0 failed/skipped. See UNIT_TEST_REPORT.md for scope and the broader run status. | PASS for executed subsets only |
| Performance and availability | Yashwitha previously reported a synthetic five-client stock-read measurement on a different isolated source; this is not a fresh testing-commit measurement. Seven-day availability was not measured. | NOT ASSESSED on this build |
| Data and configuration | The donor seeder guard patch is not applied to this testing snapshot. History-v2 initialization/reconciliation must be performed and verified for the target database before enabling that mode. | INTEGRATION PENDING |

## Findings and next actions

1. Integrate the inventory route wiring carried as `docs/sprint2/patches/inventory-routes.patch`, then verify role, CSRF and actual HTTP behavior on testing.
2. Integrate the BB21 donor evaluator/facade and companion seeder patch, with controlled history reconciliation; verify on an isolated target DB.
3. Resolve BB23's request reporting-selector conflict while preserving both pending-request and issue-total providers; reconcile the duplicate camp reader with BB20.
4. Finish the unmerged booking UI and camp cancellation work; run the corresponding actual role-based browser flows and notification mock receipt checks.
5. Run the remaining STP cases, capture per-case evidence and both code/branch coverage on the final testing SHA; verify security/NFR and obtain team review before marking acceptance.

The source project is a local demonstration with synthetic data. No clinical suitability, real notification carrier, production availability, or unmeasured performance is claimed.

## Reduced broad run update

PostgreSQL16.16 run on the same testing SHA: 770 executed, 2 errors, 8 skipped, 760 passed; eight full-size seeder cases excluded. Errors are missing BB23 dashboard modules; skipped cases depend on donor/camp sources not yet merged. 89.60% statement and 79.22% branch coverage apply only to this reduced run. The branch target above 85% is not met.
