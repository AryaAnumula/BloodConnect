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
