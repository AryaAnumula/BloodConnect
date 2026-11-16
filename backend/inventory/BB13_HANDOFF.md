# BB13 actual donor integration - WIP, ready for owner review

Contract: v1.1, Decision BC-D047, authoritative local handoff SHARED_IMPLEMENTATION_CONTRACT3.md. Digest is recorded in acceptance/evidence/contract-reference.json. Earlier evidence below remains historical; the current results supersede the former missing-donor blocker and PostgreSQL16-pending statements.

## Actual source composition

- Inventory production code: PR56 93f8e8cacdebe1b27eca6ad7d7609ee40ada09a5; route acceptance checks: 419cc5cfd90293bd5d5a541e1efe9cd00179bebb. Production Python was unchanged during these checks.
- Actual donor facade, required-argument evaluator, screening and donor tests: PR51 a93f01cccfe2a242f0a91f3f3646775ff4282297, fetched and verified as the relevant published tranche.
- Shared routes: PR59 739ff48524fc9552fa3c92a343247b711c10e4c2 inventory-routes.patch, applied to the isolated combined source only.
- Shared providers: PR60 42afc198b70fd9d3821580fbbd25d4ee2fda4653; PR61 8b1349f295170525b6d668e3fb55e48586950d58; actual issue implementation PR64 b5f72bee8ab16022154599c9a5354a9f6da69272.
- Companion core seeder patch: exact PR51 a93f01c docs/sprint2/bb21-seeder-history-guard.patch applied cleanly to the combined source containing the existing seeder. No donor, scheduling, core or shared route source is committed in this PR.

## PostgreSQL16 acceptance evidence

Database: PostgreSQL 16.16, compiled by Visual C++ build 1944, 64-bit; isolated local port55416. Actual implementations, no donor evaluator/facade adapters.

Commands in the isolated source use the project .venv Python and the actual config.urls:

```text
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test inventory.tests.test_real_collection_integration --noinput --verbosity 2
python manage.py test core.tests.test_demo_dataset_seeding donors.tests.test_confirmed_collection donors.tests.test_evaluation --noinput --verbosity 1
python manage.py test inventory.tests.test_real_collection_integration inventory.acceptance.intake_routes --noinput --verbosity 1
```

- System check: zero issues. Migration drift: no changes detected.
- Actual donor integration before transition: 7 pass / 0 fail / 0 skip, 1.931s. Includes actual intake, extra component, projection/event/unit rollback, actual booking freshness, preserved historical assessments/reconciliation, ahead-of-source rejection, source failure and separate-connection collection race.
- Actual seeder/facade/evaluator tests with companion patch: 47 pass / 0 fail / 0 skip, 50.094s. Preserves seeder replay/conflict guards and separate original/confirmed snapshots.
- After controlled history-v2 transition: actual seven plus real shared-route guards, 9 pass / 0 fail / 0 skip, 1.948s. No URL override or donor adapter.
- Prior separately pinned 67-test PostgreSQL16.16 suite and six concurrency checks remain valid historical evidence; unchanged large suites were not repeated merely to publish.

## Controlled transition and fresh browser

On a new disposable PostgreSQL16 database with two synthetic donors, dry-run checked2/advance1 without writes; explicit apply checked2/advance1 through the actual donor facade; repeat apply checked2/advance0. All historical assessment fields/timestamps stayed unchanged. Only then was the isolated donor configuration changed from demo-2026-10-v1 to demo-2026-11-history-v2. Numerical screening values were identical; old assessments became rules-stale and historical projection changes were history-stale. Actual screening created a new current assessment for a donor with no collection events.

The real authenticated STAFF browser submitted a new RBC donation with the optional event field blank on 17 November2026. API201 created one new event and unit, collection2026-11-17, server expiry2026-12-29. Database verification found projection/event/unit dates equal; duplicate replay409; the actual saved-result reader marked the pre-intake assessment history-stale; actual scheduling booking rejected it and created no appointment. Old assessments remained unchanged. See acceptance/evidence/fresh-intake.png and bb13-controlled-transition.json. This is fresh intake evidence, separate from the earlier historical-event walkthrough.

## Consume now / remaining central integration

Arnav can consume inventory.models.BloodUnit, inventory.0001_initial, inventory.services.allocation.allocate_units and inventory.exceptions.UnitConflict/UnsafeUnit now. Caller owns transaction.atomic; returns UUID-sorted [{"unit_id":"<uuid>","quantity":1}]. Migration depends on existing donors.0003 and swappable AUTH_USER_MODEL.

The tested companion seeder change belongs to Arya's integrated backend/core source, using Ankitha's published patch; it does not belong in inventory-owned PR56. Ankitha/Arya must carry the tested donor rules-version switch in their shared configuration after reconciliation on the target database. The isolated successful transition is evidence, not a claim that another database was initialized. Arya carries shared route integration and performs final review/merge. No outstanding inventory test failure or missing donor tranche remains in this composition. Keep PR56 WIP until required review and target composition rollout are complete.

## Historical record (superseded blockers retained for provenance)

## 16 November 2026 continuation - current remaining gate

The fixed intake caller, foundation and allocation remain published; production Python is unchanged from the prior PostgreSQL16 validation. API tests now explicitly use inventory.tests.urls, so they work under a real config.urls runner without pretending Arya has already wired production routes. Component fixtures use the current configured rules version. Missing-facade503 and incompatible-evaluator503 are explicit negative fixtures, not assumptions that a callee stays absent forever.

Actual browser walkthrough at inventory7997bd996c17e8db608bda170525463046f9b29d: STAFF login; addPLASMA to an existing historical event via POST201, server expiry2027-11-12 for collection2026-11-12; duplicate replay409; fresh eligible donor intake503 with no projection/event/unit change. Exact select labels were fixed. The initial historical event is a labelled fixture, so this does not prove fresh-donation integration.

New test_real_collection_integration.py uses NO donor adapters and calls actual screening, intake, saved-result reader, scheduling booking and reconciliation. It covers projection/event/unit atomicity and rollback, history-stale booking rejection, historical assessment preservation, controlled reconciliation/resumed intake, fail-closed source errors and a real collection race. Current run:7tests/0passed/7explicit skips, because PR51 remains faf570e12eaff5ef412905d24e2027e7765d3482 without the published facade/evaluator tranche. Do not count those skips as integration acceptance. Consume the exact new PR51 SHA once published, then run those tests and the coordinated history-v2 transition. No donor source was changed.

Changed integration-focused PostgreSQL16.16 run at d8b5ad8c1a839ff567dfdc22f551dfc4512c3a52:32run,25pass,7explicit donor skips,0fail. The original65-test PostgreSQL18.6 evidence and67-test PostgreSQL16 evidence remain separate historical records with their original exact SHAs. Whole BB13 acceptance remains WIP.

---

# BB-13 foundation WIP reference

This PR contains only inventory-owned BB-13 changes. Shared provider/donor/settings prerequisites are not copied into this branch. Only Arya merges.

Actual models exported from inventory.models: CollectionEvent and BloodUnit.
Actual Django-generated migration: inventory.0001_initial (backend/inventory/migrations/0001_initial.py). Dependencies: donors.0003_donorprofile_last_confirmed_collection_date_and_more and swappable AUTH_USER_MODEL. The old branch alone lacks the shared donor0003/registration baseline; compose the agreed shared source, do not fake migrations.

Arnav's interface:

```python
from inventory.models import BloodUnit
from inventory.services.allocation import allocate_units
from inventory.exceptions import UnitConflict, UnsafeUnit

allocate_units(*, actor, unit_ids: list, blood_group: str, component_type: str, issued_at) -> list[dict]
# Returns UUID-sorted [{"unit_id": "<uuid>", "quantity": 1}]
```

Caller must own transaction.atomic(). Units lock in UUID order; usability/expiry uses a fresh post-lock Kolkata date. Writes only ISSUED on units; no IssueRecord, request update, independent commit or transport. Caller rollback restores unit states. UnitConflict409/unit_conflict; UnsafeUnit422/unsafe_unit; invalid400; missing404; forbidden403; storage503. Arnav owns IssueRecord and its FK migration against inventory0001.

New intake calls the fixed donor facade and pure evaluator; it fails closed until Ankitha delivers donors.services.collection_history.record_confirmed_collection(*,donor_id,collection_date) and evaluate(...,confirmed_collection_date,...), with all callers updated. No second donor writer or donor modifications are included.

Original evidence remains unchanged:65 owned-composition tests PASS at67d8892f6f38d10dd58c503ac25d3c591e368829 on PostgreSQL18.6,0skips,34.767s. That exact source includes later inventory stories in a separately labelled test composition; it is NOT this PR's standalone head. BB13 checkpoint46PASS on PostgreSQL18.6 includes actual separate-connection collection/allocation races with explicitly labelled donor boundary adapters. No PostgreSQL16 acceptance is claimed. See the existing delivery reports/logs for exact source pins. Run lightweight checks on the publication composition; PostgreSQL16 remains required before final acceptance.

Routes are additive includes for Arya's shared integration: api/v1/ -> inventory.urls and root -> inventory.page_urls. No shared route/settings file is overwritten by this owned patch. BB14/15 are separate WIP PRs, never copied into PR56.
