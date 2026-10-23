# Arya — integration and merge checklist

## Before member branches diverge
- [ ] Review/approve bootstrap stack/auth/database/CI decisions with the team.
- [ ] Confirm one source base commit and remote; preserve all source stories/requirements.
- [ ] All four members can run migrations, health checks and smoke tests.
- [ ] Assign shared-file writers and endpoint/model contracts; record unresolved decisions.

## For each PR
- [ ] Record story ID, author, branch, base-main revision and resulting revision.
- [ ] Check the diff stays within scope and names the actual primary owner.
- [ ] Shared contracts, OpenAPI, enums and interfaces changed only with approval; consumers updated.
- [ ] Another teammate reviews Arya's own implementation; no self-approval.
- [ ] Schema constraints/migrations reviewed by owner; clean chosen-engine DB evidence exists.
- [ ] Tests/CI actually ran on recorded revision; distinguish SQLite smoke, mocks and real integration.
- [ ] Positive, negative, boundary, authentication, object and field-exposure checks are present where relevant.
- [ ] No secrets, real donor records, raw request logging, browser token storage or fabricated success.
- [ ] UI uses exact API fields/statuses and safe text rendering; login/CSRF/logout interfaces agree.
- [ ] Node changes do not claim real delivery or add future-sprint scope.
- [ ] Requirement/RTM references, known defects and incomplete criteria are honest.
- [ ] Latest main merged into branch; conflicts resolved with structural owners; tests rerun.

## Merge and verify
- [ ] Merge only the reviewed scope with ordinary merge commits for the long-lived member-branch workflow.
- [ ] Run migration check, actual migrations where needed, shared tests and post-merge health/UI smoke test.
- [ ] Record result revision, evidence and any regression; do not silently rewrite another person's work.
- [ ] Members merge new main into their branches before dependent work continues.
- [ ] Enable/require PR CI checks only after tool approval and successful workflow setup.

No health probe proves 99% availability; no tiny fixture proves p95 performance; no rendered shell proves registration usability; no mocked service proves integrated acceptance.
