from django.db.models import Max

from inventory.models import CollectionEvent


def latest_confirmed_collection_date(*, donor_id):
    """None means a successful empty query; storage failures propagate."""
    return CollectionEvent.objects.filter(donor_id=donor_id, status='CONFIRMED').aggregate(
        latest=Max('collection_date'))['latest']
