from django.db import DatabaseError

from inventory.exceptions import InventoryUnavailable
from inventory.models import InventoryAlert
from inventory.permissions import require_staff
from inventory.serializers import StockQuery


def alert_list(*, actor, filters):
    require_staff(actor)
    query = StockQuery(data=filters)
    query.is_valid(raise_exception=True)
    values = dict(query.validated_data)
    page, size = values.pop('page'), values.pop('page_size')
    try:
        rows = InventoryAlert.objects.filter(**values).select_related('intent').order_by('-created_at', '-id')
        count = rows.count()
        results = []
        for row in rows[(page-1)*size:page*size]:
            state = row.intent.state
            if state in ('PENDING', 'BLOCKED', 'LEASED'):
                state = 'PENDING'
            if state not in ('PENDING', 'DELIVERED', 'FAILED'):
                raise InventoryUnavailable()
            results.append({'id': str(row.pk), 'kind': row.kind, 'blood_group': row.blood_group,
                'component_type': row.component_type, 'unit_id': str(row.unit_id) if row.unit_id else None,
                'created_at': row.created_at.isoformat(), 'notification_state': state})
        return {'count': count, 'page': page, 'page_size': size, 'results': results}
    except DatabaseError as exc:
        raise InventoryUnavailable() from exc
