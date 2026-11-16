# BC-D037 — one story per feature PR

Arya's latest16November2026 instruction corrects the combined reporting packaging in BC-D036. Keep BB22 in existing PR59 and create independent BB23/dashboard and BB24/activity-report PRs directly from testing97614c8. Do not base them on59 or on each other. BB19 remains its own existing PR53. Preserve older integration commits, approved shared definitions and teammate work; do not rewrite history or merge anything.

This additive correction removes reporting app/routes/pages/frontend/tests/domain summary additions from59, retains actual BB22 reminder projection/rollback/dispatch-race/timing and microsecond-fingerprint fixes, and leaves public reporting contracts proposed here. Prior combined655 Django/121 Node evidence is historical; validate each corrected actual source head separately. Only Arya merges; manual CI/access/identity unchanged.

BB23/24 intentionally carry identical minimal common reporting infrastructure. Their API/provider/selector/URL/frontend/test modules are separate and neither branch imports the other feature. During later user-controlled integration preserve each distinct root include/page/test and register the common reporting app once; reconcile shared settings/runner/register metadata without dropping either story. Current stock/camp/issue providers remain honest source dependencies; these story checkpoints do not invent domain models or claim full acceptance.

## Published PRs and verification

| Story | PR and independent source | Manual PostgreSQL16 result |
| --- | --- | --- |
|BB22 existing draft|[PR59](https://github.com/AryaAnumula/BloodConnect/pull/59), source603a3d1; earlier shared donor/request/scheduling integration preserved, BB23/24 code removed|[43832488645](https://github.com/AryaAnumula/BloodConnect/actions/runs/43832488645):642 Django in122.815s,112 Node,29 availability; zero skips; clean migrations/checks.|
|BB23 dashboard|[PR60](https://github.com/AryaAnumula/BloodConnect/pull/60), sourcecde305e, directly testing97614c8|[43832291735](https://github.com/AryaAnumula/BloodConnect/actions/runs/43832291735):402 Django,81 Node,29 availability; zero skips; clean migrations/checks.|
|BB24 reports|[PR61](https://github.com/AryaAnumula/BloodConnect/pull/61), source5875a88, directly testing97614c8|[43832274733](https://github.com/AryaAnumula/BloodConnect/actions/runs/43832274733):403 Django,80 Node,29 availability; zero skips; clean migrations/checks.|

Documentation-only follow-ups retain the tested runtime/test/config source. Both new branches independently pass local contract validators and targeted tests. Comparison confirms the other story's implementation files are absent and common infrastructure is byte-identical. PR59 BB22/provider and prior domain implementation source is unchanged from before the removal; the642-test run executes its dispatch races and actual23/25h booking receipts. No history rewrite, merge, PR closure, main/testing update or CI-trigger change. Older shared baseline is not advertised as a new duplicate feature PR; BB19/20/21 retain their existing feature PRs.
