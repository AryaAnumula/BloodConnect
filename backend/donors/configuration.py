"""PROPOSED public interface. Owner: Ankitha / BB-07; policy approval required. Coordinate signature changes."""
from core.errors import DecisionRequired

def approved_screening_rules() -> dict:
    raise DecisionRequired('Screening configuration and first-time-donor policy need approval.')
