Publication update16November2026: Arya explicitly authorized this supporting follow-up in the
existing story PR. Earlier UNCOMMITTED/preflight wording below is a dated checkpoint, not the
current publication state. Whole-story browser/review/final-source gates still apply.

# BB22 camp-cancellation/provider acceptance

Prepared locally16November2026, UNCOMMITTED under Arya's active no-commit instruction.
Current booking/donor-cancel/provider regression is already implemented. Atomic camp cancellation
is still Ankitha's BB20 implementation; this acceptance does not implement it or declare BB22 done.

On disposable composed source with actual camp cancellation and Node24 on PATH:

```sh
python backend/manage.py test notification_adapter.acceptance.camp_cancellation --noinput --verbosity 2
```

The explicit module is outside ordinary test_ discovery. Missing cancel route or Node is a FAILED
readiness gate, never a skip/success. The initial local run stopped NOT READY at the absent actual
camp-cancellation route; no acceptance method executed or mock delivery was claimed.

Prepared method: real bookings create three actual outbox reminders; controlled persisted queue
states cover PENDING/BLOCKED/LEASED. Actual STAFF cancel API must cancel appointments, invalidate all
three reminders/leases and enqueue one cancellation per appointment with account UUID and persisted
camp cancellation time. Replay preserves history/time/counts. The real dispatcher then calls a
temporary private Node service and verifies exactly three durable format2 IN_APP mock receipts,
only for cancellations; redispatch sends none. No mocked success transport or real carrier.

This method is UNVERIFIED past the dependency gate until Ankitha's code arrives. It supplements
existing provider/rollback/timing tests; it does not replace PostgreSQL camp/slot/cancel races,
failure injection, full criteria or browser evidence. Keep it in BB22/PR59. Only Arya merges.
