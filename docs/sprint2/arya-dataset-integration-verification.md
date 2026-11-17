# Arya dataset integration: exact-source verification

All stories retain separate PRs and consume the shared PR62 dataset as input. No branch merge or cherry-pick, no automatic CI, no migration or contributor/identity change. Only Arya merges.

| Story/PR | Exact code source | Existing manual PostgreSQL16 run | Results |
| --- | --- | --- | --- |
|BB19/PR53|95efe9563f1dee1f776b076a5f43b61c5ea8db18|[43843864066](https://github.com/AryaAnumula/BloodConnect/actions/runs/43843864066)|416 Django in76.459s, 91 Node/frontend,29 availability; zero skips; clean migrations/system/repository checks.|
|BB22/PR59|ceaa5388aad0c096aa7e731f17d9c6ccb1671829|[43843352760](https://github.com/AryaAnumula/BloodConnect/actions/runs/43843352760)|651 Django in150.999s, 112 Node/frontend,29 availability; zero skips; clean migrations/system/repository checks.|
|BB23/PR60|a9e9639cf7643d133e531c3474be044309126513|[43841718408](https://github.com/AryaAnumula/BloodConnect/actions/runs/43841718408)|410 Django in74.874s, 81 Node/frontend,29 availability; zero skips; clean migrations/system/repository checks.|
|BB24/PR61|d5f101443a9adb69cb7248c9a337e8540d73e4db|[43841741993](https://github.com/AryaAnumula/BloodConnect/actions/runs/43841741993)|411 Django in59.762s, 80 Node/frontend,29 availability; zero skips; clean migrations/system/repository checks.|

## Full canonical source demonstrations

- BB19:80 actual API submissions,40 source reviews plus1 live review/refresh,8 requester own-lists/all details; source states40 SUBMITTED/20 APPROVED-unfulfilled/20 REJECTED verified. Foreign/missing404, session/query/CSRF/close guards pass.60 issue-linked source rows are deferred, not fabricated.
- BB22: fresh domain screenings/camps/slots/bookings from canonical donor identities; actual bounded dispatch to private Node produced2 persisted receipts/2 DeliveryAttempts. On-time receipt timing_met=true, late=false; third donor-cancelled booking no receipt. No fixture DELIVERED states/receipts imported.
- BB23: authenticated canonical file→API returns316 usable units/40 pending requests/6 upcoming camps, matching expected.json; source header, visible snapshot label, invalid query and wrong-role/session guards pass.
- BB24: authenticated canonical file→API reconciles all5 expected date ranges; whole history400 events/500 units/60 issues/25 discards; last30days336/436/60/22; empty/midnight boundaries pass.

These verifiers use disposable local SQLite databases and actual Django session/CSRF/API paths; BB22 also uses actual private HTTP to Node. This is separate from the exact-source PostgreSQL regression above. No browser walkthrough or real SMS/email/inbox claim. Source actor setup does not touch existing application data. Expected.json is used only by verification, never runtime aggregation.

Reporting synthetic mode is explicitly selected and DEBUG-only. Default domain selectors stay separate and fail closed; no silent fallback or competing mutable operational models. BB23/24 common reader/page/helper/config files are byte-identical; each branch lacks the other feature implementation. Later documentation-only commits preserve the tested runtime/test/config source.

Remaining acceptance: BB19 actual BB16 issue→partial/final tracking→close; BB22 actual camp-wide cancellation service by Ankitha and coordinated donor-history initialization; future live-domain inventory/issue/camp selectors; independent review/permitted walkthrough. These do not prevent the explicit mini-project synthetic dashboard/report mode from returning computed results now.
