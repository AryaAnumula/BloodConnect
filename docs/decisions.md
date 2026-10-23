# Decision register — read before member branches diverge

## Bootstrap defaults: PROPOSED, NOT APPROVED

These defaults exist to make one runnable common base, not to resolve project policy on behalf of the team. Arya records real team approval, date and affected files in a PR. Do not mark these approved automatically. Change defaults once centrally BEFORE parallel feature work; changing the auth/database basis later affects all members.

| ID | Provisional choice and reason | Alternative / approval action |
| --- | --- | --- |
| D-01 | Python 3.13, Django 5.2 LTS family, DRF 3.16 family, Node 24; exact Python lock in requirements.txt | Review installed versions/support; approve before branch cut. Docker tags are major/minor-family tags, not digest-pinned production images. |
| D-02 | PostgreSQL 16; aligns with ORM constraints and future real-database concurrency tests | MySQL is also allowed by baseline. Team must select engine before feature migrations; SQLite is smoke-only, never concurrency evidence. |
| D-03 | Django database-backed session cookie + CSRF; same-origin server-rendered HTML shells and plain JS | SAD describes JWT as proposed but leaves session/token implementation open. If JWT is required, STOP and redesign auth/OpenAPI/client centrally; do not add a second competing scheme. |
| D-04 | Provisional 30-minute session lifetime, no automatic every-request extension; Django login/logout rotation/invalidation; 12-character password minimum | Team must approve absolute/sliding expiry, logout/revocation, HTTPS and provisioning policies. HTTP/insecure cookies only for loopback development. Deployment review must set secure cookies and HTTPS; runserver is not production. |
| D-05 | Registration fields/schema and normalization in OpenAPI: full_name, email, mobile, blood_group, location; E.164 mobile; lowercase normalized email | Confirm fields/uniqueness and normalization before profile model or registration implementation. Never allow public role/is_staff/is_superuser assignment. |
| D-06 | GitHub Actions manual `workflow_dispatch` draft; easiest same-repo checks | Baseline also mentions Jenkins. Enable PR triggers/required checks only after tool approval. No automatic-PR-check claim until configured and run. |
| D-07 | Screening answer shapes in OpenAPI; no runtime clinical defaults | Approve exact rules, versions, boundary inclusivity and null/first-time behavior. SRS examples (18–65, 50 kg, 90 days) are examples until adopted. `approved_screening_rules()` deliberately raises. |
| D-08 | Persist versioned eligibility result; propose NOT_SCREENED/STALE search states | Approve freshness, re-screening and rule-change behavior before finalizing schema/selectors/tests. Do not present old results as current. |
| D-09 | Clinical-data access only own donor or explicitly authorized staff; ADMIN alone gives no health access | Approve staff role plus clinical permission, provisioning and field visibility. Django superuser bypass needs operational restriction/review; do not distribute superuser accounts as admin fixtures. |
| D-10 | Allowlisted security audit fields only: timestamp, event type, actor ID if known, correlation ID, outcome | Approve access/retention, failure behavior and rejected-credential event semantics; no raw request payload, health data, password or token. |
| D-11 | Health checks and monitoring evidence scaffold | Approve operating window, measurement duration, maintenance exclusions, polling method and outage accounting; until then 99% availability cannot pass. |
| D-12 | NFR-001 target is 95% within 2 seconds | Approve dataset size, concurrency/load, duration, hardware and API set; a tiny smoke test cannot prove performance. |

## Later-scope decisions — explicitly deferred, no implementation here

Camp action-by-role conflict, walk-in model/capacity, late-booking reminder policy, partial fulfilment/CLOSED semantics, whole-unit quantity semantics, retention and report timezone boundaries remain tracked in the SRS review. No BB-13–24 implementation has been generated to guess those answers.

## Approval record template

Decision ID | Approved wording | Approver(s) | Date | Affected contracts/models/tests | PR

The example `config/decisions.example.json` is an approval checklist, not medical configuration or permission to bypass open questions.
