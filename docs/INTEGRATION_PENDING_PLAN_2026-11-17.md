# Integration plan — 17 November 2026

1. Mount inventory API and page routes (prepared in this local checkout). Django check and route-resolution smoke pass; full access/CSRF integration awaits testing.
2. Merge BB21 #51 and BB20 #45 under Arya's control; then apply the BB21 seeder companion patch together with its evaluator/facade. On unmerged testing the old evaluator does not accept confirmed_collection_date, so applying the caller alone is incompatible. Prior isolated PostgreSQL16 composition passed 12 seeder tests; rerun on final source.
3. Merge BB23 #60 after preserving both dashboard and issue reporting selectors. BB20 and BB23 published matching camp summary readers; confirm one canonical source and current behavior.
4. Run controlled donor history reconciliation before any history-v2 switch; preserve existing real or synthetic data. Finish group tests and browser walkthrough against the actual integrated testing SHA.
5. Complete the independent Part 3 report and coverage work against the completed testing source. The full-suite coverage and 85% target are not yet established.

The two-route change is prepared on an integration branch based on testing d6e377d. This PR is a partial integration checkpoint: donor seeder changes must arrive with #51, not before the evaluator supports their arguments. Do not push directly to shared branches. Only Arya merges.
