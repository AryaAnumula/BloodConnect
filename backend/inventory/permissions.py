"""Operational access does not grant clinical-data access."""
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission


def require_staff(actor):
    if not (actor is not None and getattr(actor, 'is_authenticated', False)
            and getattr(actor, 'is_active', False)
            and not getattr(actor, 'is_superuser', False)
            and getattr(actor, 'role', None) == 'STAFF'):
        raise PermissionDenied()


class IsInventoryStaff(BasePermission):
    def has_permission(self, request, view):
        require_staff(request.user)
        return True
