# BB15 final actual-donor integration - WIP, ready for owner review

Actual donor tranche PR51 a93f01cccfe2a242f0a91f3f3646775ff4282297 is now composed without donor adapters; controlled reconciliation preceded history-v2. Fresh browser/intake/history/actual booking evidence is in BB13 #56 at625c522dc937de65fa692e20286e8517a55d366a. Older unpublished-donor and skipped-test references below are historical and superseded.

BB15 checks source3943331d2ef9ac548d6efec28279eed111652873; production alerts unchanged from1c6a9b23d05e786dae2f7ae85b23df2ee973ca28. Shared-source pins: PR59 routes739ff48524fc9552fa3c92a343247b711c10e4c2, PR60 42afc198b70fd9d3821580fbbd25d4ee2fda4653, PR61 8b1349f295170525b6d668e3fb55e48586950d58, real request/issueb5f72bee8ab16022154599c9a5354a9f6da69272. Only owned inventory followups are committed.

PostgreSQL16.16 (Visual C++1944,64-bit), command `python manage.py test inventory.acceptance.intake_routes inventory.acceptance.stock_routes inventory.acceptance.alert_routes --noinput --verbosity 2`:9pass/0fail/0skip,2.015s. BB15 owns3 checks: actual shared alert routes/deduplication/resolution history, active STAFF-only recipient/reader gates, and two real fresh intake201s advancing donor history and recovering low stock. That recovery resolves exactly1episode (32 ->31active), preserves32existing intents/episodes, replaycreates0. Actual saved results become history-stale. Existing recipient restriction, failure/retry and real delivery evidence retained. Systemcheck0issues, no migration drift, git diff --check passed. Full log is committed under acceptance/evidence.

Unchanged browser/transport evidence at7997bd996c17e8db608bda170525463046f9b29d is reused:33intents actually delivered through existing private Node mock,33DeliveryAttempts and33actual receipts (fingerprint_version2), browser DELIVERED, subsequent resolution retains all delivery history. Queue-only checks above are not counted as a repeated delivery run. No receipt store/token is committed. Prior PostgreSQL16 suite/concurrency/failure/retry and recipient tests retain their exact original source labels.

All six owned criteria have bounded evidence and final isolated actual-source checks now pass. Remaining is required Arya review and central integration/target rollout: Arya carries shared routes/core seeder companion patch; Ankitha/Arya carry history-v2 configuration after target-db reconciliation. Keep WIP until review/acceptance. No missing donor implementation or failing inventory check remains in this tested composition. No new PRs, merges, rebase or force-push.

## Historical provenance

## 16 November 2026 continuation - actual browser and transport evidence

The active non-superuser STAFF-only recipient gate and episode/provider runtime are unchanged. Component/threshold/concurrency/failure/retry evidence from the prior PostgreSQL16 run remains preserved; no unchanged broad suite was repeated.

At inventory7997bd996c17e8db608bda170525463046f9b29d, with Arnav b5f72bee8ab16022154599c9a5354a9f6da69272 in a separate composition, the actual controlled evaluator queued32 LOW_STOCK and1 NEAR_EXPIRY intents. The real browser first displayed33 PENDING alerts. The existing dispatcher sent actual private127.0.0.1 HTTP to Arya's Node24 mock and persisted33 DELIVERED intents and33 DeliveryAttempts;33 actual receipt files had fingerprint_version2 and included both event types. The browser refresh displayedDELIVERED, including the near-expiry platelet row. No receipt or delivered state was fabricated and no receipt store/token is committed.

After actual Arnav issue/allocation consumed the only near-expiry unit, the real controlled evaluator returned created0/resolved1/active32. All33delivered intents stayed intact and no new intent was generated on resolution. Alert history remains retained. This is an executed domain->existing outbox->private Node->stored attempt->browser projection flow, not queue-only proof or external carrier delivery.

The six adopted BB15 criteria have passing bounded component/real transport/browser evidence:near-expiry flags, actual mocked notification, low-stock triggers, threshold boundaries, authorized explicit configuration and redacted attempts/receipt/failure history. Keep PR WIP pending required shared integration and Arya's final acceptance/review; no merge or whole-story feature label. Actual fresh-donation/history/booking integration still needs the exact unpublished PR51 donor tranche; the new real donor tests remain explicitly skipped rather than substituted with adapters.

---

# BB-15 alert episodes WIP

Stacked on the single BB14 PR65, which depends on BB13 PR56. Only Arya merges. Do not merge child PRs into story parents; Arya controls shared integration and final bases. This diff contains BB15 only.

inventory.0003_alertsweep_inventoryalert follows inventory0002 and the actual notification adapter leaf. evaluate_alerts(*,actor,now) persists episode plus existing enqueue_intent atomically; no HTTP under locks. Actual stock inclusion is shared with BB14. Episodes resolve on recovery and reopen on recurrence; fingerprint changes never mutate an old event payload. GET stock/alerts and staff alert-history page preserve the fixed AlertPage schema.

Correction per frozen demo rule: recipient MUST be active non-superuser STAFF. ADMIN, DONOR, REQUESTER, inactive STAFF and superuser STAFF all fail closed. Explicit controlled recipient account UUID; no public config writer. Versioned minimum2 for32 pairs, near-expiry3days, IN_APP are educational configuration, not clinical defaults. Queue is not delivery.

Publication checks: Django system check, no migration drift, git diff --check, and8 affected alert/recipient/concurrency tests PASS on PostgreSQL18.6. Original65-test evidence remains exact source67d8892f6f38d10dd58c503ac25d3c591e368829, PostgreSQL18.6,65PASS/0skip. It is not relabelled as this publication head. Actual private Node evidence in that suite includes one failed attempt then33 acknowledgements across LOW_STOCK and NEAR_EXPIRY, persisted DeliveryAttempt and fingerprint_version2 receipts. No receipt store or token is committed.

PostgreSQL16 final inventory/concurrency acceptance will be recorded separately. All three stories remain WIP until remaining donor/shared integration, UI/load acceptance and review pass. Donor source files remain untouched; replace labelled development adapters only when Ankitha's actual facade/evaluator/callers arrive, then reconcile and verify history-v2 centrally.
