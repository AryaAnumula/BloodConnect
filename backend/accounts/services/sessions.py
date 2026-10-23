"""PROPOSED public interface. Owner: Arnav / BB-02. Coordinate signature changes."""
def establish_session(*, request, user) -> None:
    """Use Django login/session rotation; called only after credential verification."""
    raise NotImplementedError('BB-02: session establishment is unfinished.')

def end_session(*, request) -> None:
    """Use Django logout/session invalidation under the approved policy."""
    raise NotImplementedError('BB-02: logout is unfinished.')
