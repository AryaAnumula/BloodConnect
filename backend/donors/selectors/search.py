"""PROPOSED public interface. Owner: Yashwitha / BB-09; Ankitha query/API review. Coordinate signature changes."""
def search_donors(*, actor, blood_group=None, location=None, eligibility_status=None, page=1, page_size=20):
    """Return a paginated safe summary; never include donor health answers."""
    raise NotImplementedError('BB-09: donor search is unfinished.')
