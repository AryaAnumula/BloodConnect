# Story and file ownership

Assignments are proposed from the latest request and planning table. No person was reassigned by this starter. All BB-01–12 are in the current Sprint-1 planning draft; availability observation and security coverage continue as needed. Counts are not capacity.

| Story | Primary | Support/reviewer | Provisional points | Primary owned files |
| --- | --- | --- | --- | --- |
| BB-01 | Ankitha Lakshmmi Mohan | Yashwitha — login UI; Arya — authentication test review | 5 | `backend/accounts/api/login.py`; `backend/accounts/services/login.py`; `frontend/templates/login.html` |
| BB-02 | Arnav Chaudhary | Ankitha — authentication design and integration review | 3 | `backend/accounts/services/sessions.py`; `backend/accounts/api/logout.py`; `backend/accounts/tests/test_sessions.py` |
| BB-03 | Anumula Arya | Arnav — database/runtime health checks | 5 | `backend/core/health.py`; `backend/core/tests/test_health_monitoring.py`; `docs/availability.md` |
| BB-04 | Arnav Chaudhary | Ankitha — permission/API review; Arya — negative tests | 5 | `backend/accounts/permissions.py`; `backend/accounts/api/me.py`; `backend/accounts/tests/test_permissions.py` |
| BB-05 | Anumula Arya | Ankitha — authentication hooks and safe event fields | 3 | `backend/audit/events.py`; `backend/audit/models/event.py`; `backend/audit/tests/test_events.py` |
| BB-06 | Ankitha Lakshmmi Mohan | Yashwitha — registration UI; Arnav — constraints | 5 | `backend/accounts/api/registration.py`; `backend/accounts/services/registration.py`; `backend/donors/models/profile.py` |
| BB-07 | Ankitha Lakshmmi Mohan | Arya — boundary tests; Yashwitha — screening UI | 8 | `backend/donors/api/screening.py`; `backend/donors/services/screening.py`; `backend/donors/models/eligibility.py` |
| BB-08 | Ch Yashwitha | Ankitha — result/reason contract and policy review | 3 | `backend/donors/api/result.py`; `backend/donors/selectors/results.py`; `backend/donors/tests/test_results.py` |
| BB-09 | Ch Yashwitha | Ankitha — donor search/API design; Arya — performance tests | 5 | `backend/donors/api/search.py`; `backend/donors/selectors/search.py`; `backend/donors/tests/test_search.py` |
| BB-10 | Ch Yashwitha | Ankitha — registration integration; Arya — walkthrough | 3 | `frontend/templates/register.html`; `frontend/static/js/pages/registration.js`; `frontend/static/css/app.css` |
| BB-11 | Anumula Arya | Ankitha and Arnav — server-side validation fixes/review | 3 | `backend/core/validation.py`; `backend/core/tests/test_validation.py`; `docs/input-validation-matrix.md` |
| BB-12 | Arnav Chaudhary | Ankitha — donor privacy/API review; Arya — access tests | 5 | `backend/accounts/permissions.py`; `backend/donors/api/profile.py`; `backend/donors/selectors/profile.py` |

## Controlled shared files and overlap protocol

| Area | Structural owner | Required coordination |
| --- | --- | --- |
| User model / initial migration / later account migrations | Arnav | Ankitha reviews authentication/registration impact |
| DonorProfile schema / registration transaction | Ankitha | Arnav reviews uniqueness/atomicity/migrations |
| Eligibility schema and rules | Ankitha | Yashwitha reviews result/search consumers; Arnav checks privacy |
| Shared permissions.py | Arnav | BB-04 and BB-12 are same owner; endpoint owners wire approved gates |
| Registration page | Ankitha for functional form | Yashwitha BB-10 agrees UI changes before editing same files; serialize overlapping edits |
| Login UI and API | Ankitha | Yashwitha supports UI; Arnav supplies sessions.py |
| Search API/query + UI | Yashwitha | Ankitha reviews donor query/contract; Arnav privacy; Arya load tests |
| Audit model/interface | Arya | Login/permission owners add hooks; Arnav migration review |
| Shared input-validation primitives | Arya | Endpoint serializers remain owner files; submit fixes through owner review |
| OpenAPI, root URLs/settings, dependencies, Docker/CI | Arya integration control | Relevant module owner approval; no unilateral changes |
| Base template, CSS, shared API client | Yashwitha | Arnav reviews cookie/CSRF behavior; page owners coordinate |

One structural writer per shared file at a time. Announce intended shared edits in the issue, get approval, merge that small prerequisite first, then refresh dependent branches. Do not solve overlap by creating a second User/Profile model, auth framework or endpoint registry.

## Risk notes

Arya owns CI/integration plus security/availability work; do not make Arya repair all feature code. Ankitha owns screening (8 provisional points) plus login/registration and shared reviews. Story count is not effort. Obtain capacity agreement before commitment; no automatic redistribution was made.
