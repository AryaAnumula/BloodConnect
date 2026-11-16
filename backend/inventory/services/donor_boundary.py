"""Call the donor-owned BC-D047 boundary, without an alternate writer."""
from importlib.util import find_spec

from inventory.exceptions import InventoryUnavailable


def record_confirmed_collection(*, donor_id, collection_date):
    # Only a genuinely absent facade becomes unavailable. Broken imports remain failures.
    if find_spec('donors.services.collection_history') is None:
        raise InventoryUnavailable()
    from donors.services.collection_history import record_confirmed_collection as record
    return record(donor_id=donor_id, collection_date=collection_date)
