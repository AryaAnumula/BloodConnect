"""PROPOSED public interface. Owner: Arnav / BB-02. Coordinate signature changes."""
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import login, logout


def establish_session(*, request, user) -> None:
    """Use Django login/session rotation; called only after credential verification."""
    if not getattr(user, 'is_active', False):
        raise ValueError('Cannot establish a session for an inactive account.')
    # Django's login() rotates the session key and stores only the user id,
    # never the password or a custom token.
    login(request, user)
    # D-03/04 (approved): absolute lifetime from sign-in, no sliding renewal.
    # A timedelta fixes ONE expiry moment inside the session; later session writes
    # re-save that same moment instead of restarting the clock. (A plain integer
    # would slide on every write, so never pass an int here.)
    request.session.set_expiry(timedelta(seconds=settings.SESSION_COOKIE_AGE))


def end_session(*, request) -> None:
    """Use Django logout/session invalidation under the approved policy."""
    # logout() flushes the session: server-side data is deleted and the old
    # session key can no longer be used.
    logout(request)