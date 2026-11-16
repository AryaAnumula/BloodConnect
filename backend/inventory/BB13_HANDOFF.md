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
