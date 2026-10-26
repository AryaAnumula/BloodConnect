"""BB-05: proposed D-10 allowlist, pending named schema/policy review."""
import uuid
from django.db import models


class SecurityEvent(models.Model):
    class EventType(models.TextChoices):
        LOGIN = 'login', 'Login'
        ACCESS_DENIED = 'access_denied', 'Access denied'

    class Outcome(models.TextChoices):
        FAILURE = 'failure', 'Failure'
        SUCCESS = 'success', 'Success'
        DENIED = 'denied', 'Denied'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    occurred_at = models.DateTimeField(auto_now_add=True, editable=False)
    event_type = models.CharField(max_length=24, choices=EventType.choices)
    actor_id = models.UUIDField(null=True, blank=True, editable=False)
    request_id = models.UUIDField(editable=False)
    outcome = models.CharField(max_length=12, choices=Outcome.choices)

    class Meta:
        ordering = ['occurred_at', 'id']
        indexes = [models.Index(fields=['event_type', 'occurred_at'], name='audit_type_time_idx')]
        constraints = [
            models.CheckConstraint(
                condition=(models.Q(event_type='login', outcome__in=['failure', 'success']) |
                           models.Q(event_type='access_denied', outcome='denied')),
                name='audit_allowed_event_pair'),
            models.CheckConstraint(
                condition=~models.Q(event_type='login', outcome='success') | models.Q(actor_id__isnull=False),
                name='audit_success_has_actor'),
        ]

    def __str__(self):
        return f'{self.event_type}:{self.id}'
