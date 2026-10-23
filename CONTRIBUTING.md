# Contributing

Read `docs/decisions.md`, `docs/ownership.md`, `docs/api/endpoints.md` and your member guide first.

1. Use the same approved base commit and development stack.
2. Follow `docs/git-workflow.md`: merge current main into your member branch; no force push.
3. Read the assigned `docs/ai-prompts/BB-XX.md` before coding. AI must inspect repository code, not invent another architecture.
4. Agree shared contract/schema changes with the listed owner BEFORE implementation.
5. Python variables/functions: snake_case; classes: PascalCase; JSON: snake_case; JavaScript: camelCase. Internal variable names may differ; public fields/signatures must match contracts.
6. Keep controllers thin, services for writes/business rules, selectors for authorized reads. Use ORM parameters and textContent/contextual escaping; do not concatenate database queries or insert untrusted HTML.
7. Never log password/token/health payloads; use synthetic fixtures; keep .env excluded.
8. Add meaningful positive/negative/boundary/access tests and update source traceability.
9. Run the check commands in README, link actual evidence and disclose unrun tests. A passing stub test is not completed business acceptance.
10. Open a small PR with the template. Authors do not approve their own code. Arya merges after review and runs post-merge smoke tests.

Do not delete migration history, reset shared databases, rename API fields, introduce new auth schemes or dependencies, or edit another owner's shared file without coordination.
