# BB-21 temporary deviations and open items (draft PR)

## Appointment responses omit `reminder_state` (TEMPORARY DEVIATION)
The proposed appointment schema requires `reminder_state`; responses still omit it. This integration
checkpoint creates a real outbox intent during booking and invalidates it during donor cancellation,
but the response mapping is not implemented. Do not claim that a reminder was delivered merely
because an intent exists. The transport is a mock and requires explicit operation. Camp cancellation,
real PostgreSQL integrated races, response mapping and end-to-end acceptance remain draft blockers.

## Decisions applied (Arya, 14 Nov)
- Booking a slot that has started (including exactly at its start) is refused: 409 `slot_unavailable`, rechecked after the locks are taken.
- A camp time change must keep every linked slot inside the camp interval, empty slots included (BC-D005). Conflicting changes are rejected (409 `slot_conflict`); slots are never moved or deleted silently. Per BC-D005, cancelled and historical slots count too. No endpoint reactivates a slot today; if one is added it must recheck the camp interval.
- Donor self-cancellation (POST /api/v1/appointments/<id>/cancel): own confirmed appointment only, before the slot starts (422 `invalid_transition` at or after start), idempotent, history kept (status CANCELLED + cancelled_at), capacity never released twice. This checkpoint invalidates pending reminders in the cancellation transaction; integrated PostgreSQL evidence is pending.
- Migration `0002` is included with the matching models for draft review; its contents and deletion rules (PROTECT) still need review.
