# Parallel work without guessed interfaces

There are real data dependencies. Contracts remove guessing, not the need to integrate. No guaranteed dependency-free development or one-shot completion is claimed.

| Stream | Start independently after decisions/contracts approved | Wait for / mock boundary (test-only) | Finish integration |
| --- | --- | --- | --- |
| Yashwitha BB13→14→15 | Unit serializer/UI, expiry functions with synthetic configured rules, schema draft, stock selectors/test fixtures | Collection eligibility/provider reused from existing main; notification enqueue mocked until Arya provider merges | Real inventory rows + outbox + Node receipt, stock/issue reconciliation |
| Arnav BB17→18; then16→19 | Request schema/API/UI, role checks, transitions, issue orchestration with exact allocation DTO mock | BB16 real issue waits inventory.allocate_units; no local competing BloodUnit model | Real PostgreSQL separate-connection issue race; lifecycle requester UI |
| Ankitha BB20→21 | Camp/slot definitions, booking rules and scheduling summary/reminder selectors | Arya notification enqueue mocked only at test boundary until provider merged | Real booking + durable intent; PostgreSQL capacity race |
| Arya BB22→23→24 | **Publish notification enqueue provider early**; dispatcher/mock receipt; dashboard/report layouts | Ankitha scheduling/reminder selectors; other owners’ stock/request selectors; no guessed report totals | Real records + mock receipt persistence/retry and reconciled summaries |
| Optional supporting tasks | Ankitha retains donor/role review expertise alongside her two primary stories | Agree time/capacity; never make three support tasks extra mandatory stories | Reviews/regressions recorded without double-counting story credit |

First branch cut only after foundation documentation merged and relevant decisions approved. First shared runtime PR: app registration/URLs and minimal approved operational-role helper + durable notification intent provider can be merged early, with meaningful tests and honest unfinished dispatcher. No feature may claim notification delivery until Node mock really records receipt.

Collection event/source and FK retention are intentional blocking decisions: don't fabricate health/donation history. Missing approved shelf-life/threshold config → policy_unresolved409; don't guess clinical defaults. Actual provider not merged: finish boundary-independent work or wait, label mock limitations.
