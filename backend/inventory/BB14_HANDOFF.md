# BB14 final isolated integration - WIP, ready for owner review

Actual donor PR51 a93f01cccfe2a242f0a91f3f3646775ff4282297 is now composed with the actual facade/evaluator/screening and history-v2 after controlled reconciliation. BB13 acceptance is published in #56 at625c522dc937de65fa692e20286e8517a55d366a. This supersedes old missing-donor references below.

BB14 checks source5f15a8b8617ff1d8c2bde54b73e375c8ec38494e; production stock/disposition/reporting is unchanged from062550b86fddd67d5ef6f69bd8d6f7160e8fb58b. Actual config.urls with Arya PR59 routepatch739ff48524fc9552fa3c92a343247b711c10e4c2, canonical PR60 42afc198b70fd9d3821580fbbd25d4ee2fda4653, reporting PR61 8b1349f295170525b6d668e3fb55e48586950d58 and actual issue PR64 b5f72bee8ab16022154599c9a5354a9f6da69272. No owner source is committed here.

PostgreSQL16.16 (Visual C++1944,64-bit), command `python manage.py test inventory.acceptance.intake_routes inventory.acceptance.stock_routes inventory.acceptance.alert_routes --noinput --verbosity 2`:9pass/0fail/0skip,2.015s; BB14 owns4 of these checks. Actual fresh intake201 advanced donor history; stock1 -> disposition DISCARDED -> stock0; report exactly1event/1unit/0issues/1waste. Additional real-route checks reconcile historical components/dispositions/report, actual Arnav issue once and replay rejection, and ADMIN read-only gates. System check0issues, no migration drift, git diff --check passed. Full log in acceptance/evidence/final-actual-donor-stock-alert-routes-pg16.txt.

Recorded browser/load evidence was reused because production behavior did not change:1131requests/0errors/p95=0.311102300s at748022830aac27dd1d28717255531de5b5deed06, PostgreSQL16.16,500donors/500units/5clients/10secwarmup+60measured; original acceptance scope/hardware retained in earlier evidence. Prior dashboard/report checks12pass/0fail/0skip at1ea040fbbcae26b939d60b10f115f42891a88e8f remain separate evidence. No unchanged load/browser rerun.

All six owned criteria have bounded evidence and actual-source integration checks now pass. Remaining: Arya's required review and central shared-source/route integration, with core seeder patch carried by Arya and donor config carried by Ankitha/Arya after target-db reconciliation. Keep WIP; only Arya merges. No additional inventory code/test blocker in this tested composition. Parent evidence was propagated additively; no force-push, rebase, merge or shared-file changes.

## Historical provenance

## Latest published owner-provider reconciliation

The former dashboard/report-source dependency is now resolved in the isolated lane using actual Arya PR60 `42afc198b70fd9d3821580fbbd25d4ee2fda4653` and PR61 `8b1349f295170525b6d668e3fb55e48586950d58`, with Arnav request/issue source `b5f72bee8ab16022154599c9a5354a9f6da69272`. Only exact owner-file deltas were composed; overlapping files were required to be byte-identical. No Git merge or owner-source edit occurred.

Inventory test source `1ea040fbbcae26b939d60b10f115f42891a88e8f`: PostgreSQL16.16,12focused tests PASS,0fail/0skip,1.699s. Includes actual empty/full dashboard stock/request/camp reads and API200 refresh after a real discard, actual issue-service/IssueRecord/report200, explicit missing-camp/missing-issue503, provider-loader failure/programming-error behavior, and Arya's formerly stale domain-report test. That reporting-owner conflict now passes at the new exact PR61 SHA; the older recorded failure remains historical evidence only.

PR51 remains `faf570e12eaff5ef412905d24e2027e7765d3482`; its actual donor tranche is still absent. Seven adapter-free donor checks remain PENDING. No fresh-intake/history-v2/stale-booking acceptance is claimed. Keep all three stories WIP until required real donor integration, shared wiring/baseline and final review pass.

---

## 16 November 2026 continuation - read/UI/performance evidence

Arnav's exact issue source b5f72bee8ab16022154599c9a5354a9f6da69272 was consumed in an isolated composition only; no merge or request-source edit. Inventory tests now retain explicit missing-provider503 coverage and verify real IssueRecord/issue-service/report200 when the provider exists. Route-dependent classes explicitly declare the isolated test URLconf; Arya still owns production wiring.

Focused PostgreSQL16.16 results: absent-provider lane13run/12pass/1explicit real-provider skip; actual-provider lane16run/16pass/0skip including actual request issue totals. Updated inventory-focused run at d8b5ad8c1a839ff567dfdc22f551dfc4512c3a52:32run/25pass/7actual-donor skips/0fail; the seven are separately gated new donor tests, not stock/report failures.

Scoped approved S2-09 protocol (shared-rules v1.1,15Nov2026; parent unrelated approvals stay separate):500 synthetic donors / 500 units,5 authenticated clients,10s warm-up then60s measured. Run at748022830aac27dd1d28717255531de5b5deed06 on PostgreSQL16.16/Python3.13.17/Django5.2.18, Windows11,12 logical CPUs, physical RAM16471101440bytes. Local Django LiveServer WSGI, real session/CSRF login, test-only route composition. API mix906 stock reads / 225 unit-list reads;1131 samples;0 errors; p95=0.311102300s; max=0.590743800s;100%under2s. All slow/failed requests are retained by the harness; no failed response was discarded.60.237s finish includes the final in-flight tail. The scoped demo read target PASS is not production capacity or availability evidence. Reproduce with inventory.tests.performance and the explicit source/output environment variables. Full raw samples/hardware/clock record are retained in BB14_POSTGRES16_LOAD_2026-11-16.json.

Actual browser evidence at7997bd996c17e8db608bda170525463046f9b29d: usable3->2 after discard->1 after quarantine->0 after actual Arnav submit/review/issue services. ADMIN sees stock without unit-management controls. A real report displayed1donation event/3collected units/1issued/1discarded; quarantine did not add wastage. Report was200 with real issue provider. Screenshots/server logs and actual DB reconciliation are retained; fixture intake origin is explicitly historical, not new-donation proof.

All six adopted BB14 criteria now have bounded isolated-lane evidence: component-wise counts PASS; source reconciliation PASS; refresh after writes PASS; state/expiry inclusion PASS; access restrictions PASS; approved demo read-load target PASS. Keep PR WIP pending Arya's shared wiring/integration/final review and any required real donor chain acceptance; not a claim of merged testing completion. Dashboard camp-count provider remains a separate owner dependency. Reporting PR61's old domain503 test expectation is a concrete owner-side test conflict, reported without editing reporting files.

---

# BB-14 WIP - stock, units, disposition and reporting

This story is stacked on BB13 PR56. Review its diff against story/yashwitha-bb13. Only Arya merges; do NOT merge this PR into the story branch. Arya integrates dependencies and chooses the final base/integration order. No BB15 code included.

Migration inventory.0002_inventorydisposition follows inventory0001. Atomic AVAILABLE->DISCARDED/QUARANTINED, one protected terminal history row; quarantine/expiry are not wastage. STAFF-only unit/disposition controls; STAFF/ADMIN stock reads; ADMIN page omits management controls and requests.

stock_summary(*,actor,filters:dict,page=1,page_size=20) returns {count,page,page_size,results:[{blood_group,component_type,available_quantity}]}; count grouped rows, maximum32 pairs, page_size1..100. Shared usable_units query: AVAILABLE and Kolkata today<expiry. Derived EXPIRED never changes stored status.

collection_wastage_totals(*,start,end) returns exactly {donation_event_count,collected_unit_count,wasted_unit_count} from confirmed events, units, explicit DISCARDED history; aware half-open timestamp bounds and Kolkata collection dates. Historical importer is DEBUG-only, dry-run unless --apply, replay conflicts preserved, excludes events containing fictional ISSUED units. It is fixture evidence, not issue workflow proof.

Publication composition: system check, no migration drift, diff check and7 affected stock/page tests PASS on PostgreSQL18.6. Original65-test evidence remains at exact source67d8892f6f38d10dd58c503ac25d3c591e368829 on PostgreSQL18.6; it is not relabelled as the PR head. PostgreSQL16 inventory/concurrency acceptance is pending. Full dashboard/report acceptance remains pending the real camp summary and Arnav issue-history sources, browser/performance checks and central integration/review. All code remains WIP.
