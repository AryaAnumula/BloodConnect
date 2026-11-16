from django.views.generic import TemplateView

from inventory.permissions import require_staff


class IntakePage(TemplateView):
    template_name = 'inventory/intake.html'

    def dispatch(self, request, *args, **kwargs):
        # Django page access uses the same gate; translate the DRF exception for HTML.
        from django.core.exceptions import PermissionDenied as PageDenied
        from rest_framework.exceptions import PermissionDenied
        try:
            require_staff(request.user)
        except PermissionDenied as exc:
            raise PageDenied() from exc
        return super().dispatch(request, *args, **kwargs)


class StockPage(IntakePage):
    template_name = 'inventory/stock.html'

    def dispatch(self, request, *args, **kwargs):
        from django.core.exceptions import PermissionDenied as PageDenied
        from rest_framework.exceptions import PermissionDenied
        from inventory.permissions import require_stock_reader
        try:
            require_stock_reader(request.user)
        except PermissionDenied as exc:
            raise PageDenied() from exc
        return TemplateView.dispatch(self, request, *args, **kwargs)
