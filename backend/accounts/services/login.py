"""BB-01, Ankitha. Login service. Never log arguments."""
from django.contrib.auth import authenticate


class LoginRejected(Exception):
    """Invalid credentials or account not allowed to sign in.

    Deliberately generic so callers cannot tell which part failed.
    """


def authenticate_user(*, email: str, password: str):
    """Return active User; raise LoginRejected."""
    normalized = (email or '').strip().lower()
    if not normalized or not password:
        raise LoginRejected()
    user = authenticate(request=None, email=normalized, password=password)
    if user is None or not user.is_active:
        raise LoginRejected()
    return user