"""PROPOSED public interface. Owner: Arnav / BB-02. Coordinate signature changes."""
from django.contrib.auth import login, logout


def establish_session(*, request, user) -> None:
    """Use Django login/session rotation; called only after credential verification."""
    if not getattr(user, 'is_active', False):
        raise ValueError('Cannot establish a session for an inactive account.')
    # Django's login() rotates the session key and stores only the user id,
    # never the password or a custom token.
    login(request, user)


def end_session(*, request) -> None:
    """Use Django logout/session invalidation under the approved policy."""
    # logout() flushes the session: server-side data is deleted and the old
    # session key can no longer be used.
    logout(request)