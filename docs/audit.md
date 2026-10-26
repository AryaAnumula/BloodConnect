# BB-05 audit implementation — review candidate, not accepted story

## Source and ownership

Approved requirement: SEC-006; adopted **BB-05: Security-relevant access attempts are recorded safely**. The adopted story/acceptance criteria remain unchanged in `docs/sources/adopted-sprint1-stories.md`.

Primary: Anumula Arya. Supporting reviewer: Ankitha (authentication hooks and safe event fields). Arnav reviews schema, migrations and denial/session integration. D-10 in `docs/decisions.md` is still PROPOSED. This candidate migration and behavior are for local tests/review only; obtain actual named approval before merging/applying to a shared environment. No approval flag has been changed.

## Implemented in this candidate

- A SecurityEvent table and generated initial migration; UUID event ID, server timestamp, allowlisted event type/outcome, optional actor UUID, UUID correlation ID.
- `audit.events.record_security_event` persists metadata; it has no payload/credential/health/email/IP/user-agent argument, extra kwargs fail.
- A shared DRF exception hook records authentication/permission denials without consuming request data. Existing anonymous protected routes now produce a real event. Synthetic permission probes exercise the same hook but do NOT replace BB-04/BB-12 integration tests.
- Conditional tests run against the actual BB-01 login only when present; they skip on main's original login stub. The test runner explicitly reports skips.
- No audit read/list/dashboard/admin endpoint, frontend change, notification, file-log fallback, retention job, or extra dependency.

## Exact interface / proposed D-10 event mapping

```python
from audit.events import record_security_event
record_security_event(event_type='login', actor_id=None,
                      request_id=request.request_id, outcome='failure')
```

Keyword-only signature is unchanged:
`record_security_event(*, event_type: str, actor_id: UUID | None, request_id: str, outcome: str) -> None`.

| Pair | Actor | Caller |
| --- | --- | --- |
| login / failure | null for invalid credentials (do not look up/retain attempted email) | BB-01 PR #30 catches its own LoginRejected and calls writer directly |
| login / success | authenticated account UUID required | BB-01 PR #30 compatibility; additional metadata only, not a new SRS requirement |
| access_denied / denied | authenticated actor UUID if known, otherwise null | shared DRF NotAuthenticated, AuthenticationFailed, PermissionDenied handler |

The shared `core.errors.LoginRejected` also maps to login/failure for future controllers that raise it. PR #30 instead defines and catches `accounts.services.login.LoginRejected`; the handler does not see that caught exception, so there is no duplicate event. Do not add a second login hook.

Request IDs come from the existing middleware, which normalizes valid UUID headers or replaces invalid input with server-generated UUIDs. They correlate events, not authenticate callers or deduplicate requests. Multiple attempts with the same UUID remain separate rows.

`ValueError` means a programmer supplied unsupported metadata/invalid UUIDs. `TypeError` rejects extra arguments. `AuditUnavailable` is a DRF APIException, status 503, code `audit_unavailable`, generic message, no underlying DB exception. Writer returns None only after a successful atomic write. No automatic retries or fake success.

## API behavior and failures — proposed until approved

No new endpoint. Existing documented authentication/protected endpoints gain a proposed 503 Error response for audit-storage failures (`docs/api/openapi.yaml`). Existing 401/403 behavior stays unchanged when recording succeeds. GET/POST methods, input schemas, roles, pagination and feature bodies are unchanged. This does NOT make feature stubs implemented.

Denied access stays denied even if the audit DB is unavailable. The failure response is 503 with the standard error envelope rather than falsely saying the event was persisted. D-10 must approve this failure policy before merge. Health/CSRF bootstrap/registration are not new audited endpoints in this candidate. Successful login compatibility can fail with 503 too; session compensation is an unresolved integration blocker below.

The hook handles raised DRF authentication/permission exceptions only. Controllers that directly return a 401/403 bypass it and must coordinate exactly one writer call. Middleware CSRF failures, 404s, ordinary validation errors, feature-501 responses and successful reads do not create events in this candidate. Approve whether CSRF or other attempt classes belong in D-10 before extending the allowlist. Do not claim coverage for all future routes merely because a shared hook exists.

## Transactions and durability boundary

The writer owns an atomic block/savepoint. It does not own an independent database connection or the surrounding transaction. Calling inside an outer feature transaction and rolling that transaction back also rolls back the audit row; a test demonstrates this limitation. Denial handlers must run outside the rolled-back feature transaction. Current settings do not enable ATOMIC_REQUESTS. Do not enable it or put audit calls inside discarded transactions without an approved strategy.

Django TestCase itself wraps tests; these are test mechanics, not a separate production commit strategy. Persistence/migration tests use actual ORM writes, not a mocked writer.

### Important BB-01/BB-02 integration blocker

PR #30 currently calls establish_session BEFORE its login/success audit write. When the real BB-02 provider lands, an audit failure after session creation could return 503 while leaving an authenticated session. This ZIP does NOT edit Ankitha's or Arnav's files to guess session compensation.

Before complete-login acceptance, Ankitha + Arnav must agree and implement the failure semantics: if success-audit fails, ensure the newly established session is invalidated/not usable (including any session saved by the helper). Add an integration test with real session creation and injected audit DB failure; assert no usable authenticated cookie/session survives. Also prove session creation failures cannot leave a falsely recorded successful login. Do not solve this with a second auth system or by swallowing errors. The proposed ordering/compensation requires joint review. No successful browser-login claim is made here.

## Access / retention / operational limits

No HTTP or Django admin audit reader exists. ADMIN application role grants no audit access. Direct ORM/database access still exists for trusted operators: the code does not prove operational DB permissions or an approved security-reviewer access policy. Team must approve who may read, retention duration, deletion/export handling, permitted event classes and write-failure behavior. Do not invent a retention duration, grant all staff audit access or claim append-only/tamper-proof storage. This is not cryptographically immutable storage; privileged DB users can edit it. No deletion/retention automation is provided.

Actor IDs are nullable UUID snapshots, not cascading foreign keys; deleting an account does not erase an audit row. This is a schema proposal, not permission to retain personal identifiers indefinitely. Approve deletion/retention policy. No emails, passwords, tokens, health answers, URLs/query strings or raw exception details are stored. Timestamps are timezone-aware; Django stores UTC with USE_TZ; display timezone conversion belongs to a separately approved reader.

## Migration / rollout

Owner Arya; Arnav reviews `backend/audit/migrations/0001_initial.py`. It has no User FK dependency. Run on a clean local DB, inspect plan, then test the agreed PostgreSQL 16 engine before shared merge. Do not delete an existing audit migration or shared table to make this apply. If any audit migration has landed since the base SHA, STOP and coordinate a new migration/merge. Do not use `--fake`.

Existing deployments must apply migrations before serving audited endpoints; otherwise requests may return redacted 503. Run against synthetic/local databases only until policy/schema approval.

## Coverage and still pending

Implemented/tested candidate: strict writer, model constraints, actual baseline anonymous denial, redacted storage failures, actor/correlation metadata, no sensitive columns/arguments, no public audit reader. PR #30 failed-credential integration can be exercised separately without writer/authenticate mocks. Success-session integration, all real BB-04/12 role/object denials, chosen-engine deployment, independent review and D-10 approvals remain pending. BB-05 is NOT Done.

See `docs/handoffs/BB-05.md` and `docs/audit-sanitized-examples.json` (illustrative synthetic values, not runtime evidence).
