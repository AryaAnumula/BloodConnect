# Synthetic dataset verification —16 November2026

Independent shared-data [draft PR62](https://github.com/AryaAnumula/BloodConnect/pull/62), team/arya-synthetic-dataset directly from testing97614c8. No existing feature PRs combined. Only Arya merges.

Exact implementation118fd35f0a72592f5b43f709dab7ef29a6e9adb3 passed existing manually dispatched PostgreSQL16 [run43837657175](https://github.com/AryaAnumula/BloodConnect/actions/runs/43837657175):

| Check | Result |
| --- | --- |
|Django application regression, including7 new actual foundation importer tests|399 passed in99.199s; zero skips.|
|Node/frontend regression|76 passed; zero skips.|
|Availability-tool tests|29 passed.|
|Dataset integrity/mutation/export/reconciliation tests|14 passed.|
|Committed JSON/CSV/checksum and independent SQLite query check|3,388 records/15 tables validated; dashboard and5 report ranges reconcile.|
|Migrations/system/repository checks|No changes, no system issues; repository validator passes.|
|Local general and Sprint2 contract validators|Both pass; Windows general validator invoked with -X utf8.|

Local targeted importer7/7, dataset14/14 and CSV/JSON/manifest checks also passed. A separate new local reference SQLite snapshot was created under artifacts/local; it is not the application DB and is not committed. Repeat generation yields identical exports, and a leap-day date-rebased dataset passes integrity and SQL reconciliation.

The importer actually creates515 ordinary accounts,500 profiles,100 uncollected-donor assessments and80 non-issued requests on the present schema. Tests prove read-only matching replay, no superuser/clinical grants, four optional local logins, password omission, rollback on a late uniqueness collision and preservation of modified existing records. No fixture issue history is silently replaced with fulfilled totals; no Node receipt store is populated from fictional receipt rows.

Data scope is complete for the project's entities. Future actual inventory/issue/scheduling source loaders/selectors remain implementation work by the named owners, not a need for real people or missing sample values. This dataset does not claim browser acceptance, live delivery or clinical suitability. Numerical rules are existing explicit educational fixtures, not runtime changes. Later evidence-only documentation commits retain identical runtime/test/config/dataset source to118fd35. Commits use Arya's existing identity; main/testing and all story heads unchanged. No automatic CI or merge.
