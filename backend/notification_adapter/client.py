"""PROPOSED public interface. Owner: Arya; internal contract only, no Sprint-2 delivery implementation. Coordinate signature changes."""
def send_notification_intent(*, event: dict) -> dict:
    """Future authenticated HTTP call to Node. Never direct Python/JS imports."""
    raise NotImplementedError('Notification dispatch is outside Sprint-1 business scope.')
