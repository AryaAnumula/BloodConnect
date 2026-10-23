# Validation levels and evidence

1. Static repository check: `python scripts/validate_repository.py` checks the 12-story index, source criteria/owner links when private workpack files exist, two OpenAPI documents, relative links, Python syntax, baseline checksum and manual workflow wiring. It does not establish feature correctness.
2. Django check/migrations: `python backend/manage.py check`, `makemigrations --check --dry-run`, `migrate` on a clean chosen-engine DB.
3. Starter tests: `python backend/manage.py test core.tests accounts.tests` verifies infrastructure and stubs. It must evolve as features are implemented.
4. Native Node tests: `node --test notification-service/tests/*.test.mjs tests/frontend-api.test.mjs` verifies the internal skeleton and JS client only.
5. Future business acceptance: positive/negative/boundary/object-access/UI/API tests tied to actual story criteria, chosen-engine integration and approved availability/performance/usability protocols. Do not fabricate or infer success from a mock.

SQLite smoke tests cannot substitute for PostgreSQL constraint/concurrency validation. Manual GitHub Actions YAML is not proof a remote CI job passed. Docker YAML parsing is not proof images build/start. `VALIDATION.md` records what actually ran for this delivery.

Keep actual logs under ignored `artifacts/local/` on your own machine and link appropriate sanitized evidence in PRs. Never attach credentials or donor health payloads.
