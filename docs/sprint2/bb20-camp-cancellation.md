# BB-20 camp cancellation (S2-05 / S2-06; BC-D001, D008, D009)

`POST /api/v1/camps/{camp_id}/cancel`, strict body `{"reason": "<1-240 chars after trimming>"}`.
Active non-superuser STAFF/ADMIN only (service and API); CSRF, session and error envelope as the
other camp routes. Donor appointment cancel stays a separate strict `{}` endpoint with its own
before-start rule.

## Behaviour (`scheduling.services.camps.cancel_camp`)
- One transaction. Lock order: Camp, then ALL linked slots (UUID order), then affected
  CONFIRMED appointments (UUID order). No donor profile lock is taken here, so a donor lock is
  never acquired after an appointment lock.
- The clock is read once after every lock is held. That time is stored in `Camp.cancelled_at`
  and reused as every appointment's `cancelled_at` and every intent's due time.
- Every CONFIRMED linked appointment is cancelled, including ones whose slot already started.
  Already-cancelled appointments keep their original timestamp and get no intent.
- Per newly cancelled appointment: pending/blocked/leased reminders are invalidated, then ONE
  `APPOINTMENT_CANCELLED` intent is stored via the existing provider
  (`enqueue_camp_cancellation`), recipient = donor ACCOUNT id (not profile id).
- Any failure (domain write, invalidation, intent persistence) rolls back everything. A missing
  notification policy surfaces as 503 `reminder_unavailable` and also rolls back.
- Replay on an already CANCELLED camp returns the current representation with the original
  reason/time and creates no new effects, whatever reason is sent.
- Slots and appointments are kept. Bookings against a cancelled camp are refused
  (`slot_unavailable`); donors never see cancelled camps; cancelled camps cannot be edited (422).

## Limits (stated, not hidden)
- Delivery is mocked (private Node mock only; never real SMS/email). Dispatch happens after
  commit via the manual dispatcher; no network call is made while locks are held.
- A send already in flight when the camp is cancelled cannot be recalled; a reminder receipt
  accepted before cancellation stays historical.
- The cancellation is one synchronous transaction; a very large camp may need a later redesign.
  Partial batches are deliberately not used.
- PostgreSQL race evidence comes only from `CancelCampRaceTests`, which are skipped on SQLite.
