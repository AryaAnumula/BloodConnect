from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission


def require_admin(*, actor):
    if (actor is None or not getattr(actor, 'is_authenticated', False)
            or not getattr(actor, 'is_active', False) or getattr(actor, 'is_superuser', False)
            or getattr(actor, 'role', None) != 'ADMIN'):
        raise PermissionDenied()


class IsReportingAdmin(BasePermission):
    def has_permission(self, request, view):
        require_admin(actor=request.user)
        return True
