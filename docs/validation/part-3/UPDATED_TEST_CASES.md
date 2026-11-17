# BloodConnect updated test case document — Part 3

Source: Team5_SRS_SAD_STP.pdf, Software Test Plan v1.1, appendices A–C; transcription from the supplied 75-page combined PDF. Updated for testing-source commit `d6e377d3ba361730841f51e0fe48720cce0c056f`, 17 November 2026. Original IDs and planned expected results are retained below so the submitted plan remains traceable. Where a heading groups multiple IDs, see the original source for the grouped variants. Page extraction and ID mapping still require a final team review.

## Sprint changes and execution interpretation

- Authentication uses the implemented session/CSRF flow. The original `IT-UC01-07` 401/token expectation must be updated for the implemented anonymous `/api/v1/auth/me` and protected session endpoints: 403 with `authentication_required`; unauthorized data must remain inaccessible. Wrong credentials retain their separately defined login behavior. Check each endpoint contract rather than globally replacing every 401.
- Requesters submit with session-owned identity; staff review and issue; requester tracking and fully issued closure now exist in testing. Use actual persisted requests and units for system validation, including partial/full issue, rollback, privacy and idempotent close.
- Inventory has real collection-event/unit models, disposition and alert implementations. Verify actual public app routes separately: on this testing snapshot `/api/v1/blood-units` and `/staff/inventory` are not mounted. A unit test using an isolated URL configuration does not prove public routing.
- Camp cancellation, BB21 donor-history tranche/booking UI and BB23 dashboard have open PRs. Mark their unmerged system scenarios BLOCKED on this testing snapshot; do not claim that earlier isolated-lane tests prove this branch.
- BB24 reports have an explicitly labelled synthetic mode and a separate domain mode. Never conflate a fixture snapshot with live data or missing providers with a real zero count.
- Demo performance protocol in current shared rules is 500 synthetic donors/500 units, five authenticated clients and 60 seconds after warmup; the original NFR-TC-01 proposal (50 clients, five minutes, larger dataset) is a separate, unapproved proposal. Do not claim production load or availability from a shorter run. Availability requires its own measured window.
- Results below are **not yet mapped individually** to the execution run; `NOT ASSESSED` is not failure or pass. See the reports for measured automated-suite outcomes and blocked system checks. Only mark a case PASS after tracing its complete preconditions, steps and expected result to exact evidence on the tested source. Browser/UI, cross-app and non-functional cases cannot be inferred from unit coverage.

## Original STP cases with current status

### IT-UC01-01 — Register a donor

- **Original case ID / module:** IT-UC01-01 / Authentication
- **Requirement(s):** FR-001
- **Precondition:** New donor data and provisioned staff/requester/admin accounts; isolated test DB
- **Steps:** POST registration; read persisted user/profile
- **Test Data:** Unique email/mobile, valid password and required profile
- **Expected Result:** 201; donor account/profile created and salted hash stored
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC01-02 — Reject duplicate email

- **Original case ID / module:** IT-UC01-02/03 / Authentication
- **Requirement(s):** FR-001
- **Precondition:** New donor data and provisioned staff/requester/admin accounts; isolated test DB
- **Steps:** Register separately with an existing email and an existing normalized mobile.
- **Test Data:** Existing email; existing mobile
- **Expected Result:** Each call returns 409 and creates no duplicate account.
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC01-04 — Reject missing registration fields

- **Original case ID / module:** IT-UC01-04 / Authentication
- **Requirement(s):** FR-001, SEC-003
- **Precondition:** New donor data and provisioned staff/requester/admin accounts; isolated test DB
- **Steps:** Omit email, mobile and password in separate API calls
- **Test Data:** One required field missing in each call
- **Expected Result:** 400 with field errors; no partial donor record
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC01-05 — Authenticate each role

- **Original case ID / module:** IT-UC01-05 / Authentication
- **Requirement(s):** FR-002
- **Precondition:** New donor data and provisioned staff/requester/admin accounts; isolated test DB
- **Steps:** Login separately with all four role fixtures; inspect role-filtered session
- **Test Data:** Correct donor/staff/requester/admin credentials
- **Expected Result:** Each valid login succeeds; returned role matches stored role
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC01-06 — Reject wrong password

- **Original case ID / module:** IT-UC01-06 / Authentication
- **Requirement(s):** FR-002, SEC-001
- **Precondition:** New donor data and provisioned staff/requester/admin accounts; isolated test DB
- **Steps:** Send incorrect password to login; inspect response
- **Test Data:** Known email and wrong password
- **Expected Result:** 401; no valid session/token returned
- **Current case status:** PARTIAL automated evidence: `test_wrong_password_and_unknown_email_give_same_401_and_failure_events` passed on PostgreSQL 16.16. Confirm the complete STP steps and any UI requirements before marking the case PASS.

### IT-UC01-07 — Reject protected call without valid session

- **Original case ID / module:** IT-UC01-07 / Authentication
- **Requirement(s):** FR-002, SEC-004
- **Precondition:** New donor data and provisioned staff/requester/admin accounts; isolated test DB
- **Steps:** Call own-profile API without token, then invalid/expired token
- **Test Data:** Missing, invalid and expired token variants
- **Expected Result:** 401; protected data not exposed
- **Sprint update:** Exercise missing/invalid session; expect the implemented 403 `authentication_required` response rather than the legacy token/401 assumption.
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### ST-UC01-08 — Registration and login end to end

- **Original case ID / module:** ST-UC01-08 / Authentication
- **Requirement(s):** FR-001, FR-002, NFR-003
- **Precondition:** New donor data and provisioned staff/requester/admin accounts; isolated test DB
- **Steps:** Use responsive donor UI to register, confirm and log in
- **Test Data:** New donor fixture
- **Expected Result:** Successful registration/login within at most five primary registration screens
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### UT-UC02-01 — Accept eligibility lower boundaries

- **Original case ID / module:** UT-UC02-01/02 / Donor Eligibility
- **Requirement(s):** FR-003
- **Precondition:** Donor exists; test rule fixture age 18-65 inclusive, weight >=50 kg, interval >=90 days; other inputs valid
- **Steps:** Test exact lower limits and exact upper age boundary.
- **Test Data:** Configured boundary values
- **Expected Result:** Each boundary value is evaluated as eligible.
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC02-03 — Reject age outside configured range

- **Original case ID / module:** IT-UC02-03 / Donor Eligibility
- **Requirement(s):** FR-003
- **Precondition:** Donor exists; test rule fixture age 18-65 inclusive, weight >=50 kg, interval >=90 days; other inputs valid
- **Steps:** Screen once below and once above limits
- **Test Data:** Ages 17 and 66; other inputs valid
- **Expected Result:** Ineligible with age reason
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC02-04 — Reject weight below configured limit

- **Original case ID / module:** IT-UC02-04 / Donor Eligibility
- **Requirement(s):** FR-003
- **Precondition:** Donor exists; test rule fixture age 18-65 inclusive, weight >=50 kg, interval >=90 days; other inputs valid
- **Steps:** Screen just below 50 kg
- **Test Data:** 49.9 kg; otherwise eligible
- **Expected Result:** Ineligible with weight reason
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC02-05 — Reject short donation interval

- **Original case ID / module:** IT-UC02-05 / Donor Eligibility
- **Requirement(s):** FR-003
- **Precondition:** Donor exists; test rule fixture age 18-65 inclusive, weight >=50 kg, interval >=90 days; other inputs valid
- **Steps:** Screen before minimum interval
- **Test Data:** 89 days since last donation
- **Expected Result:** Ineligible with interval reason
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC02-06 — Reject invalid screening input

- **Original case ID / module:** IT-UC02-06 / Donor Eligibility
- **Requirement(s):** FR-003, SEC-003
- **Precondition:** Donor exists; test rule fixture age 18-65 inclusive, weight >=50 kg, interval >=90 days; other inputs valid
- **Steps:** Send missing weight, invalid date and negative value variants
- **Test Data:** Missing/negative weight; malformed or future last-donation date
- **Expected Result:** Validation error; no eligible status based on invalid input
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC02-07 — Persist result and show reason

- **Original case ID / module:** IT-UC02-07 / Donor Eligibility
- **Requirement(s):** FR-004
- **Precondition:** Donor exists; test rule fixture age 18-65 inclusive, weight >=50 kg, interval >=90 days; other inputs valid
- **Steps:** Screen failing donor via API; read result as donor
- **Test Data:** Age 17 or weight 49.9
- **Expected Result:** Result saved; response/UI gives ineligible reason
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### ST-UC02-08 — Change rule and rescreen end to end

- **Original case ID / module:** ST-UC02-08 / Donor Eligibility
- **Requirement(s):** FR-003, FR-004
- **Precondition:** Donor exists; test rule fixture age 18-65 inclusive, weight >=50 kg, interval >=90 days; other inputs valid
- **Steps:** Admin changes test threshold; donor rescreens; inspect new status
- **Test Data:** Test weight threshold changed from 50 to 55; donor weight 52
- **Expected Result:** New configuration used; no hard-coded old rule; visible updated reason
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### UT-UC03-01 — Filter by blood group

- **Original case ID / module:** UT-UC03-01/02 / Donor Search
- **Requirement(s):** FR-005
- **Precondition:** Staff logged in; donors seeded across groups, locations and eligibility states
- **Steps:** Run separate blood-group and location filters.
- **Test Data:** Valid group; valid location
- **Expected Result:** Each result contains only matching donors.
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC03-03 — Filter by eligibility

- **Original case ID / module:** IT-UC03-03 / Donor Search
- **Requirement(s):** FR-005
- **Precondition:** Staff logged in; donors seeded across groups, locations and eligibility states
- **Steps:** Search eligible and ineligible separately
- **Test Data:** Mixed eligibility records
- **Expected Result:** Results follow requested eligibility filter
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC03-04 — Combine all filters

- **Original case ID / module:** IT-UC03-04 / Donor Search
- **Requirement(s):** FR-005
- **Precondition:** Staff logged in; donors seeded across groups, locations and eligibility states
- **Steps:** Search group/location/eligibility together
- **Test Data:** O+, Bangalore, eligible
- **Expected Result:** Only donors satisfying all filters returned
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC03-05 — Handle zero matches

- **Original case ID / module:** IT-UC03-05 / Donor Search
- **Requirement(s):** FR-005
- **Precondition:** Staff logged in; donors seeded across groups, locations and eligibility states
- **Steps:** Search valid but absent combination
- **Test Data:** Group/location combination absent in fixture
- **Expected Result:** 200 with empty list; no unrelated donor data
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC03-06 — Reject invalid group filter

- **Original case ID / module:** IT-UC03-06 / Donor Search
- **Requirement(s):** FR-005, SEC-003
- **Precondition:** Staff logged in; donors seeded across groups, locations and eligibility states
- **Steps:** Call search with unsupported blood group
- **Test Data:** blood_group=ZZ
- **Expected Result:** 400 validation error rather than unsafe query
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC03-07 — Deny non-staff search

- **Original case ID / module:** IT-UC03-07 / Donor Search
- **Requirement(s):** FR-005, SEC-002
- **Precondition:** Staff logged in; donors seeded across groups, locations and eligibility states
- **Steps:** Call staff search with donor and requester tokens
- **Test Data:** Donor/requester token
- **Expected Result:** 403; no staff donor list
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### ST-UC03-08 — Search through staff UI

- **Original case ID / module:** ST-UC03-08 / Donor Search
- **Requirement(s):** FR-005
- **Precondition:** Staff logged in; donors seeded across groups, locations and eligibility states
- **Steps:** Login as staff; apply and clear filters; compare fixture
- **Test Data:** Seeded searchable donors
- **Expected Result:** Displayed results match filters; clearing filters restores permitted list
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC04-01 — Book a camp slot

- **Original case ID / module:** IT-UC04-01 / Appointments
- **Requirement(s):** FR-018
- **Precondition:** Eligible donor, ineligible donor, camp slot and walk-in slot fixtures exist; capacity configured
- **Steps:** Book available camp slot through API
- **Test Data:** Eligible donor; camp-linked slot with space
- **Expected Result:** 201; appointment links donor and slot
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC04-02 — Book a walk-in slot

- **Original case ID / module:** IT-UC04-02 / Appointments
- **Requirement(s):** FR-018
- **Precondition:** Eligible donor, ineligible donor, camp slot and walk-in slot fixtures exist; capacity configured
- **Steps:** Book available slot without camp link
- **Test Data:** Eligible donor; walk-in slot
- **Expected Result:** 201; appointment created without a camp requirement
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC04-03 — Allow final available capacity

- **Original case ID / module:** IT-UC04-03/04 / Appointments
- **Requirement(s):** FR-019
- **Precondition:** Eligible donor, ineligible donor, camp slot and walk-in slot fixtures exist; capacity configured
- **Steps:** Book the final available place, then attempt one more booking.
- **Test Data:** Slot with one place remaining
- **Expected Result:** Final place succeeds; next request returns conflict.
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC04-05 — Protect last slot under concurrency

- **Original case ID / module:** IT-UC04-05 / Appointments
- **Requirement(s):** FR-019
- **Precondition:** Eligible donor, ineligible donor, camp slot and walk-in slot fixtures exist; capacity configured
- **Steps:** Release two booking calls together using separate DB sessions
- **Test Data:** Two donors; one remaining slot
- **Expected Result:** One success; one conflict; count <= capacity
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC04-06 — Block ineligible donor booking

- **Original case ID / module:** IT-UC04-06 / Appointments
- **Requirement(s):** SRS 6.2
- **Precondition:** Eligible donor, ineligible donor, camp slot and walk-in slot fixtures exist; capacity configured
- **Steps:** Attempt camp and walk-in booking as ineligible donor
- **Test Data:** Persisted ineligible status
- **Expected Result:** 422; no donation-linked appointment
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC04-07 — Reject invalid slot identifier

- **Original case ID / module:** IT-UC04-07 / Appointments
- **Requirement(s):** FR-018, SEC-003
- **Precondition:** Eligible donor, ineligible donor, camp slot and walk-in slot fixtures exist; capacity configured
- **Steps:** Book unknown and malformed slot IDs
- **Test Data:** Missing/malformed/nonexistent slot ID
- **Expected Result:** 400/404; no orphan appointment
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### ST-UC04-08 — Book and view confirmation end to end

- **Original case ID / module:** ST-UC04-08 / Appointments
- **Requirement(s):** FR-018, FR-019
- **Precondition:** Eligible donor, ineligible donor, camp slot and walk-in slot fixtures exist; capacity configured
- **Steps:** Donor chooses available slot in UI and books
- **Test Data:** Eligible donor; available camp slot
- **Expected Result:** Confirmation shows appointment ID/time; persisted capacity matches UI
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### UT-UC05-01 — Record valid inventory unit

- **Original case ID / module:** UT-UC05-01 / Inventory
- **Requirement(s):** FR-006
- **Precondition:** Staff and screened eligible/ineligible donors exist; four component shelf-life fixtures configured
- **Steps:** POST unit intake then inspect persisted fields
- **Test Data:** Eligible donor; O+; RBC; valid collection date; quantity=1
- **Expected Result:** 201; recorded group/component/date/quantity match input
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### UT-UC05-02 — Compute all component expiries

- **Original case ID / module:** UT-UC05-02 / Inventory
- **Requirement(s):** FR-007
- **Precondition:** Staff and screened eligible/ineligible donors exist; four component shelf-life fixtures configured
- **Steps:** Call expiry service for each component; compare configured L
- **Test Data:** Whole Blood, Plasma, Platelets, RBC; fixture shelf lives L1-L4
- **Expected Result:** Each expiry equals collection date plus its configured shelf life
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC05-03 — Reject invalid intake fields

- **Original case ID / module:** IT-UC05-03 / Inventory
- **Requirement(s):** FR-006, SEC-003
- **Precondition:** Staff and screened eligible/ineligible donors exist; four component shelf-life fixtures configured
- **Steps:** POST missing component, negative/zero quantity and malformed date variants
- **Test Data:** Invalid required fields or quantity <=0
- **Expected Result:** 400; inventory unchanged
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC05-04 — Reject ineligible donor intake

- **Original case ID / module:** IT-UC05-04 / Inventory
- **Requirement(s):** SRS 6.5
- **Precondition:** Staff and screened eligible/ineligible donors exist; four component shelf-life fixtures configured
- **Steps:** Record unit for ineligible donor
- **Test Data:** Donor eligibility false
- **Expected Result:** 422; no inventory unit created
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC05-05 — Update stock after intake

- **Original case ID / module:** IT-UC05-05 / Inventory
- **Requirement(s):** FR-008
- **Precondition:** Staff and screened eligible/ineligible donors exist; four component shelf-life fixtures configured
- **Steps:** Read stock; add quantity q; reread group/component
- **Test Data:** Matching bucket; q positive
- **Expected Result:** Available stock increases by q after commit
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC05-06 — Exclude unavailable units from stock

- **Original case ID / module:** IT-UC05-06 / Inventory
- **Requirement(s):** FR-008, FR-011
- **Precondition:** Staff and screened eligible/ineligible donors exist; four component shelf-life fixtures configured
- **Steps:** Read stock with mixed status/expiry fixtures
- **Test Data:** Available, issued, expired, discarded and quarantined units
- **Expected Result:** Only available unexpired usable quantities counted
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC05-07 — Use updated shelf-life configuration

- **Original case ID / module:** IT-UC05-07 / Inventory
- **Requirement(s):** FR-007
- **Precondition:** Staff and screened eligible/ineligible donors exist; four component shelf-life fixtures configured
- **Steps:** Change fixture rule; record another unit; compare expiry
- **Test Data:** New component shelf-life L; fresh intake
- **Expected Result:** New unit uses current rule; no fixed 42-day assumption
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### ST-UC05-08 — Intake workflow end to end

- **Original case ID / module:** ST-UC05-08 / Inventory
- **Requirement(s):** FR-006, FR-007, FR-008
- **Precondition:** Staff and screened eligible/ineligible donors exist; four component shelf-life fixtures configured
- **Steps:** Staff records unit via UI then views stock and unit detail
- **Test Data:** Eligible donor and valid unit details
- **Expected Result:** Computed expiry and committed stock are shown consistently
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### UT-UC06-01 — Flag unit at near-expiry boundary

- **Original case ID / module:** UT-UC06-01/02 / Expiry and Stock Alerts
- **Requirement(s):** FR-009
- **Precondition:** Staff recipient and mock in-app/email/SMS channels exist; alert thresholds configured
- **Steps:** Evaluate units exactly at and just outside the alert window.
- **Test Data:** Boundary and boundary+1 dates
- **Expected Result:** Only the unit inside the configured window is flagged.
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC06-03 — Alert below low-stock minimum

- **Original case ID / module:** IT-UC06-03/04 / Expiry and Stock Alerts
- **Requirement(s):** FR-010
- **Precondition:** Staff recipient and mock in-app/email/SMS channels exist; alert thresholds configured
- **Steps:** Evaluate stock below and exactly at the configured minimum.
- **Test Data:** Minimum-1 and minimum values
- **Expected Result:** Alert appears only below the minimum.
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC06-05 — Exclude expired unit and update availability

- **Original case ID / module:** IT-UC06-05 / Expiry and Stock Alerts
- **Requirement(s):** FR-011, SRS 6.5
- **Precondition:** Staff recipient and mock in-app/email/SMS channels exist; alert thresholds configured
- **Steps:** Advance test clock beyond expiry; run check and issue picker query
- **Test Data:** Unit expired before current test time
- **Expected Result:** Unit not selectable; expired/discarded lifecycle applied per policy
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC06-06 — Deliver critical alert over two channels

- **Original case ID / module:** IT-UC06-06 / Expiry and Stock Alerts
- **Requirement(s):** FR-009, FR-010, SRS 6.2
- **Precondition:** Staff recipient and mock in-app/email/SMS channels exist; alert thresholds configured
- **Steps:** Trigger one stock and one expiry alert; inspect delivery records
- **Test Data:** In-app plus email or SMS mock
- **Expected Result:** Both required channels attempted/recorded; correct staff recipient
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC06-07 — Recover from gateway failure

- **Original case ID / module:** IT-UC06-07 / Expiry and Stock Alerts
- **Requirement(s):** FR-009, FR-010
- **Precondition:** Staff recipient and mock in-app/email/SMS channels exist; alert thresholds configured
- **Steps:** Fail external mock; trigger alert; restore mock and retry
- **Test Data:** Gateway timeout/failure
- **Expected Result:** In-app alert remains; failed channel persisted and retried without silent loss
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### ST-UC06-08 — Display alerts end to end

- **Original case ID / module:** ST-UC06-08 / Expiry and Stock Alerts
- **Requirement(s):** FR-009, FR-010
- **Precondition:** Staff recipient and mock in-app/email/SMS channels exist; alert thresholds configured
- **Steps:** Staff opens alerts after scheduled checks
- **Test Data:** Near-expiry and low-stock fixtures
- **Expected Result:** UI identifies affected unit/bucket and current condition
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC07-01 — Submit valid request

- **Original case ID / module:** IT-UC07-01 / Request Submission
- **Requirement(s):** FR-012
- **Precondition:** Requester, staff and inventory fixtures exist; requester has valid session
- **Steps:** POST request; inspect persisted record
- **Test Data:** O+, RBC, quantity=2, Urgent
- **Expected Result:** 201; unique request ID and SUBMITTED status
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC07-02 — Reject missing mandatory fields

- **Original case ID / module:** IT-UC07-02/03 / Request Submission
- **Requirement(s):** FR-012, SEC-003
- **Precondition:** Requester, staff and inventory fixtures exist; requester has valid session
- **Steps:** Omit mandatory fields and submit zero/negative quantity variants.
- **Test Data:** Missing fields; zero/negative quantity
- **Expected Result:** Each request returns 400 with no partial record.
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC07-04 — Validate urgency values

- **Original case ID / module:** IT-UC07-04 / Request Submission
- **Requirement(s):** FR-012
- **Precondition:** Requester, staff and inventory fixtures exist; requester has valid session
- **Steps:** Submit Routine, Urgent, Emergency then unsupported urgency
- **Test Data:** Allowed values and Unknown
- **Expected Result:** Allowed values accepted; unsupported value rejected
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC07-05 — Route request to staff review

- **Original case ID / module:** IT-UC07-05 / Request Submission
- **Requirement(s):** FR-013
- **Precondition:** Requester, staff and inventory fixtures exist; requester has valid session
- **Steps:** Submit requester request; inspect staff queue and notification intent
- **Test Data:** New valid request
- **Expected Result:** Pending request visible to staff; notification intent recorded
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC07-06 — Order pending requests by urgency

- **Original case ID / module:** IT-UC07-06 / Request Submission
- **Requirement(s):** FR-013
- **Precondition:** Requester, staff and inventory fixtures exist; requester has valid session
- **Steps:** Seed mixed pending requests; fetch staff queue
- **Test Data:** Routine, Emergency, Urgent
- **Expected Result:** Emergency precedes Urgent precedes Routine; tie order documented
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC07-07 — Restrict requester to own requests

- **Original case ID / module:** IT-UC07-07 / Request Submission
- **Requirement(s):** FR-012, SEC-005
- **Precondition:** Requester, staff and inventory fixtures exist; requester has valid session
- **Steps:** Requester A attempts to read Requester B request
- **Test Data:** Different requester IDs
- **Expected Result:** Forbidden/not-found response; no unrelated requester record exposed
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### ST-UC07-08 — Submit and track request end to end

- **Original case ID / module:** ST-UC07-08 / Request Submission
- **Requirement(s):** FR-012, FR-013, FR-017
- **Precondition:** Requester, staff and inventory fixtures exist; requester has valid session
- **Steps:** Requester uses UI; staff opens queue; requester checks status
- **Test Data:** Valid blood request
- **Expected Result:** Same request ID shown; SUBMITTED visible and review queue ordered correctly
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC08-01 — Approve submitted request

- **Original case ID / module:** IT-UC08-01 / Request Review
- **Requirement(s):** FR-014
- **Precondition:** Staff, requester and SUBMITTED request fixtures exist
- **Steps:** Staff PATCH status to APPROVED; inspect DB
- **Test Data:** Submitted request and staff token
- **Expected Result:** 200; status APPROVED
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC08-02 — Reject request with reason

- **Original case ID / module:** IT-UC08-02/03 / Request Review
- **Requirement(s):** FR-014
- **Precondition:** Staff, requester and SUBMITTED request fixtures exist
- **Steps:** Reject once with a reason and once without one.
- **Test Data:** Valid reason; blank reason
- **Expected Result:** Reasoned rejection succeeds; blank reason returns 400.
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC08-04 — Deny requester approval

- **Original case ID / module:** IT-UC08-04 / Request Review
- **Requirement(s):** FR-014, SEC-002
- **Precondition:** Staff, requester and SUBMITTED request fixtures exist
- **Steps:** Requester sends approval PATCH
- **Test Data:** Requester token
- **Expected Result:** 403; no approval
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC08-05 — Reject unknown status value

- **Original case ID / module:** IT-UC08-05 / Request Review
- **Requirement(s):** FR-014
- **Precondition:** Staff, requester and SUBMITTED request fixtures exist
- **Steps:** Staff sends unsupported state
- **Test Data:** status=UNKNOWN
- **Expected Result:** 400; no transition
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC08-06 — Reject disallowed backward transition

- **Original case ID / module:** IT-UC08-06 / Request Review
- **Requirement(s):** FR-014, FR-017
- **Precondition:** Staff, requester and SUBMITTED request fixtures exist
- **Steps:** Attempt to approve an already issued/closed request
- **Test Data:** ISSUED or CLOSED request
- **Expected Result:** 422; historical state not overwritten
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC08-07 — Keep concurrent review consistent

- **Original case ID / module:** IT-UC08-07 / Request Review
- **Requirement(s):** FR-014
- **Precondition:** Staff, requester and SUBMITTED request fixtures exist
- **Steps:** Send approve/reject concurrently with separate transactions
- **Test Data:** Same SUBMITTED request
- **Expected Result:** One valid final review state; losing conflicting write rejected; no inconsistent history
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### ST-UC08-08 — Review and display outcome end to end

- **Original case ID / module:** ST-UC08-08 / Request Review
- **Requirement(s):** FR-014, FR-017
- **Precondition:** Staff, requester and SUBMITTED request fixtures exist
- **Steps:** Staff reviews via UI; requester reloads status
- **Test Data:** Submitted request; approval/rejection variant
- **Expected Result:** Correct final state and rejection reason, where applicable, displayed
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC09-01 — Issue matching unit successfully

- **Original case ID / module:** IT-UC09-01 / Blood Issue
- **Requirement(s):** FR-015, FR-016
- **Precondition:** Staff, two approved requests and suitable unit fixtures exist; real chosen test DB supports locks
- **Steps:** POST issue for approved request; inspect unit/issue/stock
- **Test Data:** Matching group/component; unexpired AVAILABLE unit
- **Expected Result:** 201; one issue record; unit ISSUED; stock decreases by issued quantity
- **Current case status:** PARTIAL automated evidence: `test_partial_then_full_issue_through_the_api_reduces_stock_exactly_once` passed on PostgreSQL 16.16. Confirm the complete STP steps and any UI requirements before marking the case PASS.

### IT-UC09-02 — Block non-approved request issue

- **Original case ID / module:** IT-UC09-02 / Blood Issue
- **Requirement(s):** FR-015
- **Precondition:** Staff, two approved requests and suitable unit fixtures exist; real chosen test DB supports locks
- **Steps:** Attempt issue for SUBMITTED and REJECTED requests
- **Test Data:** Suitable unit; unapproved requests
- **Expected Result:** 422; no issue record or stock change
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC09-03 — Block expired/discarded/quarantined unit

- **Original case ID / module:** IT-UC09-03 / Blood Issue
- **Requirement(s):** FR-011, FR-015
- **Precondition:** Staff, two approved requests and suitable unit fixtures exist; real chosen test DB supports locks
- **Steps:** Attempt issue with each unsafe unit fixture
- **Test Data:** Expired, DISCARDED, quarantined variants
- **Expected Result:** 422; no unsafe allocation
- **Current case status:** PARTIAL automated evidence: `test_unsafe_units_are_rejected_without_mutation` passed on PostgreSQL 16.16. Confirm the complete STP steps and any UI requirements before marking the case PASS.

### IT-UC09-04 — Block group or component mismatch

- **Original case ID / module:** IT-UC09-04 / Blood Issue
- **Requirement(s):** FR-015
- **Precondition:** Staff, two approved requests and suitable unit fixtures exist; real chosen test DB supports locks
- **Steps:** Attempt issue with nonmatching group then component
- **Test Data:** Approved O+ RBC request; A+ RBC / O+ Plasma unit
- **Expected Result:** 422; no issue or stock change
- **Current case status:** PARTIAL automated evidence: `test_unsafe_units_are_rejected_without_mutation` passed on PostgreSQL 16.16. Confirm the complete STP steps and any UI requirements before marking the case PASS.

### IT-UC09-05 — Prevent same unit for two requests concurrently

- **Original case ID / module:** IT-UC09-05 / Blood Issue
- **Requirement(s):** NFR-004
- **Precondition:** Staff, two approved requests and suitable unit fixtures exist; real chosen test DB supports locks
- **Steps:** Submit concurrent issue calls against different approved requests
- **Test Data:** Same unit_id; two request IDs
- **Expected Result:** Exactly one successful allocation; conflicting call rejected; one unit issue record
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC09-06 — Rollback failed multi-step issue

- **Original case ID / module:** IT-UC09-06 / Blood Issue
- **Requirement(s):** FR-016
- **Precondition:** Staff, two approved requests and suitable unit fixtures exist; real chosen test DB supports locks
- **Steps:** Inject DB failure after issue insert but before unit/request update
- **Test Data:** Valid request/unit; test fault injection
- **Expected Result:** Entire transaction rolls back; stock, unit and issue state unchanged
- **Current case status:** PARTIAL automated evidence: `test_failure_after_allocation_rolls_back_units_records_and_request` passed on PostgreSQL 16.16. Confirm the complete STP steps and any UI requirements before marking the case PASS.

### IT-UC09-07 — Fulfill multi-unit request without request uniqueness bug

- **Original case ID / module:** IT-UC09-07 / Blood Issue
- **Requirement(s):** FR-015, FR-016
- **Precondition:** Staff, two approved requests and suitable unit fixtures exist; real chosen test DB supports locks
- **Steps:** Issue two distinct valid units against quantity-two request
- **Test Data:** Two unit IDs; one approved request
- **Expected Result:** Distinct unit issue records permitted; request_id not constrained to one unit; stock reduced correctly
- **Current case status:** PARTIAL automated evidence: `test_one_batch_can_complete_the_request` passed on PostgreSQL 16.16. Confirm the complete STP steps and any UI requirements before marking the case PASS.

### ST-UC09-08 — Issue and track status end to end

- **Original case ID / module:** ST-UC09-08 / Blood Issue
- **Requirement(s):** FR-015, FR-016, FR-017
- **Precondition:** Staff, two approved requests and suitable unit fixtures exist; real chosen test DB supports locks
- **Steps:** Staff approves then issues full request via UI; requester tracks
- **Test Data:** Matching units for full requested quantity
- **Expected Result:** ISSUED displayed after commit; issue trace and stock agree
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC10-01 — Create camp with valid details

- **Original case ID / module:** IT-UC10-01 / Donation Camps
- **Requirement(s):** FR-021
- **Precondition:** Admin and staff fixtures exist; provisional policy admin create/cancel, staff update pending SRS resolution
- **Steps:** Admin POST date/location/capacity
- **Test Data:** Future camp date; valid location; positive capacity
- **Expected Result:** 201; camp published
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC10-02 — Update camp details

- **Original case ID / module:** IT-UC10-02 / Donation Camps
- **Requirement(s):** FR-021
- **Precondition:** Admin and staff fixtures exist; provisional policy admin create/cancel, staff update pending SRS resolution
- **Steps:** Authorized user PATCH permitted camp fields
- **Test Data:** Changed location/date before bookings
- **Expected Result:** 200; valid edits stored
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC10-03 — Cancel camp as administrator

- **Original case ID / module:** IT-UC10-03 / Donation Camps
- **Requirement(s):** FR-021
- **Precondition:** Admin and staff fixtures exist; provisional policy admin create/cancel, staff update pending SRS resolution
- **Steps:** Admin cancels camp then fetches available slots
- **Test Data:** Existing camp
- **Expected Result:** Camp cancelled and no longer bookable; existing-booking handling needs approved policy
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC10-04 — Reject invalid capacity

- **Original case ID / module:** IT-UC10-04/05 / Donation Camps
- **Requirement(s):** FR-021, SEC-003
- **Precondition:** Admin and staff fixtures exist; provisional policy admin create/cancel, staff update pending SRS resolution
- **Steps:** Submit non-positive capacity and missing date/location variants.
- **Test Data:** Invalid capacity; missing fields
- **Expected Result:** Each invalid request returns 400 and creates no camp.
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC10-06 — Deny donor/requester camp management

- **Original case ID / module:** IT-UC10-06 / Donation Camps
- **Requirement(s):** FR-021, SEC-002
- **Precondition:** Admin and staff fixtures exist; provisional policy admin create/cancel, staff update pending SRS resolution
- **Steps:** Call create/update/cancel with donor and requester tokens
- **Test Data:** Nonstaff/nonadmin token
- **Expected Result:** 403; camp unchanged
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC10-07 — Check camp role conflict against approved baseline

- **Original case ID / module:** IT-UC10-07 / Donation Camps
- **Requirement(s):** FR-021, SRS 6.5
- **Precondition:** Admin and staff fixtures exist; provisional policy admin create/cancel, staff update pending SRS resolution
- **Steps:** Review permission matrix; execute staff create/cancel once conflict is resolved
- **Test Data:** Final approved FR-021/6.5 permission matrix
- **Expected Result:** Keep this test blocked until the camp permissions are agreed. Record the approved policy before execution.
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### ST-UC10-08 — Manage camp end to end

- **Original case ID / module:** ST-UC10-08 / Donation Camps
- **Requirement(s):** FR-021
- **Precondition:** Admin and staff fixtures exist; provisional policy admin create/cancel, staff update pending SRS resolution
- **Steps:** Admin creates; permitted user edits; admin cancels in UI
- **Test Data:** Valid camp fixture
- **Expected Result:** Changes appear in camp list; cancellation removes availability without deleting history
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### UT-UC11-01 — Send reminder at least 24 hours ahead

- **Original case ID / module:** UT-UC11-01/02 / Notifications
- **Requirement(s):** FR-020
- **Precondition:** Donor/staff/requester fixtures; mock gateway; deterministic clock; persistent delivery records
- **Steps:** Evaluate a reminder due at least 24 hours ahead and one not yet due.
- **Test Data:** Due and not-due appointments
- **Expected Result:** Only the due reminder is queued.
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC11-03 — Prevent repeated job duplicate reminder

- **Original case ID / module:** IT-UC11-03 / Notifications
- **Requirement(s):** FR-020
- **Precondition:** Donor/staff/requester fixtures; mock gateway; deterministic clock; persistent delivery records
- **Steps:** Run same due reminder job twice
- **Test Data:** Same appointment/event
- **Expected Result:** One event/channel send result; no duplicate reminder
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC11-04 — Send critical alerts in-app and external channel

- **Original case ID / module:** IT-UC11-04 / Notifications
- **Requirement(s):** FR-009, FR-010, SRS 6.2
- **Precondition:** Donor/staff/requester fixtures; mock gateway; deterministic clock; persistent delivery records
- **Steps:** Dispatch stock/expiry events; inspect both channels
- **Test Data:** Staff recipient; in-app and email/SMS
- **Expected Result:** Required channel records present; correct alert content
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC11-05 — Notify appropriate requester/staff on workflow event

- **Original case ID / module:** IT-UC11-05 / Notifications
- **Requirement(s):** FR-013, FR-017
- **Precondition:** Donor/staff/requester fixtures; mock gateway; deterministic clock; persistent delivery records
- **Steps:** Submit/review request; inspect event recipients
- **Test Data:** Requester A request and staff review
- **Expected Result:** Staff notified on submission; requester receives relevant status without another user’s data
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC11-06 — Retry failed reminder delivery

- **Original case ID / module:** IT-UC11-06 / Notifications
- **Requirement(s):** FR-020
- **Precondition:** Donor/staff/requester fixtures; mock gateway; deterministic clock; persistent delivery records
- **Steps:** Fail gateway for due reminder; restore and retry before deadline
- **Test Data:** Mock failure then success
- **Expected Result:** Failure tracked; retry delivers within timing requirement; no duplicate on success
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC11-07 — Identify late-booking policy gap

- **Original case ID / module:** IT-UC11-07 / Notifications
- **Requirement(s):** FR-020
- **Precondition:** Donor/staff/requester fixtures; mock gateway; deterministic clock; persistent delivery records
- **Steps:** Attempt appointment booking less than 24h ahead; compare agreed policy
- **Test Data:** Appointment only 12h ahead
- **Expected Result:** Keep this test blocked until the booking policy is approved. An immediate reminder for a booking 12 hours away does not meet the 24-hour requirement.
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### ST-UC11-08 — Receive only own notifications end to end

- **Original case ID / module:** ST-UC11-08 / Notifications
- **Requirement(s):** FR-020, SEC-005
- **Precondition:** Donor/staff/requester fixtures; mock gateway; deterministic clock; persistent delivery records
- **Steps:** Donor logs in after due job; compare another donor account
- **Test Data:** Distinct recipient fixtures
- **Expected Result:** Correct reminder displayed; unrelated notifications not exposed
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### UT-UC12-01 — Show dashboard summary

- **Original case ID / module:** UT-UC12-01 / Dashboard and Reports
- **Requirement(s):** FR-022
- **Precondition:** Administrator and known donation/issue/wastage/camp/request fixtures exist
- **Steps:** Admin GET dashboard; compare seeded counts
- **Test Data:** Known stock/pending request/upcoming camp counts
- **Expected Result:** 200; all three summaries match fixture
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### UT-UC12-02 — Generate date-range report

- **Original case ID / module:** UT/IT-UC12-01/02 / Dashboard and Reports
- **Requirement(s):** FR-023
- **Precondition:** Administrator and known donation/issue/wastage/camp/request fixtures exist
- **Steps:** Run reports using valid date ranges and exact inclusive boundaries.
- **Test Data:** Normal and boundary date ranges
- **Expected Result:** Totals are correct and boundary records are included once.
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC12-04 — Reject inverted or invalid date range

- **Original case ID / module:** IT-UC12-04 / Dashboard and Reports
- **Requirement(s):** FR-023
- **Precondition:** Administrator and known donation/issue/wastage/camp/request fixtures exist
- **Steps:** Request from later than to, then malformed date
- **Test Data:** from > to; invalid date
- **Expected Result:** 400; no misleading report
- **Current case status:** PARTIAL automated evidence: `test_invalid_range_fails_before_provider_calls` passed on PostgreSQL 16.16. Confirm the complete STP steps and any UI requirements before marking the case PASS.

### IT-UC12-05 — Return empty report safely

- **Original case ID / module:** IT-UC12-05 / Dashboard and Reports
- **Requirement(s):** FR-023
- **Precondition:** Administrator and known donation/issue/wastage/camp/request fixtures exist
- **Steps:** Choose valid range with no records
- **Test Data:** Empty fixture interval
- **Expected Result:** 200 with zero/empty results, not stale totals
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC12-06 — Restrict administrative report access

- **Original case ID / module:** IT-UC12-06 / Dashboard and Reports
- **Requirement(s):** FR-022, FR-023, SEC-002
- **Precondition:** Administrator and known donation/issue/wastage/camp/request fixtures exist
- **Steps:** Call dashboard/report as donor and requester
- **Test Data:** Donor/requester tokens
- **Expected Result:** 403; operational or donor data not leaked
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### IT-UC12-07 — Keep reports consistent with committed issue

- **Original case ID / module:** IT-UC12-07 / Dashboard and Reports
- **Requirement(s):** FR-022, FR-023
- **Precondition:** Administrator and known donation/issue/wastage/camp/request fixtures exist
- **Steps:** Issue unit; refresh dashboard and selected-range report
- **Test Data:** Valid issue committed; relevant reporting date
- **Expected Result:** Stock and issue totals reflect committed transaction once
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### ST-UC12-08 — Dashboard/report workflow end to end

- **Original case ID / module:** ST-UC12-08 / Dashboard and Reports
- **Requirement(s):** FR-022, FR-023
- **Precondition:** Administrator and known donation/issue/wastage/camp/request fixtures exist
- **Steps:** Admin opens dashboard; selects date range; compares seeded totals
- **Test Data:** Known operational fixture
- **Expected Result:** UI shows correct stock, pending requests, camps and report totals
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### SEC-TC-01 — Salted hash storage

- **Original case ID / module:** SEC-TC-01 / Security
- **Requirement(s):** SEC-001
- **Precondition:** Isolated test deployment; accounts for all roles; authorized access to audit/test DB
- **Steps:** Register donor; inspect password column using authorized test DB access
- **Test Data:** Test password
- **Expected Result:** Supported salted hash; no plaintext password
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### SEC-TC-02 — Unique salt for same password

- **Original case ID / module:** SEC-TC-02 / Security
- **Requirement(s):** SEC-001
- **Precondition:** Isolated test deployment; accounts for all roles; authorized access to audit/test DB
- **Steps:** Register two donors with same password; compare hashes
- **Test Data:** Two unique emails/mobiles; same password
- **Expected Result:** Hashes differ; both verify correctly
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### SEC-TC-03 — No password/token leakage

- **Original case ID / module:** SEC-TC-03 / Security
- **Requirement(s):** SEC-001, SEC-006
- **Precondition:** Isolated test deployment; accounts for all roles; authorized access to audit/test DB
- **Steps:** Inspect login/register responses and audit logs
- **Test Data:** Successful and failed login
- **Expected Result:** Password/token not present in logs or unrelated response fields
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### SEC-TC-04 — Deny donor inventory changes

- **Original case ID / module:** SEC-TC-04 / Security
- **Requirement(s):** SEC-002
- **Precondition:** Isolated test deployment; accounts for all roles; authorized access to audit/test DB
- **Steps:** Donor POST blood-units
- **Test Data:** Valid donor token
- **Expected Result:** 403; no inventory write
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### SEC-TC-05 — Deny requester review and issue

- **Original case ID / module:** SEC-TC-05 / Security
- **Requirement(s):** SEC-002
- **Precondition:** Isolated test deployment; accounts for all roles; authorized access to audit/test DB
- **Steps:** Requester PATCH approval and POST issue
- **Test Data:** Requester token
- **Expected Result:** 403; request/stock unchanged
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### SEC-TC-06 — Deny staff user-role management

- **Original case ID / module:** SEC-TC-06 / Security
- **Requirement(s):** SEC-002
- **Precondition:** Isolated test deployment; accounts for all roles; authorized access to audit/test DB
- **Steps:** Staff attempts restricted role-setting operation
- **Test Data:** Staff token; admin-role payload
- **Expected Result:** 403; no elevation
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### SEC-TC-07 — Reject client-assigned privileged registration

- **Original case ID / module:** SEC-TC-07 / Security
- **Requirement(s):** SEC-002
- **Precondition:** Isolated test deployment; accounts for all roles; authorized access to audit/test DB
- **Steps:** POST public registration with role=admin or staff
- **Test Data:** New registration + elevated role
- **Expected Result:** Elevated role not granted; reject field or ignore under documented contract
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### SEC-TC-08 — SQL injection field input

- **Original case ID / module:** SEC-TC-08 / Security
- **Requirement(s):** SEC-003
- **Precondition:** Isolated test deployment; accounts for all roles; authorized access to audit/test DB
- **Steps:** Send SQL metacharacter payload to login/search
- **Test Data:** Invalid email and filter payload
- **Expected Result:** Rejected/safely treated as data; no SQL execution or DB error leakage
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### SEC-TC-09 — XSS-safe profile rendering

- **Original case ID / module:** SEC-TC-09 / Security
- **Requirement(s):** SEC-003
- **Precondition:** Isolated test deployment; accounts for all roles; authorized access to audit/test DB
- **Steps:** Submit script-like name; view profile and donor search
- **Test Data:** <script>alert(1)</script>
- **Expected Result:** Rejected or contextually escaped; no script execution
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### SEC-TC-10 — Enforce field length limits

- **Original case ID / module:** SEC-TC-10 / Security
- **Requirement(s):** SEC-003
- **Precondition:** Isolated test deployment; accounts for all roles; authorized access to audit/test DB
- **Steps:** Submit email longer than SRS string(100) limit
- **Test Data:** 101-character email
- **Expected Result:** 400; no truncated ambiguous identity
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### SEC-TC-11 — Reject malformed JSON and unsupported enums

- **Original case ID / module:** SEC-TC-11 / Security
- **Requirement(s):** SEC-003
- **Precondition:** Isolated test deployment; accounts for all roles; authorized access to audit/test DB
- **Steps:** POST malformed request and unsupported blood group/component
- **Test Data:** Bad JSON; group ZZ; component Unknown
- **Expected Result:** 400; no partial write or server stack trace
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### SEC-TC-12 — Expired token denied

- **Original case ID / module:** SEC-TC-12/13 / Security
- **Requirement(s):** SEC-004
- **Precondition:** Isolated test deployment; accounts for all roles; authorized access to audit/test DB
- **Steps:** Call protected endpoints with expired and tampered tokens.
- **Test Data:** Expired token; modified token
- **Expected Result:** Each call returns 401 and exposes no protected data.
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### SEC-TC-14 — Missing token denied

- **Original case ID / module:** SEC-TC-14 / Security
- **Requirement(s):** SEC-004
- **Precondition:** Isolated test deployment; accounts for all roles; authorized access to audit/test DB
- **Steps:** Call protected API with no authentication
- **Test Data:** Missing session/token
- **Expected Result:** 401; no protected output
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### SEC-TC-15 — Donor cannot view another donor health data

- **Original case ID / module:** SEC-TC-15 / Security
- **Requirement(s):** SEC-005
- **Precondition:** Isolated test deployment; accounts for all roles; authorized access to audit/test DB
- **Steps:** Donor A GET Donor B health/eligibility details
- **Test Data:** Two donors; A token; B ID
- **Expected Result:** 403/approved privacy-preserving 404; no B medical data
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### SEC-TC-16 — Requester cannot view donor health data

- **Original case ID / module:** SEC-TC-16 / Security
- **Requirement(s):** SEC-005
- **Precondition:** Isolated test deployment; accounts for all roles; authorized access to audit/test DB
- **Steps:** Requester calls eligibility detail API
- **Test Data:** Requester token
- **Expected Result:** 403; no donor health inputs
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### SEC-TC-17 — Own donor and authorized staff can access permitted health data

- **Original case ID / module:** SEC-TC-17 / Security
- **Requirement(s):** SEC-005
- **Precondition:** Isolated test deployment; accounts for all roles; authorized access to audit/test DB
- **Steps:** Call same allowed detail as donor owner and staff
- **Test Data:** Owner token; authorized staff token
- **Expected Result:** Permitted responses only; password/hash excluded
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### SEC-TC-18 — Record failed login events

- **Original case ID / module:** SEC-TC-18/19 / Security
- **Requirement(s):** SEC-006
- **Precondition:** Isolated test deployment; accounts for all roles; authorized access to audit/test DB
- **Steps:** Trigger failed login and forbidden-access events.
- **Test Data:** Wrong password; unauthorized request
- **Expected Result:** Audit records capture time, action, actor/correlation data without secrets.
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### SEC-TC-20 — Verify HTTPS and sanitized errors

- **Original case ID / module:** SEC-TC-20 / Security
- **Requirement(s):** SEC-003 / SRS 3.3
- **Precondition:** Isolated test deployment; accounts for all roles; authorized access to audit/test DB
- **Steps:** Inspect deployed HTTPS URL/certificate; trigger controlled error
- **Test Data:** Staging setup and invalid request
- **Expected Result:** Client-server HTTPS works; no stack trace/secret exposure; TLS specifics recorded
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### NFR-TC-01 — Inventory/search response time

- **Original case ID / module:** NFR-TC-01 / Non-functional
- **Requirement(s):** NFR-001
- **Precondition:** Production-like isolated staging; chosen database engine; approved measurement configuration
- **Steps:** Warm up; run proposed 50 virtual users for five minutes; record endpoint and combined latency percentiles and achieved throughput
- **Test Data:** Seed 1,000 donors and 5,000 units; mixed stock and donor-search requests; load proposal subject to team approval
- **Expected Result:** At least 95% of measured inventory/search requests complete within 2 seconds under the agreed load; report errors/throughput too
- **Sprint update:** The approved demonstration protocol is described above; retain the stronger original proposal separately until specifically adopted.
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### NFR-TC-02 — Operating-window availability

- **Original case ID / module:** NFR-TC-02 / Non-functional
- **Requirement(s):** NFR-002
- **Precondition:** Production-like isolated staging; chosen database engine; approved measurement configuration
- **Steps:** Agree window and exclusions; monitor externally; compute available eligible seconds / total eligible seconds
- **Test Data:** Proposed seven-day operating-window pilot; planned maintenance excluded with recorded timestamps
- **Expected Result:** Availability >=99% for measured window; pilot does not establish a longer unmeasured period
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### NFR-TC-03 — Registration usability

- **Original case ID / module:** NFR-TC-03 / Non-functional
- **Requirement(s):** NFR-003
- **Precondition:** Production-like isolated staging; chosen database engine; approved measurement configuration
- **Steps:** Observe a new user register via desktop and mobile; count primary screens
- **Test Data:** New donor fixture; no prior use
- **Expected Result:** Registration completed in <=5 primary screens; capture task difficulties
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### NFR-TC-04 — Concurrent distinct-request unit issue

- **Original case ID / module:** NFR-TC-04 / Non-functional
- **Requirement(s):** NFR-004
- **Precondition:** Production-like isolated staging; chosen database engine; approved measurement configuration
- **Steps:** Synchronize two approved-request issue calls on separate sessions; repeat 20 times with fresh fixtures
- **Test Data:** One available unit and two distinct approved requests per run
- **Expected Result:** Never two successful allocations for the unit; exactly one committed issue record per fixture
- **Current case status:** PARTIAL automated evidence: `test_same_unit_to_two_requests_has_exactly_one_winner` passed on PostgreSQL 16.16. Confirm the complete STP steps and any UI requirements before marking the case PASS.

### NFR-TC-05 — Concurrent retry consistency

- **Original case ID / module:** NFR-TC-05 / Non-functional
- **Requirement(s):** NFR-004
- **Precondition:** Production-like isolated staging; chosen database engine; approved measurement configuration
- **Steps:** Retry issue after simulated lost response; verify allocation records
- **Test Data:** Same unit after first committed issue
- **Expected Result:** No second allocation or stock decrement; documented conflict/idempotent response
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.

### NFR-TC-06 — Restart and persistence check

- **Original case ID / module:** NFR-TC-06 / Non-functional
- **Requirement(s):** NFR-002 / SRS 6.4
- **Precondition:** Production-like isolated staging; chosen database engine; approved measurement configuration
- **Steps:** Restart app/container; verify persistent records and health recovery
- **Test Data:** Committed donor/unit/request fixture; persistent DB volume
- **Expected Result:** Committed data retained; downtime measured and not hidden from availability calculation
- **Current case status:** NOT ASSESSED; mapping to exact evidence pending.
