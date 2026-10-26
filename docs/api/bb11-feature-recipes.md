# BB-11 feature-owner recipes (reference, not auto-installed donor features)

Read [endpoint contracts](endpoints.md), [decisions](../decisions.md), [ownership](../ownership.md), and [permission usage](../permissions-usage.md) first. Keep existing auth/CSRF decorators and role/object gates; a serializer is not authorization. These are integration **patterns**, not replacement files to paste over another member's implementation. Verify current code before applying. No new URL is required.

## Imports and provider contracts

```python
from core.input_schemas import (LoginInputSerializer, RegistrationInputSerializer,
                                ScreeningInputSerializer, SearchInputSerializer)
from core.parsers import StrictJSONParser
from core.validation import validate_shared_input
```

- Serializers: `Serializer(data=raw_input)` then `.is_valid(raise_exception=True)` → `.validated_data` dict. DRF ValidationError → existing400 envelope. No DB/HTTP/audit/transaction side effects. Their `.initial_data` and `.validated_data` are sensitive: **never log either**.
- `validate_shared_input(*, value, rule_name)` → validated scalar for email/mobile/full_name/location, DRF ValidationError for invalid/unknown rule. No writes, no transaction ownership; serializers are the preferred complete input boundary.
- `StrictJSONParser`: opt in using `parser_classes = [StrictJSONParser]` on the existing JSON view. Duplicate/malformed/nonfinite input raises generic ParseError. Does not change permissions or global settings. Query input uses raw QueryDict, not JSON parser.
- Preserve raw request.data/query_params until serializer receives it. A prefiltered dict hides attacker-supplied privilege/duplicate keys. Never call `serializer.save()` assuming these plain input serializers implement domain writes.

## BB-01 — implemented reference (Ankitha review; Arya provider)

`backend/accounts/api/login.py` now sets StrictJSONParser, validates LoginInputSerializer before `accounts.services.login.authenticate_user(*, email, password)`, then calls real `accounts.services.sessions.establish_session(*, request, user)` and `audit.events.record_security_event(...)`. Existing same-origin CSRF, exact password, sessions, safe user projection and audit remain intact. No copied competing login endpoint/service. `core.tests.test_login_input_integration` and `test_bb11_reference_flow` exercise actual providers.

## BB-06 — registration (Ankitha; Arnav schema review)

Owned: `backend/accounts/api/registration.py`, `backend/accounts/services/registration.py`; donor/profile model ownership and migrations must be coordinated with BB-07/12. First approve D-04 password policy and D-05 fields/normalization/uniqueness.

Inside the existing CSRF-protected public POST view, **before any write**:

```python
# parser_classes = [StrictJSONParser] on the existing view
incoming = RegistrationInputSerializer(data=request.data)
incoming.is_valid(raise_exception=True)
# Existing proposed service signature; feature owner implements it:
profile = register_donor(validated_data=incoming.validated_data)
# Owner translates profile/user to exact RegistrationOutput and HTTP201.
```

`accounts.services.registration.register_donor(*, validated_data: dict)` target returns created profile, owns **atomic User+Profile creation** and DB-backed normalized email/mobile uniqueness, calls Django password hashing/approved policy. It is currently NotImplementedError. Agree duplicate-contact domain exception → safe409; do not catch all DB failures as duplicates. Use savepoints/transaction boundaries correctly; no half-created account if profile insert fails. Public data cannot set role/is_staff/is_superuser/permissions. No new public staff-provisioning API. No migrations deleting history or ad hoc shared DB edits.

Tests: approved valid201 with safe projection; missing/unknown/privilege/type/format/boundary400; duplicated keys400; duplicate normalized contact409; no partial writes on invalid/duplicate/profile-failure; passwords hashed/not returned; direct API bypass; actual PostgreSQL uniqueness/concurrency evidence separately.

## BB-07 — screening (Ankitha; Arnav access review)

Owned: `backend/donors/api/screening.py`, `backend/donors/services/screening.py`, approved clinical configuration and result model/migration coordinated with BB-08/12.

First enforce active auth + CSRF + own-donor/clinical-staff object authorization. Use the **donor profile's user_id**, not donor_id, for an ownership comparison. Current BB-12 helper is unfinished: do not treat it as passing. Do not insert staff-only permission in place of owner-or-staff access.

```python
incoming = ScreeningInputSerializer(data=request.data)
incoming.is_valid(raise_exception=True)
# Only after approved object authorization; keep actor and server-resolved donor ID.
result = screen_donor(actor=request.user, donor_id=donor_id,
                      answers=incoming.validated_data)
# Return exact EligibilityResult, not raw model.__dict__ or submitted answers.
```

`donors.services.screening.screen_donor(*, actor, donor_id: UUID, answers: dict)` target returns persisted EligibilityResult; owns atomic result write and approved rule version. Currently NotImplementedError. `donors.configuration.approved_screening_rules()` is a separate decision gate. D-07 clinical boundaries, first-time/null handling and D-08 freshness must be resolved. Age>=0/decimal shape are not medical acceptance rules. Test invalid input writes no result; approved boundary rules, unauthorized donor, missing record, stale/version behavior and rollback separately.

## BB-09 — search (Yashwitha; Arnav gate, Ankitha data/query review)

Owned: `backend/donors/api/search.py`, `backend/donors/selectors/search.py`, frontend search page. Retain signed-in gates and use `accounts.permissions.IsAuthorizedStaff` for the staff-only list. Approved staff requires active STAFF plus explicit clinical permission and rejects superuser bypass. Other-donor profile routes need BB-12, not this class alone.

```python
query = SearchInputSerializer(data=request.query_params)
query.is_valid(raise_exception=True)
page = search_donors(actor=request.user, **query.validated_data)
# Returns exact DonorPage once owner implements selector and response mapping.
```

`donors.selectors.search.search_donors(*, actor, blood_group=None, location=None, eligibility_status=None, page=1, page_size=20)` target returns pagination dict, read-only/no transaction/network side effects. Currently NotImplementedError. Use parameterized ORM, allowlisted filters, approved freshness and safe summary only. Test repeated/unknown query keys, O%2B encoding, page bounds, empty result, no clinical answers/contact leakage, authorized/unauthorized access, deterministic pages and real DB filters. Component tests do not prove NFR-001 speed; D-12 load protocol is separate.

## BB-08/10 — UI and result consumption (Yashwitha)

BB-08 uses `GET /api/v1/donors/{donor_id}/eligibility/result` and `donors.selectors.results.latest_eligibility_result(*, actor, donor_id: UUID)` (read-only target; not implemented). Coordinate approved freshness/no-result/error and own-or-staff gates with BB-07/12. Render reasons through textContent/escaped templates, never raw HTML.

BB-10 uses proposed RegistrationInput/Output with Ankitha. Client checks must not replace API checks; show generic safe errors, never reflect raw submitted keys. Agree what counts as a primary screen before asserting <=5 screens. UI-only mocks must live in tests, be labelled and never become a fake production success response. Real-browser stored/reflected-value and end-to-end tests remain required.

## BB-12 — privacy (Arnav)

`accounts.permissions.may_view_donor_health(*, user, donor_user_id)` target bool, read-only, no network/DB mutations or implicit audit side effects. Existing function is still unfinished. `donors.selectors.profile.donor_profile_for_actor(*, actor, donor_id: UUID)` target safe projection with object authorization; no competing profile model. Coordinate exact failure exception and minimal field policy before implementation. Decide 403 vs uniform404, and required once-only denial audit (generic404 is not automatically audited). Endpoint-owner guide stays in docs/permissions-usage.md. Test owner vs another donor, authorized clinical staff, missing permission, ADMIN, REQUESTER, inactive, anonymous, superuser and unknown UUID, including safe field projection.

## Shared audit contract and interfaces

`audit.events.record_security_event(*, event_type: str, actor_id: UUID|None, request_id: str, outcome: str) -> None`; allowed pairs login/failure, login/success, access_denied/denied. Actor required on success, UUID correlation only; no arbitrary metadata, password/token/health payload. Writer owns an atomic savepoint, not an independent outer commit; may raise ValueError or AuditUnavailable503. Login currently records direct failures/success; shared DRF handler records raised access denials. Never record the same event in both layers. D-10 access/retention and hidden-denial policy remain unresolved. Validation rejection before credentials is not automatically a failed-login event.

Inside Django call public service/selector imports, not your own HTTP endpoint. Services own state changes/transactions; selectors read and enforce agreed access/projection. Frontend uses HTTP. Django→Node uses private authenticated HTTP, never cross-language imports; notifications remain outside this Sprint-1 provider work.

## Branch, handoff and evidence

After provider merge, merge latest main into your **clean own branch**, inspect any existing implementation, adopt imports rather than duplicate rules. No force pushes. After each story's coherent work: run checks, stage only owned/coordinated files, commit e.g. `feat(BB-06): register donors with validated atomic persistence` **only when complete**, otherwise `wip(BB-06): registration checkpoint; acceptance pending`; push your own branch and open/update the story PR. Do not use a completion commit for test-only mocks. Record actual command/results, engine, dependency revisions, decisions, integration gaps and linked acceptance evidence in the PR and validation matrix. Never commit .env, files/, .venv, DBs, ZIPs or real donor/health data. Shared models/URLs/settings/OpenAPI/client/runner require coordinated changes and review.
