# Shared schema and migration ownership

## Foundational schema actually present

`accounts.User` has UUID primary key, unique normalized email, Django hashed password, role enum DONOR/STAFF/REQUESTER/ADMIN and standard Django account/group/permission fields. Initial migration is included. Role is not clinical authorization. `is_staff` is the Django admin-site flag, NOT an automatic clinical-staff grant. No Django admin site is mounted.

Normalization in manager is only foundational; BB-06 must validate and normalize all ingress paths and enforce uniqueness consistently. Prefer database-backed normalized uniqueness, transaction-safe duplicate handling and real-database tests. Do not assume manager normalization alone covers direct model writes.

## Proposed models and candidate schema — approval required before shared rollout

| Model / file | Relationships and minimum proposed fields | Owner / gate |
| --- | --- | --- |
| DonorProfile / donors/models/profile.py | UUID; one-to-one User; full_name; unique normalized mobile; blood_group; location; created_at/updated_at | Ankitha; Arnav reviews schema/constraints; D-05 |
| EligibilityResult / donors/models/eligibility.py | UUID; FK profile; assessed answers needed for approved rules; status; controlled reason codes/messages; assessed_at; rules_version; freshness metadata | Ankitha; Yashwitha consumes; Arnav privacy review; D-07/08/09 |
| SecurityEvent / audit/models/event.py | Candidate schema and initial migration now provided for local review: UUID; timestamp; allowlisted event_type/outcome pairs; actor UUID nullable; request_id; no credential/health payload | Arya; Arnav schema review; D-10 NOT approved; do not apply to shared environments until approval |
| Rule configuration | Versioned authorized mechanism; no public write endpoint or assumed new admin screen | Ankitha; D-07 |

Mobile/email and donor-account creation must be atomic. UUID account IDs and donor-profile IDs are distinct. Do not expose health answers through list summaries. Do not attach arbitrary request bodies to audit events.

## Migration workflow

1. Agree the schema/constraint change with the named owner; one active structural writer per shared model.
2. Merge the latest main into your branch; create models and import them in models/__init__.py.
3. Run `python backend/manage.py makemigrations accounts donors audit` for the changed apps, then inspect generated operations.
4. Run migrations and tests on a new chosen-engine database; record commands/results in the PR.
5. Commit schema code and its migration together. Run `makemigrations --check --dry-run` before review.
6. If two migration leaf nodes conflict, coordinate with Arnav and merge main. Use Django's migration-merge process only after inspecting dependencies; generate a merge migration when independent operations are safe. If operations conflict, design a new reconciliation migration. Never delete applied migration history or manually patch shared tables.
7. Do not edit another member's models/migration merely to make your tests pass. Document missing contracts and wait or mock at the service boundary.

The SQLite smoke profile validates starter mechanics only; it is not chosen-engine constraint or concurrency evidence. Real-data migrations are outside this starter.
