"""PROPOSED public interface. Owner: Arnav / BB-12. Coordinate signature changes."""
from uuid import UUID

def donor_profile_for_actor(*, actor, donor_id: UUID):
    """Return only the profile permitted by the object/field policy."""
    raise NotImplementedError('BB-12: authorized profile lookup is unfinished.')
