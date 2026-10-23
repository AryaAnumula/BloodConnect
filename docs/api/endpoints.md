# Sprint 1 endpoint guide

**Status:** endpoint designs are proposals pending approval. The executable scaffold only provides liveness/readiness, CSRF initialization and fail-closed business stubs. OpenAPI is the field/schema authority, not proof of implementation.

| Method/path | Owner | Allowed caller (target) | Input → output | Stories | Current status |
| --- | --- | --- | --- | --- | --- |
| `GET /api/v1/health/live` | Arya | PUBLIC | none → Liveness | BB-03 | implemented-infrastructure |
| `GET /api/v1/health/ready` | Arya | PUBLIC | none → Readiness | BB-03 | implemented-infrastructure |
| `GET /api/v1/auth/csrf` | Arnav / Yashwitha | PUBLIC | none → CsrfToken | BB-01, BB-02 | implemented-infrastructure |
| `POST /api/v1/auth/login` | Ankitha; Arnav session integration | PUBLIC | LoginInput → LoginOutput | BB-01, BB-02, BB-05 | stub |
| `POST /api/v1/auth/register` | Ankitha | PUBLIC | RegistrationInput → RegistrationOutput | BB-06, BB-10, BB-11 | stub |
| `POST /api/v1/auth/logout` | Arnav | AUTHENTICATED | none → no body | BB-02 | stub |
| `GET /api/v1/auth/me` | Arnav | AUTHENTICATED | none → AuthUser | BB-04 | stub |
| `GET /api/v1/donors` | Yashwitha; Ankitha API review | STAFF_UNDER_APPROVED_SEARCH_POLICY | none → DonorPage | BB-09, BB-11, BB-12 | stub |
| `GET /api/v1/donors/{donor_id}` | Arnav | OWN_DONOR, AUTHORIZED_STAFF | none → DonorProfile | BB-12 | stub |
| `POST /api/v1/donors/{donor_id}/eligibility` | Ankitha | OWN_DONOR, AUTHORIZED_STAFF | ScreeningInput → EligibilityResult | BB-07, BB-11, BB-12 | stub |
| `GET /api/v1/donors/{donor_id}/eligibility/result` | Yashwitha; Arnav privacy review | OWN_DONOR, AUTHORIZED_STAFF | none → EligibilityResult | BB-08, BB-12 | stub |

## Conventions

- `/api/v1/`, no trailing slashes, JSON bodies and `snake_case` field names. UUIDs identify accounts, donor profiles and results; donor UUID is not the account UUID.
- Proposed email normalization: trim surrounding whitespace and lowercase consistently. Database uniqueness must match it. Proposed mobile format: E.164, no inferred country. D-05 approval required.
- Search: AND selected filters, exact blood group, case-insensitive substring location; proposed stable ordering by donor UUID, bounded page size 1–100. Schema values for stale/not-screened require D-08 approval.
- Never include health answers, credentials or tokens in donor search summaries. Profile/result object access is separate from list visibility.
- Timestamps are offset-aware ISO 8601; store UTC. Local screen/date-boundary interpretation uses Asia/Kolkata provisionally. Future report boundaries remain a separate unresolved policy.
- Success shapes are exact schemas in `openapi.yaml`; validation error: 400, duplicate contact: 409, absent record/result: 404, unfinished feature: 501.
- Session-auth protected calls return **403 `authentication_required`** when unsigned-in and **403 `forbidden`** when signed-in but denied. Invalid login credentials target **401 `invalid_credentials`**. CSRF failure is **403 `csrf_failed`**. This follows the provisional cookie-session design; do not silently promise JWT-style 401 semantics.
- Every error uses `{error: {code, message, fields, request_id}}`. Never echo sensitive field values in messages. X-Request-ID is a correlation UUID, not an account identifier.
- Obtain a CSRF token from `GET /api/v1/auth/csrf`, retain cookies, then send X-CSRFToken on POST, including login/register. Refresh the cached token after successful login because Django rotates it. No browser tokens in localStorage.
- Security/quality stories govern these endpoints; no invented `/security`, `/validation` or `/privacy` API.

## Current behavior versus target behavior

Public business stubs return 501 after CSRF checks. Protected stubs return 403 when anonymous and 501 when authenticated. **Role/object checks and business actions are not implemented.** No data is returned by a stub. Health checks do not establish user authentication, 99% availability, performance or medical safety.

The Node adapter uses `/internal/notifications` on the private service. It accepts only the dedicated service token, then returns 501. There is no frontend-to-Node call, real carrier or recorded delivery. No Sprint-2 endpoints/models/prompts are included.
