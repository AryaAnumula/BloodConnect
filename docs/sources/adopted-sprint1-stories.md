# Adopted BB-01–BB-12 — verbatim source excerpts

These blocks preserve the supplied file, including its older sprint suggestions and TBD estimates. Current named ownership and Sprint-1 planning overrides are in `../ownership.md` and each prompt. No BB-13–24 implementation is included.

## BB-01: Donor signs in to BloodConnect

## User story
As a registered donor, I want to sign in securely so that I can access protected donor services.

## Classification
FR — Functional requirement

## Requirements
FR-002; SEC-001; SEC-004.

## Planning
- Owner: Donor/authentication owner
- Sprint: 1 — proposed; confirm before commitment
- Story points: TBD — re-estimate the revised scope
- Dependencies: BB-02, BB-04; shared backend/schema setup

## Acceptance criteria
- [ ] Valid email and password allow login through a working login screen and the API.
- [ ] Invalid credentials are rejected with an appropriate message without exposing sensitive account information.
- [ ] A successful login allows access to an authenticated donor endpoint.
- [ ] Unauthenticated users cannot access the protected endpoint.
- [ ] A seeded donor account is available for the Sprint 1 demo because registration is planned for Sprint 2.

## Evidence
Reviewed PR, positive/negative login tests and an end-to-end login demo.

## BB-02: User credentials and authenticated sessions remain protected

## User story
As a BloodConnect user, I want my credentials and authenticated session protected so that stored passwords and invalid sessions cannot be used to access my account.

## Classification
SEC — Security requirement

## Requirements
SEC-001; SEC-004.

## Planning
- Owner: Donor/authentication owner
- Sprint: 1 — proposed; confirm before commitment
- Story points: TBD — re-estimate the revised scope
- Dependencies: Shared account model and authentication implementation; integrated with BB-01

## Acceptance criteria
- [ ] Passwords are stored using the framework-supported salted password hash, never plaintext.
- [ ] Passwords and authentication tokens are not exposed in ordinary API responses or application logs.
- [ ] Authenticated APIs reject missing, invalid and expired authentication.
- [ ] A valid session or token grants access only while permitted by the agreed authentication policy.
- [ ] Logout and session/token expiry behavior are implemented and verified against an approved policy.

## Evidence
Reviewed PR, password-storage verification, invalid/expired-authentication tests and logout/session-policy evidence.

## BB-03: Users can access the application during its agreed operating window

## User story
As a BloodConnect user, I want the application available during its agreed operating window so that I can use its services reliably.

## Classification
NFR — Non-functional requirement

## Requirements
NFR-002.

## Planning
- Owner: Testing/CI and operations owner
- Sprint: Shared quality work from Sprint 1; operating-window validation by release — proposed; confirm before commitment
- Story points: TBD — re-estimate the revised scope
- Dependencies: Shared runtime/deployment setup; integrated application

## Acceptance criteria
- [ ] The operating window, planned-maintenance exclusions and availability measurement method are approved and documented.
- [ ] The deployed application has an agreed health check and records evidence of availability and outages.
- [ ] Availability reaches at least 99% during the agreed measurement window, excluding approved planned maintenance.
- [ ] The environment, observed window, downtime and calculation are recorded in the operational review.
- [ ] The story remains incomplete if the agreed measurement window has not been observed; successful startup alone is not availability evidence.

## Evidence
Reviewed setup/deployment PR, health-check evidence and an operational availability review with the observed window and downtime.

## BB-04: Users access only services permitted for their role

## User story
As a BloodConnect user, I want role-appropriate access so that I can use permitted services while restricted actions and information remain protected.

## Classification
SEC — Security requirement

## Requirements
SEC-002; SEC-005.

## Planning
- Owner: Donor/authentication owner
- Sprint: 1 for available endpoints; extend with later features — proposed; confirm before commitment
- Story points: TBD — re-estimate the revised scope
- Dependencies: BB-01, BB-02; approved role-permission matrix

## Acceptance criteria
- [ ] Donor, staff, hospital/requester and administrator test accounts are available.
- [ ] The approved matrix identifies permitted actions for endpoints currently implemented.
- [ ] Donors and hospital/requester users cannot invoke staff/admin functions through the UI or direct API requests.
- [ ] Authorized users can perform permitted actions.
- [ ] Applicable record-specific endpoints reject access to another user's restricted records.
- [ ] New feature endpoints inherit the same server-side authorization rules and tests.

## Evidence
Reviewed PR, approved role matrix, positive/negative permission tests and an authorization demo.

## BB-05: Security-relevant access attempts are recorded safely

## User story
As an authorized security reviewer, I want security-relevant events recorded safely so that failed login and unauthorized access attempts can be investigated without exposing sensitive data.

## Classification
SEC — Security requirement

## Requirements
SEC-006.

## Planning
- Owner: Donor/authentication owner; testing support
- Sprint: 1, extended throughout development — proposed; confirm before commitment
- Story points: TBD — re-estimate the revised scope
- Dependencies: BB-01, BB-02, BB-04; approved audit-event and log-access policy

## Acceptance criteria
- [ ] Failed login attempts create an audit entry.
- [ ] Unauthorized access attempts create an audit entry.
- [ ] Entries contain the approved event fields and sufficient timestamp/context to identify the event.
- [ ] Entries exclude passwords, authentication tokens and donor health data.
- [ ] Audit-log access follows the approved access policy; this story does not require a new dashboard.
- [ ] Automated tests verify both event recording and exclusion of sensitive fields.

## Evidence
Reviewed PR, automated audit tests and sanitized example audit entries.

## BB-06: New donor registers an account

## User story
As a prospective donor, I want to register with my contact and required donor details so that I can create an account and use donor services.

## Classification
FR — Functional requirement

## Requirements
FR-001; SEC-001; SEC-003.

## Planning
- Owner: Donor/authentication owner; UI support
- Sprint: 2 — proposed; confirm before commitment
- Story points: TBD — re-estimate the revised scope
- Dependencies: BB-01, BB-02, BB-04; agreed donor-profile model

## Acceptance criteria
- [ ] Valid details submitted through a working registration screen create a donor account and return HTTP 201 from the API.
- [ ] Required profile fields and their validation rules are agreed before implementation.
- [ ] Missing or malformed fields produce clear validation errors.
- [ ] Duplicate email/mobile values are rejected using the agreed normalization rules.
- [ ] Failed registration does not leave a partially created account.
- [ ] Public registration cannot assign staff, requester or admin privileges.
- [ ] A successfully registered donor can sign in using BB-01.

## Evidence
Reviewed PR, registration/duplicate/validation tests and a registration-to-login demo.

## BB-07: Donor completes eligibility screening

## User story
As a donor, I want my screening information assessed against approved configurable rules so that I can find out whether I meet the system's donation criteria.

## Classification
FR — Functional requirement

## Requirements
FR-003; SEC-005.

## Planning
- Owner: Donor/authentication owner
- Sprint: 2 — proposed; confirm before commitment
- Story points: TBD — re-estimate the revised scope
- Dependencies: BB-01, BB-04; registered or seeded donor profile; approved screening rules

## Acceptance criteria
- [ ] The donor can submit the required screening information through the interface.
- [ ] Valid information is assessed against the approved configured age, weight and donation-gap rules.
- [ ] The assessed result is saved and an eligible/ineligible outcome is available to the donor.
- [ ] Missing or invalid information is rejected without presenting a misleading result.
- [ ] Below-boundary, at-boundary and above-boundary cases follow the approved rules.
- [ ] First-time donors and missing last-donation dates follow an approved policy.
- [ ] The authorized rule-configuration mechanism is agreed; this story does not assume a new admin screen.

## Evidence
Reviewed PR, synthetic screening/boundary fixtures, saved-result tests and a screening demo.

## BB-08: Donor understands an ineligible screening result

## User story
As a donor, I want to see my eligibility result and the reason if I am ineligible so that I understand the screening decision.

## Classification
FR — Functional requirement

## Requirements
FR-004; SEC-005.

## Planning
- Owner: Donor/authentication owner; UI support
- Sprint: 2 — proposed; confirm before commitment
- Story points: TBD — re-estimate the revised scope
- Dependencies: BB-07; approved explanation wording and result-freshness policy

## Acceptance criteria
- [ ] The saved eligibility result is displayed to the donor.
- [ ] An ineligible result includes a reason consistent with the rule or rules that failed.
- [ ] An eligible result is displayed without contradictory ineligibility messaging.
- [ ] Only the donor and authorized staff can view restricted screening information.
- [ ] Changed donor information or rule settings are handled according to the approved result-freshness policy.
- [ ] The result view handles missing results and failures clearly.

## Evidence
Reviewed PR, result/reason and privacy tests, and eligible/ineligible result-screen demos.

## BB-09: Staff finds donors using approved search filters

## User story
As an authorized staff member, I want to search donors by blood group, location and eligibility status so that I can find records matching the required criteria.

## Classification
FR — Functional requirement

## Requirements
FR-005; SEC-002; SEC-005; NFR-001.

## Planning
- Owner: Donor/authentication owner; UI support
- Sprint: 2 — proposed; confirm before commitment
- Story points: TBD — re-estimate the revised scope
- Dependencies: BB-04, BB-06, BB-07; approved staff-visible donor fields

## Acceptance criteria
- [ ] Staff can search through a working donor-search screen.
- [ ] Blood-group, location and eligibility filters return matching records.
- [ ] Supported combinations return records satisfying all selected criteria.
- [ ] Invalid filter values are rejected and no matches display a clear empty state.
- [ ] Results expose only donor fields permitted by the approved access policy.
- [ ] Unauthorized users cannot access search through the UI or direct API requests.
- [ ] 95% of search API requests receive a response within 2 seconds under the approved test load.

## Evidence
Reviewed PR, synthetic single/combined-filter tests, authorization tests, load-test results and a staff-search demo.

## BB-10: New donor completes registration in a short, usable flow

## User story
As a new donor, I want a short and clear registration flow so that I can create my account without navigating unnecessary screens.

## Classification
NFR — Non-functional requirement

## Requirements
NFR-003; FR-001.

## Planning
- Owner: UI/UX owner, with donor/authentication support
- Sprint: 2 — proposed; confirm before commitment
- Story points: TBD — re-estimate the revised scope
- Dependencies: BB-06; agreed definition of a primary screen

## Acceptance criteria
- [ ] A new donor can complete registration in no more than five primary screens.
- [ ] The team documents what counts as a primary screen and verifies the count in a walkthrough.
- [ ] Required fields, validation errors and successful completion are clearly presented.
- [ ] The agreed responsive browser layouts allow the registration flow to be completed without inaccessible controls.
- [ ] The UI is integrated with the real registration API, not only a static mock.

## Evidence
Reviewed UI PR and a recorded usability walkthrough showing the screen count and integrated registration flow.

## BB-11: User-supplied data is processed safely

## User story
As a BloodConnect user, I want my submitted data processed safely so that malformed or malicious input cannot compromise the application or corrupt records.

## Classification
SEC — Security requirement

## Requirements
SEC-003.

## Planning
- Owner: Donor/authentication owner; shared feature-owner support
- Sprint: 2 for donor/search inputs; extend throughout development — proposed; confirm before commitment
- Story points: TBD — re-estimate the revised scope
- Dependencies: Implemented input endpoints; agreed validation and sanitization rules

## Acceptance criteria
- [ ] Server-side validation enforces agreed types, lengths, formats and allowed values on implemented input fields.
- [ ] Malformed input is rejected before an invalid state change is committed.
- [ ] Injection-like and script-like fixtures cannot execute as database commands or browser scripts.
- [ ] Validation remains effective when UI checks are bypassed through direct API calls.
- [ ] Error responses do not expose database internals, secrets or sensitive health data.
- [ ] Feature-specific validation tests are linked here rather than duplicated and counted twice.

## Evidence
Reviewed PR, input-validation/security tests and evidence that rejected input did not alter protected records.

## BB-12: Donor health information remains private

## User story
As a donor, I want my medical and health information accessible only to me and authorized staff so that it is not exposed to other users.

## Classification
SEC — Security requirement

## Requirements
SEC-005; SEC-002.

## Planning
- Owner: Donor/authentication owner; testing support
- Sprint: 2, extended with health-data features — proposed; confirm before commitment
- Story points: TBD — re-estimate the revised scope
- Dependencies: BB-04, BB-06, BB-07, BB-08; approved health-data access policy

## Acceptance criteria
- [ ] The donor can access their own permitted health/screening information.
- [ ] Only staff authorized by the approved policy can access donor health information.
- [ ] Other donors and hospital/requester users cannot retrieve it through the UI or direct API requests.
- [ ] Changing a record identifier does not bypass ownership or staff authorization checks.
- [ ] Search/list responses exclude health fields not permitted for that caller.
- [ ] Tests use synthetic health data rather than real donor records.

## Evidence
Reviewed PR, own-record/other-record/staff-access tests, sanitized fixtures and a privacy-control demo.
