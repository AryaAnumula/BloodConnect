"""PROPOSED public interface. Owner: Ankitha / BB-07. Coordinate signature changes."""
from uuid import UUID

def screen_donor(*, actor, donor_id: UUID, answers: dict):
    """Return persisted result under approved rules; own transaction and result write."""
    raise NotImplementedError('BB-07: screening is unfinished.')
