from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.views.generic import TemplateView
from rest_framework.exceptions import PermissionDenied as ApiPermissionDenied

from reporting.permissions import require_admin


class ReportingPage(TemplateView):
    def dispatch(self, request, *args, **kwargs):
        try:
            require_admin(actor=request.user)
        except ApiPermissionDenied:
            raise PermissionDenied from None
        response = super().dispatch(request, *args, **kwargs)
        response['Cache-Control'] = 'no-store'
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['reporting_synthetic'] = settings.DEBUG and getattr(settings, 'BLOODCONNECT_REPORT_SOURCE', 'domain') == 'synthetic'
        return context
