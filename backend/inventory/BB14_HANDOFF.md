# BB-14 WIP - stock, units, disposition and reporting

This story is stacked on BB13 PR56. Review its diff against story/yashwitha-bb13. Only Arya merges; do NOT merge this PR into the story branch. Arya integrates dependencies and chooses the final base/integration order. No BB15 code included.

Migration inventory.0002_inventorydisposition follows inventory0001. Atomic AVAILABLE->DISCARDED/QUARANTINED, one protected terminal history row; quarantine/expiry are not wastage. STAFF-only unit/disposition controls; STAFF/ADMIN stock reads; ADMIN page omits management controls and requests.

stock_summary(*,actor,filters:dict,page=1,page_size=20) returns {count,page,page_size,results:[{blood_group,component_type,available_quantity}]}; count grouped rows, maximum32 pairs, page_size1..100. Shared usable_units query: AVAILABLE and Kolkata today<expiry. Derived EXPIRED never changes stored status.

collection_wastage_totals(*,start,end) returns exactly {donation_event_count,collected_unit_count,wasted_unit_count} from confirmed events, units, explicit DISCARDED history; aware half-open timestamp bounds and Kolkata collection dates. Historical importer is DEBUG-only, dry-run unless --apply, replay conflicts preserved, excludes events containing fictional ISSUED units. It is fixture evidence, not issue workflow proof.

Publication composition: system check, no migration drift, diff check and7 affected stock/page tests PASS on PostgreSQL18.6. Original65-test evidence remains at exact source67d8892f6f38d10dd58c503ac25d3c591e368829 on PostgreSQL18.6; it is not relabelled as the PR head. PostgreSQL16 inventory/concurrency acceptance is pending. Full dashboard/report acceptance remains pending the real camp summary and Arnav issue-history sources, browser/performance checks and central integration/review. All code remains WIP.
