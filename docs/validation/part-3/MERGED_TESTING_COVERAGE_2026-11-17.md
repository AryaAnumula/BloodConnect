# Merged testing coverage — 17 November 2026

Source: `testing` commit `e4307c6b132aa2786681575764bf7eb5a7ecbd93`. PostgreSQL 16.16, coverage.py 7.17.3, backend production source across 198 files; tests, migrations and explicit acceptance modules omitted from coverage denominator. JavaScript coverage is not measured. No modules or accounts were hidden to increase percentages.

| Metric | Actual | 90% target |
| --- | ---: | --- |
| Statements / lines | 3905 / 4340 = **89.9769585%** | **Not met**; coverage.py's whole-number display rounds to 90% |
| Branch destinations | 809 / 1016 = **79.6259843%** | **Not met** |
| Combined coverage.py metric | **88.0134429%** | **Not met** |

The reduced run executed **833 tests: 832 passed, one failed, zero skipped**. The failing historical inventory import test expects the donor facade to be unavailable, but it is present on the merged branch. The test needs a properly isolated missing-facade negative and real-facade positive path, then retesting. Eight fixed-size 515-account demo-seeder cases were omitted under Arya's earlier request to limit account data; individual small role fixtures remain. This is not an exact 25% representative sample, a full test-plan execution or final acceptance. Browser walkthrough remains outstanding.

Earlier `CODE_COVERAGE_REPORT.md` and `BRANCH_COVERAGE_REPORT.md` document a different commit (`d6e377d`) and must not be presented as current merged-source measurements. This report supersedes their percentages for the `e4307c6` reduced run only. Fix/retest the failure, complete the remaining cases and improve branch coverage through meaningful tests before declaring the 90% target met.
