# Integration plan — 17 November 2026

1. Mount inventory API and page routes (prepared in this local checkout). Django check and route-resolution smoke pass; full access/CSRF integration awaits testing.
2. BB21 #51 and BB20 #45 were merged by Arya into testing. This branch now applies the BB21 seeder companion patch; verify it together with the evaluator/facade from current testing. On a clean source export of testing 5ef8c058 plus this branch's integration files, 12 seeder and 2 route-wiring tests passed on SQLite; prior isolated PostgreSQL16 composition passed 12 seeder tests. Final testing-source checks remain.
3. Merge BB23 #60 after preserving both dashboard and issue reporting selectors. BB20 and BB23 published matching camp summary readers; confirm one canonical source and current behavior.
4. Run controlled donor history reconciliation before any history-v2 switch; preserve existing real or synthetic data. Finish group tests and browser walkthrough against the actual integrated testing SHA.
5. Complete the independent Part 3 report and coverage work against the completed testing source. The full-suite coverage and 85% target are not yet established.

This integration branch was based on testing d6e377d; its seeder change depends on the donor evaluator now present after #51. This PR remains a partial integration checkpoint. Do not push directly to shared branches. Only Arya merges.
