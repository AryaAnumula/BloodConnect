"""PROPOSED public interface. Owner: Ankitha / BB-01. Coordinate signature changes."""
def authenticate_user(*, email: str, password: str):
    """Return active User; raise LoginRejected. Never log arguments."""
    raise NotImplementedError('BB-01: authentication service is unfinished.')
