"""PROPOSED public interface. Owner: Arya / BB-11; endpoint serializers remain feature-owned. Coordinate signature changes."""
def validate_shared_input(*, value, rule_name: str):
    """Shared validation entry point; implement only approved, reusable rules."""
    raise NotImplementedError('BB-11: shared input validation is unfinished.')
