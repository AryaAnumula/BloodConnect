# Shared model ownership and migrations — PROPOSED

No models are created by this pack. Do not create migrations until relevant decisions approved. Keep existing User, DonorProfile, EligibilityResult, SecurityEvent and migrations unchanged unless their named owner approves a narrow change.

| Model / module | Minimum relationships/constraints | Primary writer |
| --- | --- | --- |
| inventory.CollectionEvent | UUID; donor FK; collection date; confirmed source for donor-history/reporting; grouping across components; S2-10 must settle capture and uniqueness, no made-up medical workflow | Yashwitha, Ankitha domain review |
| inventory.BloodUnit | UUID; unique unit_code; protected collection event/donor relation; blood group/component; collection/expiry date; positive approved quantity; AVAILABLE/ISSUED/DISCARDED/QUARANTINED; indexes group/component/status/expiry | Yashwitha |
| inventory.InventoryDisposition | UUID/unit FK/actor/time/reason; controlled transition; terminal discard once; no mutable free-text health payload; source for wastage | Yashwitha |
| inventory.StockAlert | UUID; condition fingerprint+episode; reference/group/component; open/resolved state; durable intent references; no duplicate alert on each poll | Yashwitha |
| blood_requests.BloodRequest | UUID; requester FK; group/component/quantity/urgency; approved status; fulfilled quantity within0..requested; decision actor/time/reason; indexes urgency/status/time | Arnav |
| blood_requests.IssueRecord | UUID; request FK; unit OneToOne/unique; issued_by/time/quantity; request NOT unique; protected transaction history | Arnav; do not move inventory model into request app |
| scheduling.Camp/Slot | UUID; optional camp FK for walk-in; aware start/end; positive capacity; status; camp-total + slot capacity checked under shared lock order | Ankitha |
| scheduling.Appointment | UUID; donor/slot FK; status; active donor+slot unique constraint; no client owner assignment | Ankitha |
| notification_adapter.OutboxIntent | event UUID unique; recipient UUID, controlled event type, record ref, due_at, channels; pending/leased/delivered/failed/cancelled; next_attempt_at/lease expiry; no health body | Arya |
| notification_adapter.DeliveryAttempt | intent+channel+attempt info; outcome/time/redacted error; idempotent receipt identity | Arya |
| Node MockReceipt | event_id+channel unique durable mock receipt; same ID/different payload conflict; approved local persisted JSONL/file or relational adapter, avoid new infrastructure | Arya; persistence choice documented before implementation |
| reporting | read-only DTO/selectors; no second mutable stock or request model | Arya |

Deletion/retention of new operational records is unresolved unless approved: prefer protected history for inventory/request/issue, no cascade erasure by accident. Existing donor CASCADE decision does not automatically approve inventory-history deletion; resolve PROTECT/pseudonymous reference before collection FK migration. Do not store unrestricted copies of donor health answers.

## Migrations
1. Model writer agrees exact schema and cross-app references first. Arnav reviews transaction constraints; Arya coordinates INSTALLED_APPS/root URL includes.
2. Each app owns its migration history; import all models in app models/__init__.py. Use dependency on AUTH_USER_MODEL via swappable_dependency; donor dependencies use exact current migration.
3. Merge latest main; generate only changed-app migrations, inspect SQL/constraints, commit code+migration together. Test clean PostgreSQL16 setup; SQLite smoke is not concurrency evidence.
4. Parallel leaves: merge main and inspect both operations; safe independent operations can use Django merge migration. Conflicting operations need explicit reconciliation migration. Never delete applied migration files or manually patch shared tables.
5. App registration/root URL wiring is centrally coordinated in a small integration PR; owner provides exact line. Do not have four people independently replace settings.py/urls.py.

Collection capture proposal (S2-10): first POST blood-units may omit collection_event_id, in which case the event+first unit are created atomically. The returned ID can be reused for compatible same-donor/date component units. Supplying an ID never bypasses approval/ownership/history validation. No extra inaccessible event-creation prerequisite.
