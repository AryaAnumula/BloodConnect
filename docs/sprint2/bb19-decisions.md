# BB-19 scoped decisions — BC-D035

Date:15November2026. Project decision under Arya's delegated authority; implementation requested by Arya on 2026-11-15. Source: detailed BB19 plan in jackfruit and current project-chat implementation instruction. These clauses authorize this scoped implementation, not unseen-code acceptance, all parent S2 policies or a merge.

## BC-D035-a — Requester tracking

GET /api/v1/requests dispatches STAFF to unchanged staff_queue (default SUBMITTED) and active non-superuser REQUESTER to own_requests (default all own statuses). Owner filtering precedes status/order/count/page. Strict status/page/page_size only; default20, size1..100, page>=1, repeated/blank/unknown400. Urgency CRITICAL,URGENT,ROUTINE then created_at/id ascending; no client requester_id or sort. Shared POST requester submission and review PATCH stay unchanged.

## BC-D035-b — Detail and privacy

GET /api/v1/requests/{request_id} permits active non-superuser REQUESTER for own records or active non-superuser STAFF for minimized operational detail. Foreign-owner and missing valid UUID use the same404 envelope/message; direct selectors repeat role and ownership. All superusers, ADMIN and DONOR denied. Existing BloodRequest/RequestPage DTOs unchanged; own rejection reason shown as text, no clinical/contact/reviewer internals.

## BC-D035-c — Closure

POST /api/v1/requests/{request_id}/close requires owning active non-superuser REQUESTER and session+CSRF; no body (even{} rejected400) or query fields. close_request owns atomic owner-scoped request row lock; only ISSUED with fulfilled_quantity==quantity changes to CLOSED. CLOSED replay200 without a save/updated_at change. Other states or incomplete ISSUED422 invalid_transition; foreign/missing404. Only status/updated_at change; no new model/migration/closed_at, no issue/stock/notification writer. Expected storage failure503 after rollback; existing review messages remain unchanged.

## BC-D035-d — Scope, tests and integration

Arya owns BB19 (BC-D023); Arnav BB16/17/18 only. Implement own_requests/request_detail selectors and close_request service in blood_requests, shared collection per-method gates, detail/close URLs, /requests and /requests/{uuid} pages, feature tests and minimal shared runner/routes/contracts. BB17/18 integration is real; ISSUED/partial/CLOSED test fixtures do not prove actual BB16 integration. Full acceptance waits real BB16/inventory issue-to-track-to-close demo. Manual CI unchanged (BC-D028); ONLY ARYA merges (BC-D033); existing Git identity, no assistant coauthor/access changes.

## Proposed service boundaries now adopted

```python
blood_requests.selectors.tracking.own_requests(*, actor, status=None, page=1, page_size=20) -> dict
blood_requests.selectors.tracking.request_detail(*, actor, request_id) -> dict
blood_requests.services.closure.close_request(*, actor, request_id) -> dict
```

No new schema. Reuse existing DTO, user roles/session/CSRF/audit/error handling. Every boundary guards the actor; request detail and close scope the lookup before record retrieval. Fixture-based issue states are test-only. Complete acceptance requires actual BB16 integration.
