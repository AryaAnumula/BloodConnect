# Additional branch coverage — 17 November 2026

Production source: testing `e4307c6b132aa2786681575764bf7eb5a7ecbd93`. Coverage.py 7.17.3, PostgreSQL16.16; complete backend production source (198 files), with tests, migrations and acceptance modules excluded from the denominator. JavaScript is not measured. No production paths or accounts were hidden.

Coverage is combined across the earlier 833-test reduced run and subsequent targeted test executions, not a single clean run. It includes an initial exploratory run of five new tests in which one new seeder-policy test errored because its mocked policy was incomplete; the fixture was corrected and all 20 new tests subsequently passed together. Thus this is honest combined execution evidence, not a claim that every contributing invocation passed.

- **Branch: 864 / 1016 = 85.03937%**, exceeding 85% by one branch destination.
- **Statements: 4030 / 4340 = 92.85714%.** Combined line+branch coverage.py metric: 91.37416%.
- New test suite: **20 passed, 0 failed, 0 skipped** on PostgreSQL16.16. Tests cover small synthetic reference reconciliation and failures, account-seeder guards/idempotency, inventory stock/policy/selector safety, scheduling filters, notification dataset validation and seeder input guards.
- Earlier reduced broad suite: **833 run, 832 passed, 1 failed** in the pre-existing historical inventory import test; eight fixed-size 515-account seeder tests excluded due to the account-size request. No exact 25% account sample is claimed. No full end-to-end browser acceptance is claimed.

Machine-readable file `branch-coverage-e4307c6-plus-tests.json.gz` contains per-file branches. Source: existing e4307c6 plus seven newly added test modules. The earlier suite failure, full-size seeder tests and current testing-branch browser acceptance remain outstanding. Final acceptance requires the failure fixed and rechecked and the test results refreshed after merging these tests.
