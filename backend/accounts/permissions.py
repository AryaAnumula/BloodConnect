"""PROPOSED public interface. Owner: Arnav / BB-04, BB-12. Coordinate signature changes."""
def is_authorized_staff(*, user) -> bool:
    """Require active authenticated staff and the approved clinical-data permission."""
    raise NotImplementedError('BB-04/12: approved staff access policy is required.')

def may_view_donor_health(*, user, donor_user_id) -> bool:
    """Allow own donor or explicitly authorized staff; ADMIN is not automatic access."""
    raise NotImplementedError('BB-12: object policy is unfinished.')
