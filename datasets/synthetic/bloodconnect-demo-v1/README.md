# BloodConnect complete synthetic mini-project dataset

**3,388 linked fictional records across15 tables.** Reference clock:16 November2026,12:00 Asia/Kolkata (`2026-11-16T06:30:00Z`). No real people, patients, hospitals, donations or observed deliveries were copied. This is the common dataset for all four teammates; balanced coverage is intentional rather than a claim about population frequencies.

Use [dataset.json](dataset.json) as the canonical source, [csv/](csv/) for spreadsheet/table imports, [data_dictionary.json](data_dictionary.json) for every column/type/owner, [expected.json](expected.json) for known answers and [manifest.json](manifest.json) for SHA256 checksums. CSV nulls are empty cells; booleans use true/false and list fields are JSON arrays. Quantities count units/bags, not millilitres. Dates are ISO dates; timestamps are aware UTC. Identifiers are reproducible UUIDv5 values; DEMO-UNIT labels are project codes, not certified ISBT128 identifiers.

| Source table | Rows | What it supplies |
| --- | ---: | --- |
|accounts|516|500 donor accounts,8 requesters,4 staff, normal/admin-negative actors; role/activity flags, fictional emails. No passwords.|
|donors|500|Account links, synthetic names, distinct drama mobiles,8 blood groups, locations, confirmed-history projection.|
|screenings|956|Historical pre-collection, current and pre-booking assessments; ages/weights, original self-reported date, confirmed snapshot, result/reasons/version/time.|
|collection_events|400|One confirmed donation per event, donor/date/time/recording staff.|
|blood_units|500|Unique code, event/donor, group/component, quantity1, collection/expiry dates, AVAILABLE/ISSUED/DISCARDED/QUARANTINED. All32 group/component pairs.|
|inventory_dispositions|50|25 explicit discards and25 quarantines, reason/actor/time. Expiry alone is not discard.|
|blood_requests|140|40 submitted,20 approved-unfulfilled,20 rejected,20 partially fulfilled approved,20 issued and20 closed; all3 urgencies.|
|issue_records|60|Actual fictional unit→request allocations, actor/time/quantity; no unit issued twice.|
|camps|12|Future/past/active/cancelled examples, names, locations, capacities and cancellation history.|
|slots|56|48 camp slots plus8 walk-ins; intervals, capacities, open/cancelled states.|
|appointments|56|Own donor/slot links, confirmed/cancelled history, booking/cancellation timestamps.|
|outbox_intents|68|56 reminders plus12 camp-cancellation notices, account recipients, deterministic event keys, timing/state examples.|
|delivery_attempts|15|12 fictional successful attempts and3 failed attempts for retry-exhaustion coverage.|
|mock_receipts|12|Explicitly fictional fixture receipts; never put these in the Node receipt directory or cite them as actual transport evidence.|
|stock_alerts|47|Low-stock and near-expiry source conditions, including zero stock, using explicit demo thresholds.|

## Known answers at the reference clock

- Dashboard: **316 usable AVAILABLE units**, **40 SUBMITTED requests**, **6 ACTIVE upcoming camps**. The stock breakdown is in expected.json; expired AVAILABLE units, quarantines, issues and discards are excluded.
- Whole history: **400 donation events,500 collected units,60 issued units,25 explicit discards**. Component units do not inflate the donation count.
- 18 October–16 November2026 inclusive: **336 donation events,436 collected units,60 issued units,22 discards**.
- Midnight boundary:59 issues fall on16 November and1 at the final microsecond of15 November. A separate empty historical range returns zero successfully.
- Scenario UUIDs name an on-time25h reminder, late23h reminder, full slot, cancelled camp, partial/issued/closed requests, maximum quantity100, inactive actor and forbidden superuser. Invalid API examples are separate from valid source rows.

## Generate and check

From repository root (Python3.13+, the existing project environment):

```powershell
python scripts/generate_synthetic_dataset.py --check
python -m unittest discover -s tests -p test_synthetic_dataset.py -v
# Reproduce the committed fixed-date exports:
python scripts/generate_synthetic_dataset.py --as-of 2026-11-16
# Optional new reference snapshot for SQL inspection; not the application's DB:
python scripts/generate_synthetic_dataset.py --check --sqlite artifacts/local/demo-reference.sqlite3
# A separate fresh-date copy for a later presentation; stable IDs, shifted dates:
python scripts/generate_synthetic_dataset.py --as-of 2026-12-01 --output artifacts/local/presentation-data
```

The generator checks foreign keys, history snapshots, eligibility before collections/bookings, event-component uniqueness, capacities, request/issue reconciliation, expiry, recipient identities and timing. A separately written SQLite query implementation independently verifies stock/dashboard and five report ranges; every CSV is checked against JSON and checksums. Reference SQLite generation refuses to overwrite an existing database.

## Load the existing application foundation now

Use a dedicated local demo database and existing normal environment setup/migrations. No secrets are included in these files.

```powershell
python backend/manage.py migrate --noinput
python backend/manage.py seed_project_demo --dry-run
python backend/manage.py seed_project_demo
```

The explicit DEBUG-only command seeds **515 non-superuser accounts,500 profiles,100 uncollected-donor assessments and80 non-issued requests**. It creates no superuser/Django staff privilege/clinical permission. Default passwords are unusable. On the first import, optionally pass `--password-env DEMO_USER_PASSWORD` with a privately set local value to enable exactly four demo logins: `admin-000`, `staff-000`, `requester-000` and `donor-450`, each at `@demo.example.test`. Existing passwords are never reset. Replays are read-only for matching records; collisions/modified records abort and roll back instead of overwriting.

This foundation subset matches models actually present on testing. The complete dataset already includes all collection/unit/issue/camp/notification data, but the importer does not manufacture unimplemented application models or create fulfilled requests without their issue history. Collected-donor assessments are deferred with collection history; derived foundation assessments for uncollected donors use the current demo rule version without rewriting source history. Teammates map the remaining CSV/JSON tables into their own actual model/services when those land. Do not run loaddata on the canonical neutral JSON; it is not a Django model fixture.

## Source and numerical choices

The field structure was checked against primary sources: [WHO](https://www.who.int/news-room/fact-sheets/detail/blood-safety-and-availability) describes component processing; [ICCBBA](https://iccbba.org/faq/) identifies donation reference, ABO/Rh, product and expiry as label information. We model donor/event/unit lineage with project-specific codes; no real donation labels or externally sourced rows are used. Django's [initial-data documentation](https://docs.djangoproject.com/en/5.2/howto/initial-data/) informed explicit local seeding rather than an automatic migration.

Emails use IANA's reserved `.test` namespace and its subdomains ([IANA registry](https://www.iana.org/assignments/special-use-domain-names/special-use-domain-names.xhtml)); mobiles use the +44 form of Ofcom's07700 900000–900999 drama range ([Ofcom](https://www.ofcom.org.uk/phones-and-broadband/phone-numbers/numbers-for-drama)). Fictional Bengaluru locations do not imply these are Indian real contacts.

Numeric settings reuse the project's existing `jackfruit/bloodconnect_synthetic_demo.json` and `backend/donors/screening_rules.json`: shelf-life fixtures35/42/365/5 days for WHOLE_BLOOD/RBC/PLASMA/PLATELETS, near-expiry3 days, low-stock threshold2, ages18–65, weight50 and gap90. They are explicit mini-project fixture parameters, not newly inferred clinical recommendations or runtime configuration changes. No real compatibility/transfusion/testing workflow is introduced.

Ownership: Yashwitha inventory/collection/disposition/alerts, Arnav issues and request17/18, Ankitha donors/scheduling, Arya19/22/23/24 and this shared dataset. Keep story PRs separate; only Arya merges. Dataset availability is settled; any remaining source adapter/model work is code, not a need for real-person data.
