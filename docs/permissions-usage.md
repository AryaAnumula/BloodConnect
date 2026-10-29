# Using shared permissions — BB04/BB12

| Route | Server-side protection |
| --- | --- |
| Public health/CSRF/login/register | Existing public permission; unsafe requests still require CSRF |
| Logout and /auth/me | Existing active authenticated-session checks |
| GET /api/v1/donors (search) | IsAuthenticated + IsAuthorizedStaff; safe summary fields only |
| Profile/screening/result | IsAuthenticated + IsDonorOrAuthorizedStaff as role gate, then may_view_donor_health on the retrieved profile's user_id |

## Shared policy actually implemented by BB12
from accounts.permissions import IsDonorOrAuthorizedStaff, IsAuthorizedStaff, may_view_donor_health

may_view_donor_health(*, user, donor_user_id) -> bool is pure/read-only: no audit, transaction or mutation. Pass profile.user_id from the DB, not the supplied profile UUID and not a client-supplied owner. Active DONOR sees own records; active STAFF needs explicit accounts.view_donor_health; ADMIN/REQUESTER/plain STAFF and every superuser role denied. Superuser DONOR must not fall through to the owner branch. No is_staff or generic signed-in bypass.

Role-only gate does not prove ownership. IsAuthorizedStaff alone must NOT be used for own-donor routes. Endpoint owners use these same functions; do not create different medical-access policies.

## Profile route and safe fields
GET /api/v1/donors/{donor_id} uses profile UUID (not account UUID). Own donor and authorized staff get only id,user_id,full_name,email,mobile,blood_group,location. No passwords, tokens or screening answers. Unknown record and other donor's record both return standard404 not_found with indistinguishable error code/message/fields (request IDs naturally differ). Invalid roles/anonymous are rejected403 before record lookup.

## Audit ownership
Role/auth403 is recorded once by core.errors' shared hook. Existing-record object denial disguised as404 is recorded once at the endpoint boundary via accounts.health_access.record_donor_health_denial(*, request); pure policy must not record again. Ordinary missing record creates no denial event. Allowed fields only: timestamp,event_type,known actor UUID,request_id,outcome. On audit-storage failure, existing safe503 propagates; no private profile data or raw DB exception. See limited D10 record in docs/decisions.md; retention/viewer policy is not silently approved.

## Provisioning
Maintainer-only command (no public endpoint): python backend/manage.py grant_donor_health_access --user-id <STAFF_UUID>; append --revoke to remove. Grant only active non-superuser STAFF. Never include real contact/health data in fixtures or distribute superuser credentials as demo staff.

## Endpoint-owner handoff
- Ankitha BB07: call shared gate/object helper before screening read/write, reject malformed input before mutation, use profile.user_id, coordinate404/audit ownership.
- Yashwitha BB08: reuse policy for results and shared denied-access hook; no frontend-only ownership check.
- Yashwitha BB09: staff-only permission, return id,blood_group,location,eligibility_status summaries only, no health answers or contacts.
- Arya BB11: regression evidence can reuse these policy/API tests instead of duplicating rules.

No BB07/08/09 file is rewritten by this completion patch. Full BB12 acceptance across those features remains pending their actual integration. For a college-project checkpoint, profile flow plus these tested shared helpers is ready for central review; don't claim unimplemented endpoint coverage.
