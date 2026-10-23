# Sprint 1 architecture and file map

Browser (same origin) → Django/DRF controller → serializer/permission → service or selector → Django ORM/PostgreSQL. Node is an isolated notification adapter skeleton reached via authenticated internal HTTP; delivery is deferred.

- `backend/config/`: settings/routes. Arya controls changes with module-owner review.
- `backend/accounts/api/`: one endpoint per file. Login/registration Ankitha; logout/me Arnav; CSRF shared infrastructure.
- `backend/accounts/services/`: login/registration Ankitha, session helper Arnav. `models/user.py` Arnav, with Ankitha review.
- `backend/donors/api/`: screening Ankitha, search/result Yashwitha, private profile Arnav.
- `backend/donors/services/screening.py` and `configuration.py`: Ankitha.
- `backend/donors/selectors/`: search/results Yashwitha; private profile Arnav.
- `backend/donors/models/`: model files are reserved; the package must import implemented models. Profile schema requires Ankitha + Arnav approval. Eligibility schema Ankitha; consumers review.
- `backend/core/`: request ID, error envelope, health and explicit stubs. Arya controls shared contract changes; per-feature serializers live beside that feature's API file, not in one giant serializer.
- `backend/audit/`: Arya. Call sites are added by their own endpoint owner after event interface approval.
- `frontend/templates/` and `frontend/static/js/pages/`: plain, same-origin page shells, no embedded health records. Yashwitha reviews shared layout/client; assigned story owner coordinates their page integration.
- `notification-service/`: native Node skeleton, private HTTP. No carrier, queue or delivery implementation.
- `docs/ai-prompts/`: exactly 12 member-ready prompts. `docs/team/`: four member guides.

## Which files are safe to change?

Independent: the story-specific endpoint/service/test/page files in ownership.md. Controlled: settings, top-level URLs, OpenAPI schemas, User/Profile structural schema, shared HTTP client, lock file, Docker/CI. Generated: migrations (generate deliberately; review/commit, do not casually rewrite), dependency lock, validation report. Local/excluded: .env, local databases, .venv, logs, local artifacts and unapproved local decisions.

No inventory, issue, camp, booking, reporting or notification-delivery business implementation exists in this Sprint-1 base. The source PDF includes later scope only for reference.

## Status of executable code

Implemented infrastructure: startup, provisional custom User foundation and initial migration, Django-provided password hashing, process/database checks, CSRF initialization/protection, safe correlation metadata/error envelope, UI shells, Node health/authentication gate, smoke-test scaffolding.

Unfinished: credential-login endpoint, registration, complete session/logout behavior, role/object policies, donor/profile/result persistence, clinical rules, search, input-validation coverage, durable audit storage, load/availability/usability acceptance. The infrastructure does not complete any entire BB story.
