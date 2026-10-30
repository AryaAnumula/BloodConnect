# Public service contracts — PROPOSED

All return values are JSON-ready DTOs, not inconsistent mixtures of ORM instances and dictionaries. Validate actor at public boundary. Exception class names below are proposed domain names; agree central translation before callers depend on them. No implementation supplied by this foundation.

## inventory.services.units.record_unit

```python
from inventory.services.units import record_unit
record_unit(*, actor, data: dict) -> dict
```

Owner: Yashwitha; stories: BB-13.

Return/transaction/side effects: Own atomic collection/unit write and domain validations; no HTTP calls; return BloodUnit DTO.

Expected exceptions: ValidationError, DecisionRequired, UnitConflict, IneligibleDonor.

Calling modules: UI/API, fixtures.

## inventory.selectors.stock.stock_summary

```python
from inventory.selectors.stock import stock_summary
stock_summary(*, actor, filters: dict, page: int=1, page_size: int=20) -> dict
```

Owner: Yashwitha; stories: BB-14.

Return/transaction/side effects: Read only; StockPage; available stock derived from usable unit rows.

Expected exceptions: PermissionDenied, ValidationError, DecisionRequired.

Calling modules: stock API, reporting.

## inventory.services.allocation.allocate_units

```python
from inventory.services.allocation import allocate_units
allocate_units(*, actor, unit_ids: list, blood_group: str, component_type: str, issued_at) -> list[dict]
```

Owner: Yashwitha; stories: BB-13/16.

Return/transaction/side effects: Requires caller atomic transaction; lock units sorted UUID; validate/recheck usability; mark ISSUED; caller creates unique IssueRecords. Return unit id/quantity DTOs; rollback with caller; never own separate commit.

Expected exceptions: UnitConflict, UnsafeUnit, ValidationError.

Calling modules: Arnav issue_request ONLY.

## inventory.selectors.reporting.collection_wastage_totals

```python
from inventory.selectors.reporting import collection_wastage_totals
collection_wastage_totals(*, start, end) -> dict
```

Owner: Yashwitha; stories: BB-13/24.

Return/transaction/side effects: Read only aware UTC half-open interval; explicitly defined collection event/unit/wastage counts.

Expected exceptions: DecisionRequired.

Calling modules: Arya report selector.

## inventory.services.alerts.evaluate_alerts

```python
from inventory.services.alerts import evaluate_alerts
evaluate_alerts(*, actor, now) -> dict
```

Owner: Yashwitha; stories: BB-15.

Return/transaction/side effects: Own atomic condition/dedup record plus notification intent; no network inside transaction.

Expected exceptions: DecisionRequired, ValidationError.

Calling modules: controlled management command.

## blood_requests.services.submission.submit_request

```python
from blood_requests.services.submission import submit_request
submit_request(*, actor, data: dict) -> dict
```

Owner: Arnav; stories: BB-17.

Return/transaction/side effects: Own atomic request + optional durable notification intent; derive requester from actor.

Expected exceptions: PermissionDenied, ValidationError, DecisionRequired.

Calling modules: request creation API.

## blood_requests.services.review.review_request

```python
from blood_requests.services.review import review_request
review_request(*, actor, request_id, status: str, rejection_reason: str | None=None) -> dict
```

Owner: Arnav; stories: BB-18.

Return/transaction/side effects: Own atomic request row lock and valid transition.

Expected exceptions: NotFound, PermissionDenied, InvalidTransition.

Calling modules: review API.

## blood_requests.services.issue.issue_request

```python
from blood_requests.services.issue import issue_request
issue_request(*, actor, request_id, unit_ids: list) -> dict
```

Owner: Arnav; stories: BB-16.

Return/transaction/side effects: Own outer transaction; lock request then invoke inventory allocation; write unique issue records and exact fulfilled state; persist notification intent before commit if relevant.

Expected exceptions: NotFound, PermissionDenied, UnitConflict, UnsafeUnit, InvalidTransition.

Calling modules: issue API.

## blood_requests.selectors.reporting.request_issue_totals

```python
from blood_requests.selectors.reporting import request_issue_totals
request_issue_totals(*, start=None, end=None) -> dict
```

Owner: Arnav; stories: BB-18/23/24.

Return/transaction/side effects: Read only; pending count current and issue totals in aware half-open range.

Expected exceptions: DecisionRequired, ValidationError.

Calling modules: Arya dashboard/report.

## scheduling.services.camps.create_camp

```python
from scheduling.services.camps import create_camp
create_camp(*, actor, data: dict) -> dict
```

Owner: Ankitha; stories: BB-20.

Return/transaction/side effects: Own atomic valid camp write; separate update_camp and cancel_camp follow same actor/id/data convention.

Expected exceptions: PermissionDenied, ValidationError, CapacityConflict.

Calling modules: camp API.

## scheduling.services.appointments.book_appointment

```python
from scheduling.services.appointments import book_appointment
book_appointment(*, actor, slot_id) -> dict
```

Owner: Ankitha; stories: BB-21.

Return/transaction/side effects: Own outer atomic; lock camp then slot; validate current eligibility; prevent duplicate/capacity; create appointment+reminder intent together.

Expected exceptions: NotFound, PermissionDenied, CapacityConflict, IneligibleDonor.

Calling modules: booking API.

## scheduling.selectors.summary.upcoming_camp_count

```python
from scheduling.selectors.summary import upcoming_camp_count
upcoming_camp_count(*, now) -> int
```

Owner: Ankitha; stories: BB-20/23.

Return/transaction/side effects: Read only approved ACTIVE future definition.

Expected exceptions: DecisionRequired.

Calling modules: dashboard.

## notification_adapter.services.intents.enqueue_intent

```python
from notification_adapter.services.intents import enqueue_intent
enqueue_intent(*, event_id, recipient_id, event_type: str, record_id, due_at, channels: list[str]) -> dict
```

Owner: Arya; stories: BB-15/22.

Return/transaction/side effects: Requires caller transaction.atomic; write idempotent OutboxIntent; no network and no independent commit; return intent UUID/state.

Expected exceptions: ValidationError, EventConflict.

Calling modules: inventory alerts, appointments/camp cancellation.

## notification_adapter.services.dispatch.dispatch_due

```python
from notification_adapter.services.dispatch import dispatch_due
dispatch_due(*, now, limit: int=100) -> dict
```

Owner: Arya; stories: BB-22.

Return/transaction/side effects: Claim pending intents with lease/attempt record; no long DB lock during HTTP; update receipt/next retry; retry after crash safely using event/channel dedup.

Expected exceptions: NotificationTransportUnavailable.

Calling modules: management command/scheduled invocation.

## notification_adapter.client.send_notification_intent

```python
from notification_adapter.client import send_notification_intent
send_notification_intent(*, event: dict) -> dict
```

Owner: Arya; stories: BB-22.

Return/transaction/side effects: Existing import path retained. Dedicated-token private HTTP to existing Node path; bounded timeout. Return MockReceipt only on real mock acknowledgment; no direct Python/JS imports.

Expected exceptions: NotificationTransportUnavailable, ValidationError.

Calling modules: dispatcher only.

## reporting.selectors.dashboard.dashboard_for_admin

```python
from reporting.selectors.dashboard import dashboard_for_admin
dashboard_for_admin(*, actor, now) -> dict
```

Owner: Arya; stories: BB-23.

Return/transaction/side effects: Read only approved operational summaries; no private health projection; dependency outage→redacted503 not invented zeros.

Expected exceptions: PermissionDenied, ReportingUnavailable.

Calling modules: dashboard API.

## reporting.selectors.activity.activity_report

```python
from reporting.selectors.activity import activity_report
activity_report(*, actor, from_date, to_date) -> dict
```

Owner: Arya; stories: BB-24.

Return/transaction/side effects: Read only combine owner selectors; convert approved local dates into aware UTC half-open interval.

Expected exceptions: PermissionDenied, ValidationError, DecisionRequired, ReportingUnavailable.

Calling modules: reports API.

## Lock order

Issue: request row → unit rows sorted UUID → issue rows; inventory allocation never locks request rows. Booking: camp → slot → appointment; walk-in has no camp. Alert dispatcher never holds long database locks while contacting Node. Always recheck state inside the transaction; UI prechecks do not prevent races. Multi-unit issue is all-or-nothing and unique unit issue constraint is final protection. Retry conflict returns controlled409, not partial success.

## Import direction

blood_requests.services.issue → inventory.services.allocation; inventory NEVER imports issue service. reporting→inventory/blood_requests/scheduling selectors; domain apps NEVER import reporting. inventory/scheduling→notification_adapter.services.intents; notification adapter NEVER imports calling domain services at import time. Shared role/validation utilities do not import feature models. Deferred event handlers use minimal record references; avoid circular models/imports.

## Operational role provider (PROPOSED; S2-04 approval first)

Primary supporting writer Ankitha, shared-file coordination Arya. New backend/core/sprint2_permissions.py (not an existing implementation):

```python
from core.sprint2_permissions import (is_operational_staff, IsOperationalStaff, IsOperationalAdmin, IsOperationalRequester, IsOperationalDonor)
def is_operational_staff(*, user) -> bool: ...
```

Pure predicate requires authenticated active non-superuser role STAFF; no automatic clinical permission. Each DRF class returns bool from has_permission(request,view), accepts exactly named operational role, no writes/network/audit side effect. Unauthorized DRF exception handling remains existing shared envelope/audit path; do not double-log. Camp action-specific gate combines ADMIN/STAFF only after S2-04 approval. Object ownership remains service/selector responsibility. Callers: inventory/request/scheduling/reporting API gates. Existing accounts.permissions clinical gates stay unchanged. Tests cover all roles, inactive, anonymous and all superusers; no runtime code included by foundation.

## Scheduling reminder read boundary (PROPOSED, owned by Ankitha)

```python
from scheduling.selectors.reminders import reminder_context
def reminder_context(*, appointment_id) -> dict: ...
```

Read-only internal selector; no transaction ownership/network/notification writes. Return appointment_id, donor_user_id, slot_id, starts_at (aware UTC), appointment_status, camp_status (nullable for walk-in) and revision/reference sufficient to reject canceled/rescheduled reminders. No health answers/contact payload. Exceptions: NotFound, DecisionRequired; caller Arya BB22 dispatcher rechecks before sending. Do not use a browser endpoint for this backend call. Coordinate exact added DTO/revision semantics before implementation; no selector implementation supplied in pack.
