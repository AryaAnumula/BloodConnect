from django.conf import settings
from django.views.generic import TemplateView


class ReportingPage(TemplateView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['reporting_synthetic'] = settings.DEBUG and getattr(settings, 'BLOODCONNECT_REPORT_SOURCE', 'domain') == 'synthetic'
        return context
