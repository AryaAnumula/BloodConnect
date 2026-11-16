# BB22 dataset integration and bounded dispatch — BC-D039

Latest user asks to use the completed synthetic dataset to progress Arya's stories, keeping each PR separate. These BB22 changes stay in existing PR59, not PR60/61/62. No merge/cherry-pick or feature-model takeover.

## Fresh domain operations from dataset identities

```powershell
python backend/manage.py queue_dataset_reminders --dataset ../BloodConnect-Synthetic-Data/datasets/synthetic/bloodconnect-demo-v1/dataset.json
python backend/manage.py dispatch_notifications --watch-seconds 60 --interval-seconds 1 --limit 100
```

Use a dedicated migrated local DEBUG demo database and existing scoped provider approvals. Start the existing private opt-in Node mock with the same internal token and a persistent fresh receipt directory using the established BB22 handoff first. The command verifies the shared manifest and selects the dataset's eligible uncollected on-time/late donor identities. It creates actual current screenings, camps/slots and bookings through existing services, then a third future walk-in booking and its donor cancellation. One preparation transaction rolls back on failure. No health/history projection is overwritten; incompatible actors or existing confirmed bookings are refused. Re-running while those bookings exist does not duplicate/overwrite them; use normal cancellation or a new dedicated database.

All queued reminder intents start from actual booking operations. **No fictional dataset DELIVERED state/receipt is imported.** On-time demo slots start25h+10s after setup, allowing a short real setup margin; late slots start23h ahead. Existing25h scheduling and24h actual-receipt rules remain unchanged. The bounded worker repeatedly reads a fresh clock and dispatches outside business transactions. Watch0(default) preserves one-shot behavior; watch0–3600s, interval1–3600s, limit1–1000. No daemon, service, scheduler or automatic CI is installed. The established at-least-hourly demo operating policy still requires the operator to keep dispatch running during the demonstrated window; this is not an uptime guarantee.

## Repeatable actual transport verifier

```powershell
python scripts/verify_bb22_dataset.py --dataset ../BloodConnect-Synthetic-Data/datasets/synthetic/bloodconnect-demo-v1/dataset.json
```

Requires Node on PATH (or --node absolute executable). Creates only its own disposable local SQLite database and private local Node process/receipt directory, migrates the real schema, queues the real operations, runs14s of bounded polling and verifies two newly persisted format2 receipts and two DeliveryAttempts. Results: on-time DELIVERED/late_booking=false/timing_met=true; late DELIVERED/true/false; cancelled-before-dispatch CANCELLED/no receipt. It terminates only its own Node process and closes/removes its own temporary DB. No browser or real carrier claim.

Local canonical dataset verifier passed with those outcomes, zero imported receipts, correct account recipients and actual domain reader/transport. Nine new targeted tests passed: source-to-booking/cancel, duplicate-demo refusal, bad source, local guard, rollback on second booking failure, default dispatch, bounded/fresh-clock polling, bad watch options and unresolved-policy failure. PostgreSQL regression/evidence is separately recorded for the exact committed source.

Remaining team scope: Ankitha's actual camp-wide cancellation service and coordinated history initialization; independent review/permitted walkthrough. This command demonstrates donor cancellation and does not pretend to implement the camp service. Old mock receipt compatibility limitations remain documented. Only Arya merges; his identity/manual CI remain unchanged.
