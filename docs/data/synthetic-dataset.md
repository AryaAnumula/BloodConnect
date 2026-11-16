# Common synthetic dataset: BC-D038

Latest16November2026 user instruction explicitly authorizes a complete AI-generated mini-project dataset and GitHub publication. Real-person data is unnecessary. [Dataset and usage](../../datasets/synthetic/bloodconnect-demo-v1/README.md), [canonical JSON](../../datasets/synthetic/bloodconnect-demo-v1/dataset.json), [field/type dictionary](../../datasets/synthetic/bloodconnect-demo-v1/data_dictionary.json), [known answers](../../datasets/synthetic/bloodconnect-demo-v1/expected.json).

The source contains500 donors/500 units and linked screening, collection, request, issue, discard, scheduling and mock notification history. UUIDs and dates are reproducible; the default reference date is16November2026. Sources/provenance, explicit existing educational numerical settings, generation/check commands, standalone reference SQL and safe local foundation import are documented with the dataset.

## Required fields and ownership

| Area | Factors used by features | Owner |
| --- | --- | --- |
|Accounts/donors|UUID account/profile identity, role/activity, name/mobile/group/location; no published credentials|Ankitha; account structure shared|
|Eligibility/history|Age/weight, self-reported last date, confirmed event snapshot, result/reasons, assessed_at/rules version; historical assessments kept|Ankitha + Yashwitha collection caller|
|Collection/stock|Confirmed event ID/donor/date, component unit ID/code, quantity, expiry/status, explicit discard actor/time/reason|Yashwitha|
|Requests/issues|Requester/group/component/quantity/urgency/status, review actor/time/reason, fulfilled quantity, unique unit allocations and issue time|Arnav16–18; Arya19|
|Scheduling|Camp/slot times/location/capacity/status, donor appointment, booked/cancelled timestamps|Ankitha20/21|
|Notifications|Account recipient, appointment/event IDs, due/slot times, channels, late/timing flags, attempt/receipt state; fixture evidence clearly labelled|Arya22|
|Dashboard/reports|Usable units, submitted count, upcoming ACTIVE starts>=now; distinct collection events, unit counts, actual issue quantities and explicit discards in local-date→UTC bounds|Arya23/24 using domain selectors|

All required data entities now exist in the shared dataset. The application still needs each owner's actual persistence/selector implementation to expose them through feature APIs. Use this single source and expected.json to reconcile those implementations; do not copy invented totals into selectors or point production code at the standalone reference database. This does not combine or merge BB22/23/24 PRs.

## Import boundary

The existing testing schema can immediately import515 ordinary accounts,500 profiles,100 uncollected-donor assessments and80 non-issued requests with seed_project_demo. Remaining full history is available as neutral JSON/CSV with target model ownership in the dictionary. Deferred rows do not become fabricated successful imports. No schema/migration, public route, permissions, clinical/default config or automatic CI is changed by the dataset work.

[Verification evidence](synthetic-dataset-verification.md): actual PostgreSQL16 regression399 Django/76 Node/29 availability plus14 dataset tests passed, with independent SQL/CSV/checksum reconciliation. Generated mock history is not observed network-delivery evidence. Only Arya merges; authorship remains his existing Git identity.
