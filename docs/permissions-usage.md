# Using accounts.permissions (BB-04 / BB-12)

| Route type | What to use |
| --- | --- |
| Public (health, csrf, login, register) | `AllowAny`; CSRF still applies to POST |
| Any signed-in active user (logout, /auth/me) | `IsAuthenticated` |
| Staff only (donor search) | `permission_classes = [IsAuthorizedStaff]`; return summary fields only, never health answers |
| Own donor OR authorized staff (profile, screening, eligibility result) | `IsAuthenticated` plus an object-level check with `may_view_donor_health` (arrives with BB-12) |

Rules:
- Do NOT put `IsAuthorizedStaff` alone on own-donor routes; legitimate donors would get 403.
- "Own donor" means the donor profile found in the database for the donor_id belongs to `request.user`. A supplied ID is never proof of ownership.
- ADMIN, REQUESTER and Django superusers get no donor health access through a generic signed-in check.
- Until `may_view_donor_health` is implemented it raises NotImplementedError; endpoints must fail closed, not skip the check.