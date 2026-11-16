# Team next actions —16 November2026

> **BC-D037 supersedes combined packaging:** Arya requires one story per feature PR. BB22 changes stay in existing PR59. BB23/dashboard and BB24/activity reporting have moved to separate team/arya-bb23 and team/arya-bb24 PRs based directly on testing. Their code/routes/tests are removed from this PR with an additive commit; the earlier combined checkpoint and655/121 test evidence below are historical, not current-head validation. Prior integrated teammate work is preserved. Only Arya merges. See [story separation](story-pr-separation-2026-11-16.md).


Use current shared `testing` as the released integration baseline. New work on PR59 is **not merged** there. For dependent development, coordinate the exact current `team/arya-scheduling-provider-integration` head with Arya before incorporating its code; retain your own changes and test the resulting tree. Do not open duplicate providers/models or silently apply older overlapping PR diffs. Only Arya performs merges.

## Completed Arya-controlled changes in the current PR59 draft

- PR45/46/51 bases changed from main to testing without changing heads or draft status.
- Actual appointment reminder-state projection, no fabricated missing-intent state, transactional response-projection rollback.
- Dispatcher PostgreSQL concurrency tests for a live lease and in-flight cancellation CAS preservation; transport cannot recall an already in-flight accepted send.
- Real local Node mock receipt integration covers23-hour late and exactly25-hour on-time bookings; actual provider acknowledgment, late flag and24-hour timing outcome checked separately.
- Dashboard/report API, pages, admin gates, date/UTC orchestration, live request/camp aggregates and fail-closed stock/event dependencies. No stock/issue model invented and no fake zero totals.
- Existing shared policy conflicts/BB19 ownership/tests preserved. Exact scoped decisions/providers are in [Arya work decisions](arya-work-2026-11-16.md).
- Old BB22 microsecond replay limitation fixed with receipt format2. Legacy/unknown fingerprint versions return503 unchanged pending authoritative reconciliation; no auto-migration/deletion/reissue. See BB22 handoff for compatibility requirements.
- Exact implementatione1bedee passed [manual PostgreSQL16 run43830110568](https://github.com/AryaAnumula/BloodConnect/actions/runs/43830110568):655 Django,121 Node/frontend,29 availability tests, zero skips. Subsequent evidence-only documentation retains identical runtime/test/config source.

## Yashwitha — remaining BB13–15 providers

Your published helper draft is present; the actual models, migrations and allocation/reporting selectors are still needed. Use the existing four components, quantity1, event/component constraints, protected history, explicit synthetic configured policy and profile-lock/history transaction rules already approved in shared-rules.md. No new design-approval hold is needed for those exact clauses.

Publish actual model/migration/provider commit and test evidence, including the existing donors0003 dependency. Coordinate evaluator/version/projection reconciliation with Ankitha; errors are not 'no confirmed history'. Do not reset/rewrite applied migrations. Real stock must sum usable AVAILABLE rows, not an independent counter.

For Arya's dashboard/report implement the public selectors in arya-work-2026-11-16.md. `stock_summary` returns available_quantity, distinct group/component rows and truthful pagination. For collection DateField counts, convert the shared aware UTC report bounds to local Asia/Kolkata dates and use the same half-open local interval; for discard/issue timestamp records use the UTC bounds directly. Count confirmed collection events once, units separately and explicit discards once; do not count expiry as a discard. Return zero only after a successful empty query. Do not create clinical defaults or fake totals to make a dashboard turn green.

## Arnav — remaining BB16 and issue reporting

BB17/18 are already on main. Continue independent issue-side validation/service/UI while waiting for real inventory; final issue migration/integration must reference Yashwitha's actual model, migration and error imports. One outer transaction locks request then sorted units, creates unique protected issues, updates fulfilled state; partial remainsAPPROVED and full becomesISSUED. No stock counter/notification event invented; no requester closure in your story.

Provide real `blood_requests.selectors.reporting.request_issue_totals(*,start=None,end=None)` with issued_unit_count from IssueRecord timestamps and quantities. The dashboard's separate pending_request_count is already implemented from actual SUBMITTED requests. Issue history cannot be reconstructed from current fulfilled totals. Publish actual provider SHA and PostgreSQL race/rollback/reconciliation evidence for Arya's final BB19/24 integration.

## Ankitha — remaining BB20/21 and history

Your PR46/51 (and45) now target testing. Their referenced heads are already represented in59; reconcile later work on the current integration tree without reverting donor freshness, overlap, FOR NO KEY UPDATE or all-linked-slot checks.

The response reminder_state mapping is now implemented: real PENDING/BLOCKED/LEASED -> publicPENDING, with terminal provider states preserved; missing state503. Do not reintroduce the draft omission or fabricate PENDING. Booking and donor cancellation persist state/intent changes and DTO projection in their atomic transaction.

Implement the remaining camp-cancel service/API against the existing provider: lock camp->sorted slots->appointments; set camp and confirmed appointments cancelled; invalidate reminders and enqueue exactly one camp-cancellation intent per affected appointment with the persisted timestamp; roll back all domain/intent writes on in-transaction failure. Replays retain original timestamps and create no new effects. Delivery happens after commit and cannot undo domain cancellation. Keep records for history, preserve capacity semantics and include appropriate PostgreSQL races/rollback evidence. Do not make network calls under those locks.

Coordinate the real donors evaluator argument, current-history snapshot/readers, initialization/backfill and history-v2 configuration with Yashwitha before existing-data enablement. The final history-stale rule is a snapshot/projection mismatch in either direction, not only 'collection date later'. Booking must continue to serialize against collections under the donor profile lock. No donors->inventory runtime import.

## Arya — merge and final acceptance checklist

1. Review actual PR59 head/diff and its matching manual PostgreSQL result; earlier run hashes are not evidence for newer source changes.
2. Decide which checkpoint to merge personally. Do not count all included stories complete merely because the draft combines them; main/testing do not change until you merge.
3. After any merge, manually verify the actual resulting testing SHA and functional demo. Later promote through a separate reviewed testing->main merge commit and retain testing; these merges are your actions.
4. For BB19 full acceptance, complete actual submit->review->partial issue->final issue->owner tracking->close once BB16 exists. For BB23/24, reconcile real inventory/event/issue totals; current valid requests return503 until those providers exist.
5. Browser walkthrough still needs a permitted user-run session; previous automation was blocked on URL confidence. Do not label Node/HTTP tests a browser walkthrough or bypass that block.
6. Older overlapping drafts44/45/46/51/53/55/56/57/58 should be reviewed against the integration log before you decide whether to close/merge them. This handoff neither closes nor merges them and does not authorize a second application of already included changes.
