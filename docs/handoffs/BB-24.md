# BB-24: Activity reports — independent checkpoint

Owner Arya. Branch team/arya-bb24, directly from testing97614c8; not based on PR59 or the other reporting story. Latest16November instruction supersedes combined BB23/24 packaging. Only Arya merges; commits use his existing identity, no assistant coauthor. No automatic CI.

GET /api/v1/reports and /reports page retain agreed public schemas and active authenticated non-superuser ADMIN gates. Common reporting infrastructure is intentionally byte-identical in both story PRs; feature routes/API/provider/selector/frontend/tests are separate. Either branch registers only its own endpoint and needs neither the other story nor unmerged domain apps to start. Common app registration must appear once when eventually integrating; preserve both distinct route includes and test files.

Missing collection_wastage_totals and request_issue_totals returns redacted reporting_unavailable503. Available empty source may return zero. Boundary doubles are orchestration tests, not actual source/reconciliation acceptance. No inventory/issue/camp model or competing migration is invented. Stock DTO retains available_quantity. Activity dates retain inclusive Asia/Kolkata→UTC half-open definition; events/units/issues/explicit discards remain distinct; expiry is not discard. No privacy/clinical defaults or full-story completion claim.

Validation on the actual published head is recorded in the PR body and local central decision log. Prior combined59 runs are historical, not proof of this independent branch. Browser walkthrough is not claimed; previous automation block is not retried/bypassed.

Provider boundaries: inventory.selectors.reporting.collection_wastage_totals(*,start,end) -> donation_event_count,collected_unit_count,wasted_unit_count; blood_requests.selectors.reporting.request_issue_totals(*,start=None,end=None) -> issued_unit_count. Aware UTC half-open bounds, successful empty source0, absent model/source503. Yashwitha owns collection/wastage and Arnav owns actual issue history; fulfilled request totals are not an issue-history substitute.
