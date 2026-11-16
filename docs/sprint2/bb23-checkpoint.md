# BB-23: Administrator dashboard — independent checkpoint

Owner Arya. Branch team/arya-bb23, directly from testing97614c8; not based on PR59 or the other reporting story. Latest16November instruction supersedes combined BB23/24 packaging. Only Arya merges; commits use his existing identity, no assistant coauthor. No automatic CI.

GET /api/v1/dashboard and /dashboard page retain agreed public schemas and active authenticated non-superuser ADMIN gates. Common reporting infrastructure is intentionally byte-identical in both story PRs; feature routes/API/provider/selector/frontend/tests are separate. Either branch registers only its own endpoint and needs neither the other story nor unmerged domain apps to start. Common app registration must appear once when eventually integrating; preserve both distinct route includes and test files.

Missing stock_summary and upcoming_camp_count (scheduling is not installed on testing yet) returns redacted reporting_unavailable503. Available empty source may return zero. Boundary doubles are orchestration tests, not actual source/reconciliation acceptance. No inventory/issue/camp model or competing migration is invented. Stock DTO retains available_quantity. Activity dates retain inclusive Asia/Kolkata→UTC half-open definition; events/units/issues/explicit discards remain distinct; expiry is not discard. No privacy/clinical defaults or full-story completion claim.

Validation on the actual published head is recorded in the PR body and local central decision log. Prior combined59 runs are historical, not proof of this independent branch. Browser walkthrough is not claimed; previous automation block is not retried/bypassed.

Provider boundaries: inventory.selectors.stock.stock_summary(actor,filters,page,page_size) -> StockPage{count,results[{blood_group,component_type,available_quantity}]}; scheduling.selectors.summary.upcoming_camp_count(*,now) -> nonnegative int; blood_requests.selectors.reporting.pending_request_count() reads actual SUBMITTED requests and is included here. Camp provider belongs to Ankitha; if absent,503 rather than direct import/startup failure. Stock max32 distinct group/component rows, no silent truncation.
