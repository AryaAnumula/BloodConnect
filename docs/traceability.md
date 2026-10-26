# Sprint 1 traceability — planned business coverage

Source requirement references are preserved. Infrastructure test names below are actual tests; they are **not invented STP test IDs**. Add real STP/RTM mappings during implementation with the testing owner. No row claims its story is complete.

| Story | Source requirements | Implementation prompt | Business acceptance status |
| --- | --- | --- | --- |
| BB-01 | FR-002; SEC-001; SEC-004. | `BB-01.md` (private team workpack) | Unimplemented / approval and integration needed |
| BB-02 | SEC-001; SEC-004. | `BB-02.md` (private team workpack) | Unimplemented / approval and integration needed |
| BB-03 | NFR-002. | `BB-03.md` (private team workpack) | Unimplemented / approval and integration needed |
| BB-04 | SEC-002; SEC-005. | `BB-04.md` (private team workpack) | Unimplemented / approval and integration needed |
| BB-05 | SEC-006. | `BB-05.md` (private team workpack) | Audit candidate implemented; D-10, real authentication/permission integration and acceptance pending; see docs/handoffs/BB-05.md |
| BB-06 | FR-001; SEC-001; SEC-003. | `BB-06.md` (private team workpack) | Unimplemented / approval and integration needed |
| BB-07 | FR-003; SEC-005. | `BB-07.md` (private team workpack) | Unimplemented / approval and integration needed |
| BB-08 | FR-004; SEC-005. | `BB-08.md` (private team workpack) | Unimplemented / approval and integration needed |
| BB-09 | FR-005; SEC-002; SEC-005; NFR-001. | `BB-09.md` (private team workpack) | Unimplemented / approval and integration needed |
| BB-10 | NFR-003; FR-001. | `BB-10.md` (private team workpack) | Unimplemented / approval and integration needed |
| BB-11 | SEC-003. | `BB-11.md` (private team workpack) | Unimplemented / approval and integration needed |
| BB-12 | SEC-005; SEC-002. | `BB-12.md` (private team workpack) | Unimplemented / approval and integration needed |

## Starter infrastructure evidence only

- `core.tests.test_smoke.StarterSmokeTests`: health, database failure redaction, CSRF, explicit stubs, anonymous gate and shell rendering.
- `core.tests.test_contracts.StarterContractTests`: documented route/method wiring and actual infrastructure/error response schemas.
- `accounts.tests.test_foundation.AccountFoundationTests`: Django hashing foundation and no automatic ADMIN clinical permission.
- Native Node tests: liveness, internal-service auth rejection and honest 501 response.
- Frontend client tests: same-origin restriction, CSRF acquisition and surfaced 501 error.

After a feature lands, replace its relevant stub assertion with true acceptance tests and record actual results, environment, tester, build/commit and evidence. Do not count one shared test multiple times as independent story completion.
