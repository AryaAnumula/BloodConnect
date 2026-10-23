"""PROPOSED public interface. Owner: Arya / BB-05; caller hooks Ankitha/Arnav. Coordinate signature changes."""
from uuid import UUID

def record_security_event(*, event_type: str, actor_id: UUID | None, request_id: str, outcome: str) -> None:
    """Allowlisted metadata only. No password/token/health payload arguments."""
    raise NotImplementedError('BB-05: durable audit recording is unfinished.')
