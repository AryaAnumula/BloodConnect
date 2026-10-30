# Sprint 1 API guide — runtime versus feature contracts

Base: current main b23d518 plus independent BB05/BB11 follow-up. BB08/09 endpoints remain stubs. Field/schema authority: [OpenAPI](openapi.yaml). Stories/requirements stay as adopted. **Route existence does not prove feature completion.**

| Method / path | Primary owner | Allowed caller / gate | Request → response | Runtime status |
| --- | --- | --- | --- | --- |
| GET /api/v1/health/live | Arya / BB-03 | public | none → Liveness 200 | implemented infrastructure |
| GET /api/v1/health/ready | Arya / BB-03 | public | none → Readiness 200/503 | implemented infrastructure |
| GET /api/v1/auth/csrf | Arnav; frontend Yashwitha | public, retain cookies | none → CsrfToken 200 | implemented |
| POST /api/v1/auth/login | Ankitha / BB-01; Arnav BB-02; Arya BB-05/11 | public + CSRF | LoginInput → LoginOutput 200 | implemented reference with strict validation |
| POST /api/v1/auth/logout | Arnav / BB-02 | active authenticated + CSRF | no body → 204 **empty body** | implemented |
| GET /api/v1/auth/me | Arnav / BB-04 | active authenticated | none → AuthUser 200 | implemented, metadata only |
| POST /api/v1/auth/register | Ankitha / BB-06, UI Yashwitha BB-10 | public + CSRF; never public elevated-role provisioning | RegistrationInput → RegistrationOutput | implemented201;strict input400;generic duplicate_contact409 |
| GET /api/v1/donors | Yashwitha / BB-09; Arnav access review | target: IsAuthorizedStaff | query → DonorPage | implemented STAFF+permission gate;strict AND filters;safe summaries and stable pagination |
| GET /api/v1/donors/{donor_id} | Arnav / BB-12 | own active donor OR authorized clinical staff; all superusers denied | profile UUID → safe DonorProfile | implemented: 200 allowed; 403 role/auth denial; identical404 missing/other-donor; audit failure503 |
| POST /api/v1/donors/{donor_id}/eligibility | Ankitha / BB-07; Arnav privacy review | target: own donor OR authorized clinical staff + CSRF | UUID + ScreeningInput → EligibilityResult | implemented demo assessment/history;400 invalid;403 role;hidden404;409 policy |
| GET /api/v1/donors/{donor_id}/eligibility/result | Yashwitha / BB-08; Arnav privacy review | target: own donor OR authorized clinical staff | UUID → EligibilityResult | implemented latest saved result;own/staff;hidden404;policy409 |

Full owner/story/FR/SEC mappings, types, required fields, outputs, response codes and parameters are in each OpenAPI operation. No separate endpoint is invented for SEC-003. Frontend calls Django, never Python imports or the internal Node service.

## Exact ingress contracts

All POST feature bodies are JSON **objects**, not lists/null; field names use snake_case, no undeclared privilege fields. Login uses StrictJSONParser now; feature owners opt in when implementing other JSON views. Duplicate keys, invalid syntax/UTF-8, NaN/Infinity and overflow such as 1e999 produce redacted 400 `invalid_json` on the wired login. Do not manually prefilter raw input before strict validation.

| Schema / ingress | Required fields / validation | Gate / effects |
| --- | --- | --- |
| LoginInput | email: string, valid email, max254, trim/lowercase; password: nonempty string, exact whitespace retained | implemented before credential evaluation; no guessed max password length |
| RegistrationInput | email max254; mobile E.164 `+` then 8–15 digits, nonzero first digit; password string min12 (recorded approval); full_name and location trimmed nonblank max120; blood_group enum | D04/D05 approvals recorded;real registration service enforces atomic account/profile and uniqueness |
| ScreeningInput | age_years JSON integer >=0 (not eligible age); weight_kg nonnegative decimal **string**, at most 2 decimal places; last_donation_date required ISO YYYY-MM-DD or null | D07/D08 educational rules/freshness recorded;real screening service owns rule evaluation |
| SearchInput | optional blood_group, location max120 (empty allowed), eligibility_status; page integer digits >=1 default1; page_size1..100 default20; duplicate or unknown query keys rejected | D-08 states/freshness and staff gate required; no medical answers in summary |

blood_group: `A+ A- B+ B- AB+ AB- O+ O-`. Proposed search eligibility_status: `ELIGIBLE INELIGIBLE NOT_SCREENED STALE`. Result status: `ELIGIBLE INELIGIBLE`, with is_stale separately. Encode a plus sign in queries (`O%2B`); use URLSearchParams rather than manual concatenation. Do not derive medical eligibility from a valid payload.

## Output projections (exact property types in OpenAPI)

- LoginOutput: `{user: {id, email, role}, session_expires_at}`. No password, health data or bearer token.
- AuthUser: `{id, email, role}` only.
- RegistrationOutput: `{donor_id, user: {id, email, role}}` (real201 response).
- DonorProfile: `{id, user_id, full_name, email, mobile, blood_group, location}` explicit profile projection; no screening answers, passwords or tokens. Other feature projections remain separately controlled.
- DonorPage: `{count, page, page_size, results: [{id, blood_group, location, eligibility_status}]}`. Empty real results use `count: 0, results: []`, not 404 or a fabricated success while stubbed.
- EligibilityResult: `{id, donor_id, status, reason_codes, reasons, assessed_at, rules_version, is_stale}`. No raw screening answers in general summaries.

Identifiers are UUID strings; **donor_id is not user_id**. Timestamps are aware ISO 8601, stored UTC; date-only values stay YYYY-MM-DD, not silently converted to timestamps. Proposed local date interpretation Asia/Kolkata needs boundary/policy review. Proposed search: AND filters, exact group, case-insensitive location substring, stable donor-UUID ordering, bounded pagination. Implementation/performance evidence pending.

## Errors and security

Error body: `{ "error": { "code": "validation_error", "message": "Request validation failed.", "fields": {"email": ["Enter a valid email address."]}, "request_id": "<correlation UUID>" } }`.
Never echo raw input, DB exceptions, passwords, sessions or health data. Correlation ID is not identity. Validation error fields are controlled rule messages, not arbitrary input names.

- Login: 200 valid; 400 validation_error/invalid_json; 401 invalid_credentials (same generic message for unknown, wrong or inactive); 403 csrf_failed; 415 unsupported media type; 503 audit_unavailable.
- Signed-in routes: missing/invalid/expired cookie session normally 403 authentication_required/invalid_authentication, not JWT-style 401. Signed-in role denial 403 forbidden. Denial-audit storage failure may return redacted 503. CSRF failure 403 csrf_failed.
- Proposed business responses: 400 invalid input, 409 duplicate contact, 404 missing record/result, 200/201 per OpenAPI. Hidden-object denial 403 versus 404 remains a policy decision: do not guess or globally audit every 404.
- Unfinished public business stub returns 501 after CSRF; protected stubs return anonymous403/authenticated501. They do not create data. Shape validators do not authorize requests, guarantee transactions, SQL safety in unrelated raw queries or sanitize HTML/URL/CSS contexts.

## Real frontend reference

```javascript
import { apiFetch, resetCsrfToken, showStatus } from '/static/js/api/client.js';
// In a served same-origin module; do not log credentials.
await apiFetch('/api/v1/auth/login', { method: 'POST', body: { email, password } });
resetCsrfToken(); // login rotates CSRF: next POST must initialize a fresh token
const me = await apiFetch('/api/v1/auth/me');
showStatus(`Signed in as ${me.email}`); // actual helper uses textContent
await apiFetch('/api/v1/auth/logout', { method: 'POST' }); // returns null for 204
resetCsrfToken();
```

`apiFetch` accepts only agreed same-origin API paths, sends cookies, initializes CSRF, serializes JSON, throws controlled error.message/code/status and handles 204 without JSON parsing. Caller owns UI state and clearing cached CSRF after session changes. No tokens/localStorage, no real donor fixtures. Browser controls/client validation are convenience, not server security.

The mocked Node `/internal/notifications` remains private token-authenticated and 501; no frontend calls or delivery claims. Sprint 2 is excluded.


BB08/09/10 master follow-up:actual result/search interfaces and registration UI status are documented in [master guide](../yashwitha-master.md). Earlier provider-first descriptions above must not be read as instructions to recreate merged APIs. BB10 now supplies safe field-error and submit-state handling against real registration.
