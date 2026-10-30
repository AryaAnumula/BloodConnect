# Sprint 2 endpoint guide — proposed, not mounted

Exact shapes and validations are in openapi.proposed.yaml, conventions.md and decisions-to-approve.md. Required fields are defined in request schema; response enums/required fields in response schema. Every operation lists owner, stories, requirement IDs, roles, auth, status codes and decision gates. No route changes occur on applying the foundation. Existing Sprint 1 API spec remains authoritative for implemented donor/auth routes.

| Method/path | Story | Owner | Roles | Request → success | Gates |
| --- | --- | --- | --- | --- | --- |
| POST `/api/v1/blood-units` | BB-13 | Ch Yashwitha | STAFF | BloodUnitCreate → 201 BloodUnit | S2-01, S2-02, S2-10 |
| GET `/api/v1/blood-units` | BB-13 | Ch Yashwitha | STAFF | none → 200 BloodUnitPage | S2-01, S2-02 |
| GET `/api/v1/blood-units/{unit_id}` | BB-13 | Ch Yashwitha | STAFF | none → 200 BloodUnit | S2-01, S2-02 |
| POST `/api/v1/blood-units/{unit_id}/dispositions` | BB-13 | Ch Yashwitha | STAFF | DispositionCreate → 200 BloodUnit | S2-02, S2-08 |
| GET `/api/v1/stock` | BB-14 | Ch Yashwitha | STAFF, ADMIN | none → 200 StockPage | S2-02 |
| GET `/api/v1/stock/alerts` | BB-15 | Ch Yashwitha | STAFF | none → 200 AlertPage | S2-06 |
| POST `/api/v1/requests` | BB-17 | Arnav Chaudhary | REQUESTER | RequestCreate → 201 BloodRequest | S2-01, S2-03 |
| GET `/api/v1/requests` | BB-18, BB-19 | Arnav Chaudhary | STAFF, REQUESTER | none → 200 RequestPage | S2-03 |
| GET `/api/v1/requests/{request_id}` | BB-19 | Arnav Chaudhary | STAFF, REQUESTER_OWNER | none → 200 BloodRequest | S2-03 |
| PATCH `/api/v1/requests/{request_id}/status` | BB-18 | Arnav Chaudhary | STAFF | ReviewRequest → 200 BloodRequest | S2-03 |
| POST `/api/v1/requests/{request_id}/issues` | BB-16 | Arnav Chaudhary | STAFF | IssueCreate → 201 IssueResponse | S2-01, S2-02, S2-03 |
| POST `/api/v1/requests/{request_id}/close` | BB-19 | Arnav Chaudhary | REQUESTER_OWNER | none → 200 BloodRequest | S2-03 |
| POST `/api/v1/camps` | BB-20 | Ankitha Lakshmmi Mohan | ADMIN | CampCreate → 201 Camp | S2-04, S2-05 |
| GET `/api/v1/camps` | BB-20 | Ankitha Lakshmmi Mohan | DONOR, STAFF, ADMIN | none → 200 CampPage | S2-04, S2-05 |
| PATCH `/api/v1/camps/{camp_id}` | BB-20 | Ankitha Lakshmmi Mohan | ADMIN, STAFF | CampUpdate → 200 Camp | S2-04, S2-05 |
| POST `/api/v1/camps/{camp_id}/cancel` | BB-20 | Ankitha Lakshmmi Mohan | ADMIN | CancelAction → 200 Camp | S2-04, S2-05, S2-06 |
| POST `/api/v1/appointment-slots` | BB-21 | Ankitha Lakshmmi Mohan | ADMIN, STAFF | SlotCreate → 201 Slot | S2-04, S2-05 |
| GET `/api/v1/appointment-slots` | BB-21 | Ankitha Lakshmmi Mohan | DONOR, STAFF, ADMIN | none → 200 SlotPage | S2-05 |
| POST `/api/v1/appointments` | BB-21 | Ankitha Lakshmmi Mohan | DONOR | AppointmentCreate → 201 Appointment | S2-05, S2-07 |
| GET `/api/v1/appointments` | BB-21 | Ankitha Lakshmmi Mohan | DONOR | none → 200 AppointmentPage | S2-05 |
| GET `/api/v1/dashboard` | BB-23 | Anumula Arya | ADMIN | none → 200 Dashboard | S2-04, S2-08 |
| GET `/api/v1/reports` | BB-24 | Anumula Arya | ADMIN | none → 200 ActivityReport | S2-08 |
