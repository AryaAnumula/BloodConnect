# Sprint 2 decisions — no invented approvals

Existing Sprint 1 approvals remain in `docs/decisions.md`; its old bootstrap rows are history, not permission to undo later approvals. This new register adds S2-prefixed engineering decision labels, **not SRS requirement IDs**. All ten start PROPOSED. Arya records actual agreement in config/sprint2-decisions.json and this document before incompatible model/endpoint implementation. Approval is not supplied by the assistant.

## S2-01 — Inventory quantity, components and shelf life

PROPOSED: whole-unit demo: BloodUnit.quantity=1; request quantity positive integer whole units; no bag splitting; exact group/component match. Components RBC/PLASMA/PLATELETS. All supported component shelf-life days must be explicitly configured/approved; no clinical defaults.

Driver: Yashwitha + Arnav + Arya. Affects: BB-13/14/16/17/24.

Status: **PROPOSED — approval required**. Record approved wording, approver/date, affected files and PR.

## S2-02 — Expiry and stock states

PROPOSED: collection_date local Asia/Kolkata date, never future; expiry_date=collection_date+approved shelf_life_days. Usable only while local_date < expiry_date; equality is expired. AVAILABLE/ISSUED/DISCARDED/QUARANTINED stored states; EXPIRED derived in read projection. Stock sums only usable AVAILABLE quantities. No independent decrement counter.

Driver: Yashwitha + Arnav. Affects: BB-13/14/15/16.

Status: **PROPOSED — approval required**. Record approved wording, approver/date, affected files and PR.

## S2-03 — Request lifecycle and provisioning

PROPOSED: REQUESTER accounts seeded/provisioned by restricted management command, never public role assignment. Urgency CRITICAL/URGENT/ROUTINE ordered in that order then created_at/id. SUBMITTED→APPROVED/REJECTED; rejection reason required. Partial issue keeps APPROVED with fulfilled_quantity; exact completion→ISSUED; owning requester may close only ISSUED→CLOSED via dedicated action. No reopening or cancellation in this scope.

Driver: Arnav + Ankitha + Arya. Affects: BB-16/17/18/19.

Status: **PROPOSED — approval required**. Record approved wording, approver/date, affected files and PR.

## S2-04 — Operational staff and camp role matrix

PROPOSED: active non-superuser STAFF for inventory/request review/issue; ADMIN only dashboard/reports; no clinical answers included. Camp create/cancel ADMIN only, update ADMIN or STAFF, slots ADMIN or STAFF; booking DONOR only. Clinical endpoints retain the existing explicit health permission. Do not reuse the clinical-staff gate for all operational staff by accident.

Driver: Ankitha + Arya. Affects: BB-13–24.

Status: **PROPOSED — approval required**. Record approved wording, approver/date, affected files and PR.

## S2-05 — Slot and camp capacity/cancellation

PROPOSED: aware start/end times; positive slot capacity; optional camp FK permits walk-ins; camp total capacity also enforced across its slots. Duplicate active donor/slot denied. Lock camp then slot (UUID order when multiple), then booking rows. Camp cancel cancels active appointments and durable cancellation intents atomically; no silent future bookings. Screening must be current ELIGIBLE before booking; no new medical rules.

Driver: Ankitha + Arnav + Arya. Affects: BB-20/21/22.

Status: **PROPOSED — approval required**. Record approved wording, approver/date, affected files and PR.

## S2-06 — Alerts and mocked delivery

PROPOSED: configured near-expiry days and per group/component minimums; equality to minimum is NOT low stock; near expiry requires 0 < expiry_date-local_date <= configured days. No invented thresholds. Create durable intent in same database transaction as domain trigger; manual management-command sweep/dispatcher, no Celery/Redis dependency. Controlled synthetic staff recipients configured outside public APIs. Django owns outbox/retries; Node provides idempotent mock receipt only, not real SMS/email.

Driver: Yashwitha + Arya + Arnav. Affects: BB-15/22.

Status: **PROPOSED — approval required**. Record approved wording, approver/date, affected files and PR.

## S2-07 — Reminder due time and late bookings

PROPOSED: due_at=slot.starts_at−24h; approved scheduler cadence must make normal bookings send no later than due_at. For booking with less than 24h lead: immediate best-effort mock, tagged late_booking; explicitly NOT satisfaction of the ≥24h criterion. At exactly 24h, schedule immediately. Canceled/changed appointments invalidate old pending intent and deduplication prevents stale delivery.

Driver: Arya + Ankitha (scheduling owner). Affects: BB-22.

Status: **PROPOSED — approval required**. Record approved wording, approver/date, affected files and PR.

## S2-08 — Reporting sources and dates

PROPOSED: Asia/Kolkata local from/to dates inclusive, translated to UTC half-open [from 00:00, day_after_to 00:00). Missing/reversed dates invalid. Stock summary current; pending requests=SUBMITTED; upcoming camps=ACTIVE starts_at>=now. Donation source is BloodUnit collection records, distinct donor_id+collection_date events plus separately labelled unit counts (limitation: distinct same-day donations indistinguishable); issue source IssueRecord; wastage explicit InventoryDisposition(DISCARDED) or computed expiry event once per unit, not both. Never call inventory units distinct donor donations without this definition approved.

Driver: Arya + Yashwitha + Arnav. Affects: BB-23/24.

Status: **PROPOSED — approval required**. Record approved wording, approver/date, affected files and PR.

## S2-09 — Performance and availability evidence

PROPOSED for approval: synthetic college demo workload 500 donor profiles/500 units, 5 concurrent clients, 60s steady interval after warm-up; record environment and p95 ≤2s. This is a suggested test protocol, NOT measured evidence or an SRS rewrite. BB-03 observation window/exclusions still need actual approval and measurement.

Driver: Arya + Yashwitha + Arnav. Affects: BB-03/09/14.

Status: **PROPOSED — approval required**. Record approved wording, approver/date, affected files and PR.

## S2-10 — Inventory collection and donor history

PROPOSED: recording a unit requires current ELIGIBLE donor, group derived/checked against profile. Update a confirmed last-donation source once per approved collection event; multiple components from same collection must not double-count or invalidate each other. Agree collection-event identifier/record before implementing this linkage; BB-13 may not invent a second donor-health schema.

Driver: Yashwitha + Ankitha + Arya. Affects: BB-13/21/24.

Status: **PROPOSED — approval required**. Record approved wording, approver/date, affected files and PR.

## Scoped approval record — BB-17 request submission (S2-01 and S2-03, partial)

Date: 15 November 2026. Authority: Codex assistant acting under Arya's explicitly delegated project-decision authority. Evidence: BC-D017–BC-D022 in the central decision log and Arya's reply to Arnav. Applies to BB-17 only; S2-01 and S2-03 as a whole remain **PROPOSED** (see `scoped_approvals` in `config/sprint2-decisions.json`).

Approved clauses:

1. **Components (S2-01):** WHOLE_BLOOD, RBC, PLASMA and PLATELETS. The three-component proposal is superseded. The shared OpenAPI component enum is corrected narrowly, consistent with the inventory vocabulary.
2. **Quantity (S2-01):** strict JSON integers 1–100 inclusive, a college-demo limit, not a clinical limit. Strings, booleans, fractions and out-of-range values are rejected with 400 `validation_error`; values are never clamped. Submission does not require sufficient current stock. Values are recorded in versioned `config/request-policy.json` and aligned in the serializer, form, OpenAPI and database constraint. Missing or invalid runtime policy fails closed with 409 `policy_unresolved`.
3. **Submission rules (S2-03):** REQUESTER accounts are provisioned through a restricted local management command only; there is no public requester registration or role assignment. New requests receive server-set `SUBMITTED`, `fulfilled_quantity: 0` and `rejection_reason: null`. The requester comes exclusively from the authenticated session. Exactly `blood_group`, `component_type`, `quantity` and `urgency_level` are accepted; client-supplied `requester_id`, `status` and other undeclared fields are rejected. The requester relationship is protected against deletion of request history; accounts are deactivated instead.
4. **Superusers (S2-03):** every superuser is denied, even one whose role is REQUESTER. Submission requires an authenticated, active, non-superuser REQUESTER. Clinical permissions do not grant submission access.
5. **Permission helper:** a small private helper in `backend/blood_requests/permissions.py`, used at the API and service boundaries, with existing session/CSRF/error/audit conventions and no duplicate audit recording. No need to wait for the shared helper.
6. **Shared files:** minimal app registration, API include, form route `/requests/new` and test-runner additions ship in the BB-17 PR. Existing routes and checks are preserved. No separate integration PR.
7. **Endpoint:** `POST /api/v1/requests` → 201 `BloodRequest`, no trailing slash. Input-contract amendments are the fourth component and the maximum quantity. API urgency values stay CRITICAL, URGENT, ROUTINE; the older document's "Emergency" corresponds to CRITICAL.

Still unresolved (not approved by this record): shelf-life values, urgency ordering and tie-break for review, review/issue/closure transitions and fulfilment semantics, notification policies, and the remainder of S2-01 and S2-03. No merge approval is implied.

## Scoped approval record — BB-18 staff review (BC-D029)

Date: 15 November 2026. Authority: Codex assistant acting under Arya's explicitly delegated project-decision authority. Evidence: central PROJECT_DECISION_LOG.md BC-D029 and the BB-18 workpack. The exact clauses BC-D029-a … g (queue and ordering, review state machine and reasons, STAFF role gate, atomic decision history and migration, shared list route boundary, interfaces and wiring, scope and provenance) are recorded verbatim in `docs/sprint2/bb18-decisions.md` and under `scoped_approvals` on S2-03 in `config/sprint2-decisions.json`. S2-03 and S2-04 as a whole remain **PROPOSED**; issue, fulfilment, closure (BB-16/19) and notification policies are not approved by this record.
