# BB-21: confirmed appointment overlap

Decision recorded 15 November 2026 by Codex under Arya's delegated project-decision authority, for the Sprint 2 demo.

A donor may have more than one confirmed appointment when their slot intervals do not overlap. A donor must not have two confirmed appointments with overlapping slot intervals, whether the slots belong to the same camp, different camps, or a walk-in. Treat intervals as half-open: an appointment ending exactly when another starts does not overlap. Cancelled appointments do not block a new booking. Existing eligibility and capacity rules still apply; this decision does not change clinical donation intervals.

For a new booking, acquire the existing Camp → Slot → DonorProfile lock order, then check the donor's confirmed appointments for `existing.start < new.end` and `existing.end > new.start` while holding the donor profile lock. Reject an overlap with HTTP 409 and a stable `appointment_conflict` code; no appointment or reminder intent may persist on rejection. The same-slot duplicate may retain its existing duplicate-booking response. The profile lock serializes concurrent bookings for the same donor, including across camps and walk-in slots. Any future operation that changes a confirmed appointment's slot or slot times must enforce the same rule and lock ordering before it can be enabled.

Add PostgreSQL concurrency coverage for competing overlapping bookings across different slots, including walk-in versus camp, plus adjacent, non-overlapping, cancelled and same-slot cases. Document the response in the API contract. This decision is an addition to the scoped Sprint 2 scheduling rules; it does not change the overall or parent approval statuses or authorize a merge.

## Evidence and limits

PostgreSQL documents that `FOR NO KEY UPDATE` locks conflict with one another, while they do not conflict with `FOR KEY SHARE`. The lock is effective only if every relevant booking or modification path takes it before checking; the database does not automatically enforce this cross-row predicate. PostgreSQL also defines inclusive and exclusive range bounds; this decision uses `[start, end)` for unambiguous adjacency. See [PostgreSQL 16 row locks](https://www.postgresql.org/docs/16/explicit-locking.html#LOCKING-ROWS) and [range types](https://www.postgresql.org/docs/16/rangetypes.html). These sources support the engineering mechanics, not a clinical policy or a claim that the draft implementation has passed tests.
