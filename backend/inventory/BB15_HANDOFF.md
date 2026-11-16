# BB-15 alert episodes WIP

Stacked on the single BB14 PR65, which depends on BB13 PR56. Only Arya merges. Do not merge child PRs into story parents; Arya controls shared integration and final bases. This diff contains BB15 only.

inventory.0003_alertsweep_inventoryalert follows inventory0002 and the actual notification adapter leaf. evaluate_alerts(*,actor,now) persists episode plus existing enqueue_intent atomically; no HTTP under locks. Actual stock inclusion is shared with BB14. Episodes resolve on recovery and reopen on recurrence; fingerprint changes never mutate an old event payload. GET stock/alerts and staff alert-history page preserve the fixed AlertPage schema.

Correction per frozen demo rule: recipient MUST be active non-superuser STAFF. ADMIN, DONOR, REQUESTER, inactive STAFF and superuser STAFF all fail closed. Explicit controlled recipient account UUID; no public config writer. Versioned minimum2 for32 pairs, near-expiry3days, IN_APP are educational configuration, not clinical defaults. Queue is not delivery.

Publication checks: Django system check, no migration drift, git diff --check, and8 affected alert/recipient/concurrency tests PASS on PostgreSQL18.6. Original65-test evidence remains exact source67d8892f6f38d10dd58c503ac25d3c591e368829, PostgreSQL18.6,65PASS/0skip. It is not relabelled as this publication head. Actual private Node evidence in that suite includes one failed attempt then33 acknowledgements across LOW_STOCK and NEAR_EXPIRY, persisted DeliveryAttempt and fingerprint_version2 receipts. No receipt store or token is committed.

PostgreSQL16 final inventory/concurrency acceptance will be recorded separately. All three stories remain WIP until remaining donor/shared integration, UI/load acceptance and review pass. Donor source files remain untouched; replace labelled development adapters only when Ankitha's actual facade/evaluator/callers arrive, then reconcile and verify history-v2 centrally.
