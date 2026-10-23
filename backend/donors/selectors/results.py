"""PROPOSED public interface. Owner: Yashwitha / BB-08; Arnav access review. Coordinate signature changes."""
from uuid import UUID

def latest_eligibility_result(*, actor, donor_id: UUID):
    """Return authorized persisted result; absence is a defined not-found state."""
    raise NotImplementedError('BB-08: result lookup is unfinished.')
