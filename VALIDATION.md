# Validation report — historical main-base and current BB-11 refresh

This report records executed checks, not completion of BB-01–BB-12.

## Current BB-11 refresh (supersedes earlier runtime-status descriptions)

Main fcf58cf + existing PR33 e288514 + incremental refresh: 141 Django tests passed (0 skips), 7 Node tests passed, 29 availability-tool tests passed. System check, clean SQLite migration setup, migration consistency, repository/two OpenAPI/source checksum/link checks passed. Actual login/session/me/logout/audit reference is integrated; donor registration/screening/result/search/profile remain honest stubs. No donor model/migration added. See [BB-11 handoff](docs/handoffs/BB-11.md) and package logs for exact scope.

Linux Python3.13.14, Node24.14.1, Django5.2.18/DRF3.16.1. Docker/PostgreSQL, remote CI and real-browser end-to-end checks were NOT RUN for this refresh. Earlier Chromium observations below describe the old starter only, not this refresh. AI-assisted test review is not human approval, a GitHub push/merge, complete feature acceptance, performance or availability certification.

## Historical starter evidence (unchanged below)


## Passed

- Python 3.13 / Django 5.2.18 / DRF 3.16.1; Node 24.14.1. Exact Python pins are included.
- Migrations applied on a clean explicitly opted-in SQLite smoke database; no pending model changes.
- Django system check.
- **12 Django tests** and **5 JavaScript/Node tests**.
- Both OpenAPI documents structurally validated.
- Repository checks: 12-story index, Python syntax, relative Markdown links, supplied PDF checksum and manual CI wiring.
- No private AI prompt or member-guide folders are included in this package.
- Headless Chromium smoke executed on this package at 390×844.
- Browser observations: honest login/registration 501 messages, live/ready 200, anonymous donor search 403, no uncaught page error or horizontal login overflow.

## Not run / not established

- Docker builds/Compose startup and PostgreSQL execution: tooling was unavailable. SQLite does not prove chosen-engine constraints, concurrency or production readiness.
- Remote GitHub Actions, branch protection, PR approvals or merges: not performed. The workflow is manual and still proposed.
- Complete feature acceptance, real session/login/registration/screening/search, full RBAC/privacy and integrated input/audit coverage: unfinished.
- Approved operational observation window and 99% availability: not established. Tool unit tests are not this evidence.
- NFR-001 load/performance and NFR-003 end-to-end usability acceptance: not established.
- Production security/deployment or dependency vulnerability certification: not performed.

## Reproduce

Use README.md, docs/testing.md and scripts/check.sh. Command exit codes are recorded in docs/planning/starter-validation.json. Tests of stub/probe behavior must evolve deliberately as actual features land; do not delete assertions merely to hide failures.

## BB-03 implementation checkpoint

The original baseline results above are retained as historical starter evidence. This BB-03 change additionally passed 16 total Django tests, 29 monitoring-tool tests and 5 JavaScript/Node regression tests. Both API specifications, system checks, SQLite migration consistency and protocol dry-run passed. Operational approval/window, Docker/PostgreSQL and remote CI remain unverified. See [BB-03 handoff](docs/handoffs/BB-03.md) for scope and actual evidence limits.
