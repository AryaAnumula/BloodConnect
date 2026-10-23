"""PROPOSED public interface. Owner: Ankitha / BB-06; Arnav schema review. Coordinate signature changes."""
def register_donor(*, validated_data: dict):
    """Atomically create donor User/Profile; return profile. Reject duplicate email/mobile."""
    raise NotImplementedError('BB-06: registration is unfinished.')
