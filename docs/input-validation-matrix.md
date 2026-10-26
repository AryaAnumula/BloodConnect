# BB-11 — SEC-003 adoption and acceptance matrix

Exact source story/criteria remain in docs/sources/adopted-sprint1-stories.md. Team plans BB-11 in Sprint 1; original proposed planning text is not rewritten. Arya owns providers; Ankitha/Arnav support server-side review, Yashwitha owns UI/search adoption. No full story acceptance is inferred from component checks.

| Input / endpoint | Shared provider | Runtime and evidence | Feature owner / remaining gate |
| --- | --- | --- | --- |
| POST /api/v1/auth/login | LoginInputSerializer, StrictJSONParser | **Wired** in this refresh; actual endpoint/provider tests in core.tests.test_login_input_integration, core.tests.test_bb11_reference_flow; baseline account/audit suites retained | Ankitha reviews owner-controlled login change; normal sign-in unchanged |
| POST /api/v1/auth/register | RegistrationInputSerializer, StrictJSONParser target | Unwired501; component shapes tested only | Ankitha BB-06, D-04 password/D-05, DB constraints and atomicity |
| POST /api/v1/donors/{donor_id}/eligibility | ScreeningInputSerializer, StrictJSONParser target | Unwired501; no medical results/writes | Ankitha BB-07, D-07/08 and BB-12 |
| GET /api/v1/donors | SearchInputSerializer on raw QueryDict | Unwired501; repeated/unknown/encoded-plus/page-bound component checks only | Yashwitha BB-09, staff gate, data/filter/freshness and D-12 |
| JSON parser | StrictJSONParser | core.tests.test_validation.StrictParserTests: duplicate/nested/malformed/UTF8/nonfinite including +/-1e999; finite decimals/exponents; generic errors | Opt in per feature; no global parser or body/depth policy change |
| Validation before write | StrictInputSerializer, strict fields | core.tests.test_validation_api uses test-only URLconf/force-auth and synthetic User.first_name write; ORM literal preservation | Not production registration; owners must prove no invalid/partial domain writes |
| DOM/API helper | Existing showStatus textContent; empty204 fix in apiFetch | tests/frontend-input-safety.test.mjs controlled DOM sink; tests/frontend-api.test.mjs mocked fetch including logout204 | Yashwitha review; not browser/server end-to-end evidence |
| Result/profile projections | Output schemas and permission interfaces | Still stubs; no all-model-fields dumping supplied | BB-08/12 owner tests and approved field visibility |

## Provider guarantees and exclusions

Object-only serializers reject unknown/read-only keys, strict types and repeated query values without echoing attacker-controlled keys/values. Passwords remain exact, write-only, never logged. Normalization preserves existing login trim/lowercase; registration/mobile proposals still require approval. Use parameterized ORM and safe contextual rendering, not blanket HTML/SQL stripping. These providers do not authorize, enforce DB uniqueness, start transactions, decide medical eligibility or sanitize arbitrary URL/HTML/CSS sinks. No invented max password or clinical thresholds.

Service imports/errors/transactions and per-story test obligations: [feature recipes](api/bb11-feature-recipes.md). No secret/health fixtures. Audit denial metadata is intentional security evidence, not an invalid domain write; don't suppress audit to force a zero-write test.

## Adopted acceptance — bounded status

| Criterion summary (source wording remains authoritative) | Demonstrated here | Still needed |
| --- | --- | --- |
| Agreed server types/lengths/formats/values | Shared provider and real login | Approved remaining field/policy choices and real feature adoption |
| Malformed input rejected before invalid state changes | Real login no auth/account change; synthetic write-order probe | Registration/screening transaction/error tests |
| Injection/script-like data cannot execute SQL/browser code | Literal ORM probe; safe DOM sink unit | Actual feature queries and real-browser reflected/stored-value flows |
| Direct API bypass remains safe | Actual login raw requests; test-only write probe | Other real feature APIs including auth/object checks |
| Errors exclude internals/secrets/health | Parser/validator/login/audit-failure tests | Feature DB/domain errors/projections |
| Feature evidence linked, not duplicated | Exact shared modules listed | Feature owners add their actual modules/PRs, engine and results below |

## Feature-owner evidence register (not pre-filled successes)

| Story | Actual feature test modules / PR / revision | Engine and results | Decision approval references | Status |
| --- | --- | --- | --- | --- |
| BB-06 | Owner to supply | NOT RUN here | D-04 password/D-05 pending | pending |
| BB-07 | Owner to supply | NOT RUN here | D-07/08 + object access pending | pending |
| BB-08 | Owner to supply | NOT RUN here | D-08/visibility pending | pending |
| BB-09 | Owner to supply | NOT RUN here | D-08/12 as applicable | pending |
| BB-10 | Owner to supply | Real browser NOT RUN here | D-05/screen definition | pending |
| BB-12 | Owner to supply | NOT RUN here | Field/denial policy | pending |

D-03, D-04 session part and D-09 role gate are recorded in decisions.md; this does not approve password policy, clinical rules or all object projections. PostgreSQL/Docker/remote CI/real browser remain separate unexecuted checks in this local build. See [handoff](handoffs/BB-11.md).
