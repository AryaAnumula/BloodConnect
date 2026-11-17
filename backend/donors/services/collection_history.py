"""Canonical donor-history boundary for inventory (BC-D047 section 4).

Thin facade over the ONE existing writer in donors.services.collections: it only maps the
agreed `collection_date` keyword to that writer's `collected_on`. No second projection, no copied
logic, no commit of its own. The caller owns the atomic transaction (TransactionRequired
otherwise); invalid date -> DRF ValidationError, no profile -> NotFound; profile lock stays
FOR NO KEY UPDATE. Returns the date actually stored (never moves backwards).
"""
from datetime import date
from uuid import UUID

from donors.services import collections


def record_confirmed_collection(*, donor_id: UUID, collection_date: date) -> date:
    return collections.record_confirmed_collection(donor_id=donor_id, collected_on=collection_date)
