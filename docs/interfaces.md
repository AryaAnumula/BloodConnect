# Cross-module public interfaces (PROPOSED)

These signatures are deliberately unfinished and raise NotImplementedError/DecisionRequired until their owning story is implemented. Import a service/selector directly inside Django; do not call your own HTTP API from backend services. Browser callers use API HTTP; Python-to-Node uses private authenticated HTTP. Never import JavaScript as a Python function.

## Ownership, returns, errors and transactions

| Interface | Target return / errors | Transaction and side effects | Caller |
| --- | --- | --- | --- |
| authenticate_user | active User / LoginRejected | No duplicate user writes; audit hooks coordinated | LoginView |
| establish_session / end_session | None / approved auth error | Django session store/cookie rotation or invalidation; not custom token storage | LoginView / LogoutView |
| register_donor | created DonorProfile / validation or duplicate-contact domain error | Own atomic User+Profile creation; no public elevated roles | RegistrationView |
| screen_donor | persisted EligibilityResult / validation, forbidden, not found or DecisionRequired | Own atomic result write/versioning; rule read must be approved | ScreeningView |
| latest_eligibility_result | result / no-result/not-found/forbidden | Read only; freshness determined under D-08 | ResultView |
| search_donors | pagination dict matching DonorPage / invalid filters or forbidden | Read only; bounded query/projection, no health fields | SearchView |
| donor_profile_for_actor | profile projection / not found or forbidden | Read only with own/authorized-staff policy | ProfileView |
| may_view_donor_health / is_authorized_staff | bool after approved policy | Read only; ADMIN role alone does not grant access | donor API/selectors |
| record_security_event | None / approved audit failure behavior | Durable allowlisted event write; decide behavior if audit persistence fails | login/denial hooks |
| validate_shared_input | validated value / controlled validation error | No database writes; avoid destructive blanket escaping/stripping | owner serializers |
| approved_screening_rules | approved versioned rule dict / DecisionRequired | No silent clinical defaults | screening service |
| send_notification_intent | future delivery acknowledgement / defined transport error | DEFERRED: no Sprint-1 event dispatch or fake delivery | future modules |

Domain-to-HTTP error translation must use the OpenAPI envelope; agree custom exception classes before changing callers. Do not return a mix of model objects and dictionaries from the same service. Controllers/serializers translate the documented service result to the exact response schema. Consumers must coordinate any schema change.

## File-level signatures

### `backend/accounts/permissions.py`

```python
def is_authorized_staff(*, user) -> bool:
def may_view_donor_health(*, user, donor_user_id) -> bool:
```

PROPOSED public interface. Owner: Arnav / BB-04, BB-12. Coordinate signature changes.

### `backend/accounts/services/login.py`

```python
def authenticate_user(*, email: str, password: str):
```

PROPOSED public interface. Owner: Ankitha / BB-01. Coordinate signature changes.

### `backend/accounts/services/registration.py`

```python
def register_donor(*, validated_data: dict):
```

PROPOSED public interface. Owner: Ankitha / BB-06; Arnav schema review. Coordinate signature changes.

### `backend/accounts/services/sessions.py`

```python
def establish_session(*, request, user) -> None:
def end_session(*, request) -> None:
```

PROPOSED public interface. Owner: Arnav / BB-02. Coordinate signature changes.

### `backend/audit/events.py`

```python
def record_security_event(*, event_type: str, actor_id: UUID | None, request_id: str, outcome: str) -> None:
```

PROPOSED public interface. Owner: Arya / BB-05; caller hooks Ankitha/Arnav. Coordinate signature changes.

BB-05 candidate implements this signature. `login/failure` (actor null), `login/success` (actor UUID) match PR #30; `access_denied/denied` is proposed for the shared exception hook. Returns None, raises ValueError for invalid metadata or AuditUnavailable (503) on persistence failure. Owns an atomic write/savepoint, not an independent outer commit. See docs/audit.md for caller/transaction/session-failure obligations; D-10 is not approved.

### `backend/core/validation.py`

```python
def validate_shared_input(*, value, rule_name: str):
```

PROPOSED public interface. Owner: Arya / BB-11; endpoint serializers remain feature-owned. Coordinate signature changes.

### `backend/donors/configuration.py`

```python
def approved_screening_rules() -> dict:
```

PROPOSED public interface. Owner: Ankitha / BB-07; policy approval required. Coordinate signature changes.

### `backend/donors/selectors/profile.py`

```python
def donor_profile_for_actor(*, actor, donor_id: UUID):
```

PROPOSED public interface. Owner: Arnav / BB-12. Coordinate signature changes.

### `backend/donors/selectors/results.py`

```python
def latest_eligibility_result(*, actor, donor_id: UUID):
```

PROPOSED public interface. Owner: Yashwitha / BB-08; Arnav access review. Coordinate signature changes.

### `backend/donors/selectors/search.py`

```python
def search_donors(*, actor, blood_group=None, location=None, eligibility_status=None, page=1, page_size=20):
```

PROPOSED public interface. Owner: Yashwitha / BB-09; Ankitha query/API review. Coordinate signature changes.

### `backend/donors/services/screening.py`

```python
def screen_donor(*, actor, donor_id: UUID, answers: dict):
```

PROPOSED public interface. Owner: Ankitha / BB-07. Coordinate signature changes.

### `backend/notification_adapter/client.py`

```python
def send_notification_intent(*, event: dict) -> dict:
```

PROPOSED public interface. Owner: Arya; internal contract only, no Sprint-2 delivery implementation. Coordinate signature changes.
