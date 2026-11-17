# Sprint 2 integration and conflict log

> **BC-D037 supersedes combined packaging:** Arya requires one story per feature PR. BB22 changes stay in existing PR59. BB23/dashboard and BB24/activity reporting have moved to separate team/arya-bb23 and team/arya-bb24 PRs based directly on testing. Their code/routes/tests are removed from this PR with an additive commit; the earlier combined checkpoint and655/121 test evidence below are historical, not current-head validation. Prior integrated teammate work is preserved. Only Arya merges. See [story separation](story-pr-separation-2026-11-16.md).


## 16 November 2026 — Arya pending-work execution

The amendments here supersede corresponding pending notes in the historical15 November snapshot below. Follow [BC-D036 and provider contracts](arya-work-2026-11-16.md) and [remaining team actions](team-next-actions-2026-11-16.md). This is still the shared **draft PR59**, not a merge or final acceptance of every included story.

- PR45/46/51 now target testing. Their heads950b5fe/d3f2dd3/faf570e and draft status were preserved; no PR was merged or closed.
- Commit94c7fa2 exposes real appointment reminder states, rolls booking/cancellation back if response projection fails, adds real PostgreSQL dispatcher race tests and checks actual Node receipts for23-hour late and exactly25-hour on-time bookings. This completes the public-state mapping previously pending for Ankitha.
- Commitd3faf28 adds ADMIN dashboard/report APIs and pages, strict dates/roles, real request/camp counts and fail-closed inventory/issue provider boundaries. No competing inventory/issue models or fake zero counts were added. Full BB23/24 data integration remains pending the providers in BC-D036.
- Manual PostgreSQL16 run [43828870029](https://github.com/AryaAnumula/BloodConnect/actions/runs/43828870029) passed exact sourced3faf281f2703636b4c71d7b7ea091dcdecf1f2b:655 Django tests in152.558s,118 Node/frontend tests,29 availability tests, zero skips, clean migrations/system/repository checks. Dispatcher races and real local mock receipt integration executed. Test doubles used in report orchestration do not prove actual inventory/issue integration.
- Commite1bedee fixes the older microsecond receipt-fingerprint limitation with version2 and meaningful restart/conflict/offset/legacy-preservation tests. Unversioned/unknown records fail closed503 unchanged; no unverifiable migration or deletion. Local Node service tests:11 pass,1 POSIX-permissions check skipped on Windows; the manual Linux run is recorded separately below.
- Final exact implementation heade1bedee169a57bc1bb29d8463ba744bca2559021 passed existing manual PostgreSQL16 run [43830110568](https://github.com/AryaAnumula/BloodConnect/actions/runs/43830110568):655 Django tests in157.744s,121 Node/frontend tests,29 availability tests, all zero skips. Clean migrations/system/repository checks. Local general and Sprint2 validators passed; the Windows general validator requires Python -X utf8 to avoid its inherited cp1252 default. Subsequent evidence-only documentation changes do not alter runtime/test/config source relative to this tested head.

Remaining dependencies: Yashwitha's actual inventory models/migration, stock/allocation and collection/wastage selectors; Arnav's BB16 issue model/service/report selector; BB19 actual issue-to-tracking-to-close acceptance; Ankitha's camp-cancellation service and coordinated donor-history evaluator/projection initialization. Independent review and a permitted functional browser walkthrough remain separate acceptance work. No browser walkthrough or real carrier delivery is claimed.

Only Arya merges. Main/testing source, collaborator access, Git identity and manual-only workflow configuration were not changed by this execution. Commits use Arya's existing author identity without assistant coauthor trailers. The original Arya checkout's10 ownership edits were preserved.

## 15 November 2026 — common draft and conflict decisions

Scope: synthetic university demo. `testing` at `97614c8` remains the shared baseline. PR #59 (`team/arya-scheduling-provider-integration`) is the single **unmerged** integration draft. It is not the same tree as `testing` and is not final acceptance. Teammates whose work needs its changes may fetch and integrate the exact current #59 head into their own branches, preserve their changes, resolve conflicts with the affected owner, and test the result. Communicate the integrated commit to Arya; no new PR is needed unless he asks. Only Arya merges; no existing PR has been closed or merged by this reconciliation.

### Open PR comparison at the time of this audit

| PR | Relationship to #59 and final integration decision |
| --- | --- |
| #45 BB-20 (`950b5fe`) | Commit is an ancestor of #59. Camp create/update work is already present; do not apply the old diff a second time. Camp cancellation is still incomplete. |
| #46 BB-21 (`d3f2dd3`) | Commit is an ancestor. The later history branch and #59 include the history freshness, profile-lock and overlap improvements absent from this older head. Carry forward later code; do not revert to #46's older eligibility/locking logic. |
| #51 BB-21 history (`faf570e`) | Commit is an ancestor. #59 integrates it with the notification provider and later freshness/overlap fixes. Future Ankitha changes must be reconciled on top, not discarded. |
| #56 BB-13 (`57c29f5`) | Commit is an ancestor. Its helper-only inventory draft is present; Yashwitha's unpublished models and migration are not. Integrate her later commit when shared. |
| #57 overlap decision (`d84dfa9`) | Commit is an ancestor, and the decision and its code and test are included. No separate application is needed. |
| #58 inventory registration (`93b71c3`) | Commit is not an ancestor. A trial merge conflicts in `backend/config/settings.py` because #59 also adds scheduling; its one-line inventory registration is already independently present **alongside** scheduling and blood_requests. Preserve all three apps; do not merge this duplicate change over #59. |
| #55 provider (`ad696c8`) | Commit is an ancestor. Use this newer provider and its 25-hour scoped policy; don't overwrite it with #44's older snapshot. Delivery remains mock only. |
| #44 provider (`33a9978`) | Earlier provider history is not an ancestor of #59; #55 carries and extends its work on the newer base, with later fixes and limitations. Treat #55/#59 as the integration source, not a byte-identical copy and not evidence of real delivery. Compare any future #44-only edits before deciding whether they must be ported. |
| #53 BB-19 (`9dd7324`) | Reconciled into the #59 integration draft. Request tracking/closure and their tests are included, but real BB-16 issue-to-tracking remains pending. Preserve the BB-17 submission and BB-18 staff queue. |

These are snapshots; fetch and compare any new commits before incorporating them. GitHub still shows #45/#46/#51 based on `main`, so their displayed diffs contain earlier stack work. They are not evidence that a later teammate update has been integrated.

### Resolved conflicts and binding demo decisions

1. **#53 decision register:** keep the #59 scoped Sprint 2 decisions, notification scopes and BB-21 overlap clause; add the BB-19 BC-D035 scoped records. Parent proposals stay proposed where applicable. Scope approvals do not imply clinical approval or merge approval.
2. **#53 endpoint documentation:** BB-19 requester tracking/closure belongs to Arya and BB-18 staff queue to Arnav. Preserve the existing role dispatch. Camp create/cancel is STAFF or ADMIN under BC-D001; do not restore the old ADMIN-only proposal. Camp cancellation is still not implemented.
3. **#53 check runner:** preserve inventory, scheduling, notification, request, donor and existing suites; add the BB-19 request-tracking frontend tests. Do not replace either side's checks with the other.
4. **Inventory app registration:** retain `inventory.apps.InventoryConfig` with `scheduling` and `blood_requests`; the settings conflict with #58 is an already-applied duplicate, not a reason to remove either app.
5. **Donor-history order:** inventory owns the outer transaction. Lock and validate the donor profile first, check current eligibility and reject a new event before the latest confirmed date, update the donor projection before inserting the new event and first unit, and roll everything back together on failure. An additional compatible component on an existing event is not another donation. The existing projection service is idempotent and does not itself authorize a new event. Yashwitha and Ankitha must coordinate the real evaluator/interface and migration; see `s2-10-donors-notes.md`.
6. **Freshness:** a mismatch in either direction between the assessment's confirmed-history snapshot and the profile projection is stale. Saved results, donor search and booking must reflect stale rules or stale history. Projection reconciliation/backfill and the coordinated history-rules version remain to be implemented before enabling existing data.
7. **Appointments:** a donor may hold confirmed appointments only in non-overlapping half-open intervals, including across walk-ins and camps; adjacent slots are allowed and cancelled appointments do not block. The current booking service checks under the donor profile lock and returns `appointment_conflict` for overlap. Same-slot duplicate may retain `duplicate_booking`.
8. **Notifications:** booking/cancellation outbox integration in #59 uses the single provider; a queued intent is not a delivered message. Cancellation delivery failures after commit cannot roll back domain changes. An already in-flight send cannot be recalled. `reminder_state` response mapping, camp cancellation and real delivery are not complete.
9. **BB-13/16 ownership:** Yashwitha supplies the actual inventory model, migration, stock selector and allocation provider. Arnav may implement independent request-side work now, but real BB-16 integration and its dependent migration wait for that provider and its actual commit/error types. Request then UUID-sorted units lock in one transaction; no separate stock decrement counter or issue notification requirement.

### Progress and verification

- Prior exact #59 head `b8200b9`: manual PostgreSQL 16 run [43729999153](https://github.com/AryaAnumula/BloodConnect/actions/runs/43729999153) passed 612 Django tests, including cross-slot race and booking-to-local-mock receipt, with clean migrations and repository checks. This is evidence for that head only.
- This reconciliation adds #53 and resolves the overlapping files as above. Local contract/repository validation and request-tracking frontend checks are run separately; run the manual PostgreSQL workflow on the actual resulting commit before using it as integration-test evidence.
- Remaining work includes Yashwitha's unpublished inventory models/migration/allocation and reconciliation, Arnav's real BB-16 issue integration, BB-19's issue-to-tracking acceptance, Ankitha's camp cancellation and reminder-state mapping, and the provider's documented in-flight cancellation limitation. Tests of already implemented pieces do not complete these stories. No real SMS/email or real-donor use is claimed.
