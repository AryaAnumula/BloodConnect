# BB-11 refresh — start here

## What this changes

Based on main `fcf58cf405d7a97aa741103fe2539b80b144e9a7` plus existing BB-11 PR #33 `e2885148869230211b3840a91608edbdf9adc38a`.
This is shared-provider delivery and a working login reference, **not the finished BloodConnect application or full SEC-003 acceptance**. No new SRS IDs, story titles or acceptance criteria are created. Sprint 1 is the team's planning override; adopted source text is unchanged.

- Reuses the BB-11 strict fields/serializers and opt-in JSON parser.
- Fixes non-finite exponent overflow (`1e999`) as well as duplicate/malformed JSON handling.
- Wires the existing **BB-01 login**, keeping real BB-02 sessions, BB-04 `/auth/me` and BB-05 audit.
- Adds real-provider login → me → logout/replay tests, invalid-input tests and bounded audit-failure regression.
- Fixes shared frontend helper parsing of an empty logout 204 body. No frontend framework added.
- Updates API status/guide, owner recipes and adoption matrix. No donor model/migration, clinical rule, new dependency, new endpoint, global parser setting or Sprint-2 feature is added.

## Read in this order

1. [API guide](api/endpoints.md) and [OpenAPI field authority](api/openapi.yaml).
2. [Feature-owner recipes](api/bb11-feature-recipes.md): exact imports/calls, auth and transaction boundaries.
3. [Owner handoff](bb11-consumer-handoff.md) and [coverage matrix](input-validation-matrix.md).
4. [Decisions](decisions.md), [permissions](permissions-usage.md), [interfaces](interfaces.md).
5. [BB-11 evidence/handoff](handoffs/BB-11.md).

## What each person does after the provider is reviewed and merged

- **Ankitha:** merge current main; review login integration; implement BB-06 registration then BB-07 screening with existing serializers after decisions are approved. Own transactional persistence and tests.
- **Yashwitha:** merge main; BB-10 may use the documented registration contract for UI-only work, clearly mark mocks; BB-08 consumes result projection, BB-09 consumes search serializer and authorized-staff gate. Real feature success needs actual APIs.
- **Arnav:** merge main; build BB-12 ownership helper and safe profile projection; coordinate endpoint wiring with Ankitha/Yashwitha. Do not apply staff-only permission to routes that permit the owning donor.
- **Arya:** deliver provider/reference; review combined evidence, not rewrite all remaining features. Keep BB-11 acceptance pending until feature-specific tests are linked.

Merge main into a clean member branch (`git fetch origin`, `git merge origin/main`; Ankitha's fork uses `upstream/main`). No force pushes. Resolve shared files jointly. Use small story-specific PRs and commits; the branch owner pushes only their own work. A conflict-free merge is not proof of correctness.

## Decision boundaries

Recorded D-03, session part of D-04, D-09 staff gate/role matrix apply. The 12-character registration minimum is still a **proposal**, not approved merely because a candidate serializer exists. D-05 registration/normalization, D-07 clinical rules/first-time donors, D-08 freshness/states, D-10 operational audit policy, D-11 availability window and D-12 load protocol still need explicit decisions. BB-12 field-level visibility and record-denial 403/404 semantics must be recorded before production endpoint wiring. Do not invent medical thresholds.

## Implementation order, not story-number order

Provider/login reference → review/merge → all members sync → approved registration model/contract (BB-06) + BB-12 helper → screening (BB-07) → result (BB-08). UI (BB-10) and search query/UI parts (BB-09) can proceed independently against explicit contracts; final integration follows real records, freshness and permission policies. Shared tests are not counted as six completed stories.

## Tests / limits

Use `sh scripts/check.sh` only in an environment with both Python and Node24 (such as the configured CI job); it preserves audit, availability and frontend suites. The web Docker image is Python-only: run Python checks in its container and Node tests on the host, as shown in README.md. Windows without Docker can use SQLite **smoke** checks only; package instructions contain exact commands. AI-assisted local results are recorded in the handoff, never a human approval. Docker/PostgreSQL, remote CI and real-browser end-to-end flows are not certified by these local checks.
