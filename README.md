# BloodConnect — shared Sprint 1 starter (BB-01–BB-12)

**This is a common foundation, not the completed application.** This clean main base contains proposed API contracts, isolated module files, smoke tests and local development setup. The separate private team workpack supplies 12 AI prompts and four member guides; those paths are ignored by Git. No BB-13–24 implementation or prompts are included.

## Start here

For Arya's repository/bootstrap handoff, start with [START_HERE.md](START_HERE.md).

1. Read [decisions](docs/decisions.md). PostgreSQL 16, Django 5.2/DRF, same-origin session+CSRF, Node 24 and manual GitHub Actions are provisional defaults. The SAD mentioned JWT as a proposal; it did not settle authentication. Approve/change these once centrally before member branches diverge.
2. Review [ownership](docs/ownership.md), [API guide](docs/api/endpoints.md), [interfaces](docs/interfaces.md) and [data model](docs/data-model.md).
3. Arya creates one reviewed base commit in the shared repository; all four use that commit and their member guide (private team workpack).
4. Get the base running, then implement a thin login flow collaboratively. Use the [dependency plan](docs/dependencies.md), not numeric story order.
5. From the separate private workpack, read your story prompt in `docs/ai-prompts/BB-XX.md` before giving instructions to your AI. Make small PRs; Arya reviews/merges, and another teammate reviews Arya's own code.

## Docker local setup (recommended shared environment)

Prerequisites: Docker Engine/Desktop with Compose v2; Python 3 available for local secret-file generation. From repository root:

```sh
python scripts/bootstrap_env.py
docker compose up --build
```

Open http://localhost:8000 and http://localhost:8000/login. Check `/api/v1/health/live` and `/api/v1/health/ready`. API paths have **no trailing slash**. The web container applies reviewed migrations on local startup. Database/Node ports are private; only the loopback web port is published. `runserver` is LOCAL ONLY, not production deployment.

In another terminal:
```sh
docker compose run --rm web python backend/manage.py test core.tests accounts.tests
docker compose run --rm web python backend/manage.py makemigrations --check --dry-run
docker compose run --rm web python scripts/validate_repository.py
docker compose run --rm notifications node --test tests/server.test.mjs
```

The web container is Python-only. Frontend Node tests need Node 24 on the host:
```sh
node --test tests/frontend-api.test.mjs
```

To create local synthetic role accounts (not working login functionality):
```sh
docker compose run --rm web python backend/manage.py seed_demo_users
```

`bootstrap_env.py` generates local `.env` secrets without printing them. Never commit/send `.env`. Seeding reads its local demo password, does not print it and grants no clinical permissions. Example emails: donor@example.test, staff@example.test, requester@example.test, admin@example.test. No public staff/requester/admin registration is implemented. Stop containers with `docker compose down`; do not remove the DB volume unless you intentionally want to erase your own local data.

## Native setup (Python 3.13, Node 24, PostgreSQL 16)

```sh
python -m venv .venv
# Linux/macOS:
. .venv/bin/activate
# PowerShell instead: .venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python scripts/bootstrap_env.py
```

Create the local PostgreSQL database/user matching your generated `.env` (or edit the local values to match an existing dev database). This ZIP does not assume a native DB server already exists. Settings load `.env`; OS environment overrides it. Then:
```sh
python backend/manage.py migrate
python backend/manage.py check
python backend/manage.py runserver
```

From the same configured environment:
```sh
sh scripts/check.sh
```

Windows without a POSIX shell: run the individual commands in `scripts/check.sh`, or use Docker. The Node adapter is optional for Sprint-1 business work; Docker passes its service token automatically. For native startup, explicitly export the local token from `.env` into that process's environment and run `node notification-service/src/server.mjs`; Node does not load `.env` automatically.

## Explicit SQLite smoke-only alternative

If PostgreSQL/Docker is unavailable, on Linux/macOS in the activated environment:
```sh
DB_ENGINE=sqlite ALLOW_SQLITE_SMOKE=1 python backend/manage.py migrate
DB_ENGINE=sqlite ALLOW_SQLITE_SMOKE=1 python backend/manage.py test core.tests accounts.tests
```

Generate `.env` first or provide a generated signing key via environment. SQLite cannot establish chosen-engine constraints, real concurrency or release readiness. This is a local smoke escape hatch, not a database decision.

## What works now?

- Startup/settings, foundational UUID email User + initial migration, framework password hashing.
- Django process/database probes and correlation/error handling.
- CSRF token initialization and protected mutation skeletons.
- Plain responsive page shells and shared same-origin JS client.
- Private Node liveness/authentication gate.
- Starter infrastructure tests and contract/prompt consistency checks.

## What does NOT work yet?

Login, logout, registration, RBAC/object policies, donor/profile/result persistence, screening, search, durable audits and full input-safety coverage are **not completed**. Business endpoints return explicit 501 after relevant CSRF/authentication gates; anonymous protected requests return 403. Do not treat stubs or smoke tests as story completion. Node does not deliver/record messages. Availability, performance and usability acceptance evidence is not established.

## Navigation

- [API OpenAPI](docs/api/openapi.yaml) and [endpoint guide](docs/api/endpoints.md)
- [Ownership](docs/ownership.md), [dependencies](docs/dependencies.md), [architecture](docs/architecture.md)
- [Data model/migrations](docs/data-model.md), [public service interfaces](docs/interfaces.md)
- [Git workflow](docs/git-workflow.md), [contributing](CONTRIBUTING.md), [Arya review checklist](docs/integration-checklist.md)
- Member guides: Ankitha (private team workpack), Arnav (private team workpack), Arya (private team workpack), Yashwitha (private team workpack)
- [Adopted first 12 stories](docs/sources/adopted-sprint1-stories.md) and supplied PDF under docs/sources.
- [Validation report](VALIDATION.md): actual results and unrun checks.

No repository was supplied to patch and no GitHub remote, branch, PR, approval or protection was created. CI is a manual draft until the team confirms GitHub Actions. Pin/review runtime container digests and production dependencies/settings separately before any real deployment.

Additional evidence guides: [testing levels](docs/testing.md) and [requirement traceability](docs/traceability.md).
