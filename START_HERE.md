# Start here — Arya and the four-person team

## 1. What you received

A shared **Sprint-1 starter for BB-01–BB-12 only**. The clean main ZIP excludes AI prompts and member AI guides. Use the separate private workpack for those. The API contracts and module/service boundaries are proposed; business features are unfinished and must not be presented as completed stories. No BB-13–24 feature implementation or prompts are included.

## 2. Before coding

Read `docs/decisions.md` together. Confirm database, versions, session-versus-JWT choice, frontend origin and CI choice. The starter uses provisional PostgreSQL 16, Python 3.13/Django 5.2/DRF, Django cookie sessions + CSRF, Node 24 and manual GitHub Actions. Approve or change the shared base ONCE before everyone branches. Clinical/access/monitoring decisions have separate gates.

Review `docs/ownership.md`, `docs/api/endpoints.md`, `docs/api/openapi.yaml`, `docs/data-model.md` and `docs/interfaces.md`.

## 3. Establish the repository

If this is an empty new repository, Arya can initialize it after reviewing the starter:

```sh
git init -b main
git status
# Review for local secrets and unneeded files before staging.
git add .
git commit -m "Create reviewed BloodConnect Sprint 1 foundation"
git remote add origin <actual-shared-repository-url>
git push -u origin main
```

If a repository already exists, do not overwrite it or run those commands blindly. Compare/import this starter in a reviewable branch. No GitHub operations have been performed by delivering this ZIP.

Everyone clones the same reviewed base commit, then follows `docs/git-workflow.md` for their member branch. Use merge-based synchronization and no force pushes. Do not wait until the end to review four large incompatible branches.

## 4. Run the base

Follow README Docker setup (`python scripts/bootstrap_env.py`, then `docker compose up --build`). Each member must run the common tests before starting feature work. Do not share `.env`; everyone generates their own local values.

## 5. Give each member the correct AI prompt

| Member | Primary stories | Guide |
| --- | --- | --- |
| Ankitha | BB-01, BB-06, BB-07 | docs/team/ankitha.md |
| Arnav | BB-02, BB-04, BB-12 | docs/team/arnav.md |
| Arya | BB-03, BB-05, BB-11 | docs/team/arya.md |
| Yashwitha | BB-08, BB-09, BB-10 | docs/team/yashwitha.md |

Each member opens the corresponding `docs/ai-prompts/BB-XX.md` and gives its whole contents to their AI inside the shared repository checkout. These prompts contain source criteria, owned files, contracts, tests, dependencies, exclusions and handoff instructions. Do not ask four AIs to generate four independent projects.

## 6. Progress in dependency order

Shared foundation → thin seeded login/session/permission flow → registration → screening/results/search. Audit, privacy, validation, availability setup and UI work proceed alongside the features through fixed interfaces. Use labeled mocks only at approved boundaries and require real integration before Done.

Arya reviews and merges small PRs. Another teammate reviews Arya's own changes. Run the post-merge checklist in `docs/integration-checklist.md`. Points are provisional and story counts do not establish equal effort.

## 7. Know the limits

Health/CSRF and scaffolding tests work; complete business endpoints do not. Stub responses are 501 after relevant gates. Anonymous protected requests return 403 under the provisional session design. Local development is not production deployment. See `VALIDATION.md` for checks actually executed and checks still unrun.

## Keep private work materials out of Git

The clean main ZIP has no `docs/ai-prompts/` or `docs/team/` folders. The team workpack has the exact same shared code plus those private folders. They are ignored by `.gitignore`; do not force-add them. Do not overwrite a teammate's changed checkout with an entire ZIP. Import only the intended reviewed code changes.
