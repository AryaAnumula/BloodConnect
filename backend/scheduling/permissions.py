"""BB-20/21 role gate for camp and slot actions (BC-D001, BC-D002, BC-D020).

Active, authenticated, non-superuser accounts only; there is no superuser bypass. STAFF and ADMIN
create/update/cancel camps and set up slots; DONOR, STAFF and ADMIN list; only DONOR books and
cancels their own appointment. REQUESTER, anonymous and inactive accounts have no scheduling
access. Replace the body with core.sprint2_permissions if that shared helper lands; this is the
only place scheduling checks camp roles.
"""
from rest_framework.exceptions import PermissionDenied

# REQUESTER never manages camps; no superuser bypass.
CAMP_ACTION_ROLES = {
    'create': frozenset({'ADMIN', 'STAFF'}),
    'update': frozenset({'ADMIN', 'STAFF'}),
    'cancel': frozenset({'ADMIN', 'STAFF'}),
    'list': frozenset({'DONOR', 'STAFF', 'ADMIN'}),
    # BB-21: slots by ADMIN or STAFF; booking DONOR only.
    'slot_create': frozenset({'ADMIN', 'STAFF'}),
    'slot_list': frozenset({'DONOR', 'STAFF', 'ADMIN'}),
    'book': frozenset({'DONOR'}),
    'own_appointments': frozenset({'DONOR'}),
    'cancel_own': frozenset({'DONOR'}),
}


def may_manage_camps(*, user, action) -> bool:
    if user is None or not getattr(user, 'is_authenticated', False):
        return False
    if not getattr(user, 'is_active', False):
        return False
    if getattr(user, 'is_superuser', False):
        return False
    return getattr(user, 'role', None) in CAMP_ACTION_ROLES.get(action, frozenset())


def require_camp_role(*, user, action) -> None:
    if not may_manage_camps(user=user, action=action):
        raise PermissionDenied()
