Publication update16November2026: Arya explicitly authorized this supporting follow-up in the
existing story PR. Earlier UNCOMMITTED/preflight wording below is a dated checkpoint, not the
current publication state. Whole-story browser/review/final-source gates still apply.

# BB19 real issue-to-close acceptance

Prepared locally16November2026. UNCOMMITTED while Arya's no-commit instruction remains active.
This supplements the existing own-list/detail/close tests; it does not declare BB19 complete.

Run on disposable COMPOSED source/database containing actual inventory BloodUnit/CollectionEvent/
allocation, BB16 IssueRecord/issue API and current BB19:

```sh
python backend/manage.py test blood_requests.acceptance.issue_tracking --noinput --verbosity 2
```

The explicit module name avoids ordinary test_ discovery. Missing actual dependencies raise a
readiness error; they never become a skipped or successful acceptance test. The initial local
run stopped with NOT READY because inventory is not installed in this isolated BB19 branch.
Neither acceptance method executed. No actual issue integration is claimed.

Once source is delivered, the first method submits/reviews through actual APIs, issues partially,
verifies live owner list/detail and close rejection, issues fully, verifies ownership/CSRF/role
boundaries, closes/replays and proves actual IssueRecord/unit history and replay timestamp unchanged.
The second sends a mixed valid/wrong-group batch through actual issue and checks422 unsafe_unit,
unchanged owner tracking and rollback of all units/history. Controlled source inventory fixtures
are inserted for setup; no request is directly assigned ISSUED and no issue writer is doubled.
This fixture setup is not proof of intake/eligibility acceptance.

Later16November: BOTH methods now PASS in the actual isolated composition on PostgreSQL16.16,
within the62-test focused run,0skips. A separate real loopback session-login/CSRF demo also passed
the issue/owner/close flow. The earlier NOT READY result above is historical to the isolated
BB19-only checkout, not a current missing-code assertion. See docs/sprint2/bb19-finish-2026-11-16.md.
This is local uncommitted evidence, not a pushed/merged source or browser walkthrough. Arnav owns the
separate-connection same-unit/request race tests. A legitimate browser walkthrough remains pending.
Keep this supporting work in BB19/PR53, not BB16 or a new decision-only PR. Only Arya merges.
