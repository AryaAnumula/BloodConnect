# BloodConnect Sprint 2 contract-first foundation

Reviewed main: `a46f81817d7ee26bff7b3ce6e423785a34f951c7` (PR42 merged). This is a **design/documentation foundation**, not implemented Sprint2 functionality. It intentionally adds no runtime routes/models/migrations/dependencies and does not change Sprint1 API/auth. No personal AI prompt files belong on main.

## Main-branch update needed before parallel development
1. Merge this foundation via a small PR, not ZIP-overwriting the clone.
2. Arya and relevant owners approve/change S2-01…S2-10 in config/sprint2-decisions.json and decisions-to-approve.md. These are engineering decision IDs, not new SRS IDs. Shelf-life/threshold numerical values and collection source/retention must be explicitly settled; no clinical defaults in this pack.
3. Regenerate affected proposed API/model/service contracts centrally if a decision changes. Contract validator checks consistency, not approval truth or business correctness.
4. Implement early shared runtime extension points in a separate reviewed PR: app registration/root URL includes; operational (not clinical) role helpers; durable notification intent provider. Do not mount fake-success routes. Each feature app has its own urls.py and per-story files.
5. Everyone merges shared main into clean branches and uses the same approved contract revision. Run feature tests then integrate real providers frequently.

## Documents
- [Exact proposed API](openapi.proposed.yaml) and [endpoint guide](endpoints.md)
- [Internal mocked notification API](notifications.proposed.yaml)
- [Decision gates](decisions-to-approve.md)
- [Public services](services.md), [models/migrations](models-and-migrations.md)
- [Conventions](conventions.md), [ownership](ownership.md), [dependency order](dependencies.md)
- [Integration checklist](integration-checklist.md)

## Avoid the Sprint 1 documentation trap
The current Sprint1 validator intentionally requires exactly12 stories/11 existing API paths and optional docs/ai-prompts only BB01–12. Keep that index/spec untouched. New Sprint2 stories/spec live under docs/sprint2; run the NEW scripts/validate_sprint2_contracts.py separately. Do not dump private prompts into docs/ai-prompts and break the existing validator. Once API implementation merges, update implementation status/evidence in a coordinated PR; don't silently certify draft routes.

Some old docs/interfaces.md and docs/data-model.md still have provider-first/stub wording. For actual Sprint1 behavior inspect main code/current OpenAPI and later decision approval records. This pack does not overwrite those historical documents with guesses. Sprint2-specific files here are the proposed forward contract.

## Checks
python scripts/validate_sprint2_contracts.py
python scripts/validate_repository.py

Set PYTHONUTF8=1 on Windows. Existing tests still run unchanged. CI remains the existing manual workflow unless a separate approval enables PR triggers; no claimed automatic CI. Docker PostgreSQL16 remains project target; SQLite is explicit smoke-only.

## V2 reassignment

Ankitha now owns BB-20/21 and backend/scheduling. Arya owns BB-22/23/24 plus notification adapter/Node and integration. Other owners, points, priorities and exact source criteria unchanged. This supersedes V1 workpack ownership. The reassignment is approved by user request; domain/business-rule proposals are NOT thereby approved.
