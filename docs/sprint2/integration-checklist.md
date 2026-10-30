# Arya integration checklist

- [ ] Recorded base and source branch, one owner per story, actual changed scope.
- [ ] Relevant S2 decisions approved (not blank approval placeholders).
- [ ] Request/response fields, roles, errors, statuses and public function imports agree with central contract.
- [ ] Shared changes coordinated; old Sprint1 helpers/tests preserved, no second auth or donor model.
- [ ] Domain models + generated migrations committed together; clean DB/migration consistency checked; no deleted history.
- [ ] Own/other/missing record, invalid input, role/superuser and safe error tests; no secrets or real health data.
- [ ] UI talks to real API; synthetic mocks disclosed; no hardcoded success or invented report zeros.
- [ ] Real PostgreSQL separate connections cover BB16 double issue and BB21 overbooking before those criteria accepted.
- [ ] Outbox created with business transaction; Node failure doesn't erase valid business action; actual mock receipt/retry/idempotency tested.
- [ ] Actual local checks and NOT RUN listed; CI claims linked to real runs, not conflict-free status.
- [ ] Relevant UI smoke, known defects, evidence/docs and post-merge revision recorded.
- [ ] Arya merges; Arya's own work asks teammate review where feasible, AI-assisted review labelled accurately.

Pragmatic college minimum: existing regression suite plus feature-positive/negative/access/boundary checks; one short integrated demo per stream; real DB tests specifically for transaction races. Do not require production infrastructure, real carriers or exhaustive browser matrices. Do not waive adopted performance/availability claims—record pending evidence honestly instead.
