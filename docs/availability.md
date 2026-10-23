# BB-03 — availability tooling implemented; operational acceptance pending

Owner: Anumula Arya. Supporting reviewer: Arnav. Source: **NFR-002** and the adopted BB-03 story. No new requirement IDs, routes, deployment services or dependencies are introduced.

## Scope and current status

Existing public read-only endpoints are unchanged:

| Endpoint | Meaning | Responses |
| --- | --- | --- |
| GET /api/v1/health/live | Django process answers; does not query the database | 200 process_only |
| GET /api/v1/health/ready | Database SELECT 1 connectivity probe | 200 ready or redacted 503 not_ready |

Readiness does not prove applied migrations, working donor services, clinical correctness or a complete login. Liveness must remain available when the DB is unavailable. Public responses contain no database exception details or credentials.

`scripts/measure_availability.py` now collects bounded readiness observations and produces a protocol-bound report. It is a **proposed sampled measurement method awaiting D-11 approval**, not a continuous user-journey monitor or automatic story acceptance mechanism. Health checks and synthetic tests cannot demonstrate 99% operational availability.

## Before acceptance collection: agree D-11

Arya and Arnav must record actual approval of:

1. Named environment, actual deployed Git revision, readiness URL and observer location.
2. Offset-aware start/end timestamps and timezone; use the real future operating window, not example dates. Source requirement does not specify its duration: agree a representative duration with the team/course assessor.
3. Sampling interval, timeout, bucket-weighted calculation, and the fact that point sampling can miss outages between checks.
4. Planned-maintenance intervals, approved **before** the window. Do not relabel observed downtime as maintenance after the fact.
5. Missing/late observations, monitoring interruption, evidence review and the 99% target.

The example's 10-second interval and 2-second timeout are illustrative only, not team approval. `config/decisions.example.json` is still unapproved; do not flip its flags merely to make a CLI run. A protocol includes an approval reference; the script cannot verify the person/approval/deployment claim externally. An independent reviewer must do so.

## Prepare local protocol — Windows PowerShell

From your actual repository root (on team/arya while implementing):

```powershell
New-Item -ItemType Directory -Force artifacts/local/bb03
if (!(Test-Path artifacts/local/bb03/protocol.json)) { Copy-Item config/availability.protocol.example.json artifacts/local/bb03/protocol.json }
```

Edit that local JSON without committing it. Fill `protocol_id`, `environment_name`, `source_revision` (actual deployed 40-character commit SHA), `approved_by`, `approved_at`, `approval_reference`, the real window, and preapproved maintenance. Approval must predate the window. Do not fabricate these values. `git rev-parse HEAD` identifies a checkout; verify that it actually matches the observed deployment. Do not put secrets or donor details into the protocol.

`artifacts/local/` is already Git- and Docker-ignored. No existing ignore rules, including `files/`, need to be removed. Keep private prompt packs ignored. Do not use the tracked example as a real approval record.

Validate the example safely, without writing observations or sending requests:

```powershell
python scripts/measure_availability.py --protocol config/availability.protocol.example.json --output artifacts/local/bb03/example --dry-run
```

Expected: valid shape, approval false, observation_complete false, story_complete false.

## Run observations

Start the application using the current README (Docker local development is one proposed environment). The collector is standard-library Python and can run separately on the host; it does not need a database password or Django signing key. Run it BEFORE the approved window starts:

```powershell
python scripts/measure_availability.py --protocol artifacts/local/bb03/protocol.json --url http://localhost:8000/api/v1/health/ready --output artifacts/local/bb03/evidence
```

Keep application, database and observer running for the full approved window. Do not change the protocol, target URL, deployment revision or approved maintenance during a run. Any actual deployment change requires a reviewed new protocol/run, not relabeling old observations. An external/independent observer is preferable for deployment acceptance; a monitor inside the same stopped container loses coverage and cannot prove uptime.

A limited tooling smoke check may use `--max-samples 2` with its own clearly labeled approved test protocol/output folder. It forces sampled_threshold_met false and cannot establish full-window acceptance. Unit-test approval strings are synthetic, never actual team approval.

Ctrl+C writes an incomplete report when interruption occurs during collection. Resuming uses the same command and output directory; it does not recreate missing past samples. If the process crashes, observations are flushed as appended; run the read-only summary after investigating the crash. A stale collector.lock must be reviewed: verify no collector is running before removing ONLY that lock. Never delete evidence to make coverage appear complete. Malformed/truncated evidence stops reporting for manual reconciliation.

Read-only summary (use the SAME URL and protocol as collection):

```powershell
python scripts/measure_availability.py --protocol artifacts/local/bb03/protocol.json --url http://localhost:8000/api/v1/health/ready --output artifacts/local/bb03/evidence --summarize-only
```

Exit 0 means the requested tooling action ran, **not** story acceptance. Exit 2 means invalid protocol/evidence/access; exit 130 indicates collection interruption. A dry-run does not create an evidence directory. Approval-less real collection is refused. Summary requires an existing bound session.

## Evidence and calculation

The output directory contains:

- `session.json`: protocol SHA-256, probe URL, environment, supplied deployed revision and collector start time. A changed protocol/URL/environment/revision cannot silently resume into the same directory.
- `observations.jsonl`: scheduled/observed timestamps, readiness boolean, HTTP status. No raw response body, credential, token, health data or recipient is stored. Status 0 means transport/format failure. Redirects are not followed.
- `report.json`: sampled durations, missing coverage, percentage, environment/revision and review warnings. Atomic report replacement does not alter the observation history.

Hashing detects accidental protocol mismatch; it is not a digital signature or proof observations were never manually edited. Preserve original files and disclose manual reconciliation. Approval IDs/environment/revision are user-supplied claims requiring independent review.

For each scheduled bucket, eligible duration = bucket duration minus approved maintenance overlap. Maintenance overlaps are merged/clipped so time is excluded once. The scheduled readiness sample estimates that bucket's eligible time. Unavailable samples count as sampled downtime; missing, late or unfinished future buckets count as UNKNOWN, never uptime. Partial final buckets use their actual duration.

`sampled_availability_percent = sampled_available_seconds / eligible_seconds * 100`

Unknown time remains in the denominator. `coverage_percent = (eligible_seconds - unknown_seconds) / eligible_seconds * 100`. Zero eligible duration gives null percentages and cannot pass. The bucket estimate is not a mathematical bound on continuous real-world availability; brief outages can occur between probes. These semantics must be explicitly approved as the measurement method, or replaced with an approved method before claiming NFR-002 acceptance.

`sampled_threshold_met` requires elapsed window, positive eligible duration, full eligible coverage, supplied pre-window approval/deployment fields, and >=99% under this sampled method. A persisted tooling/interruption-history flag prevents limited/interrupted runs from later being promoted to a pass merely by re-summarizing. Use a separate properly approved full run for acceptance. **story_complete always remains false**: independent source-criteria, protocol, deployment and evidence review is still required.

## Checks and handoff

```powershell
python -m unittest discover -s tests -p test_availability.py -v
```

For Django checks use the current configured environment, or Docker:

```powershell
docker compose run --rm web python backend/manage.py test core.tests accounts.tests
docker compose run --rm web python scripts/validate_repository.py
docker compose run --rm web python backend/manage.py makemigrations --check --dry-run
```

`sh scripts/check.sh` also includes the standalone monitor tests when a POSIX shell and the documented dependencies are available. No CI trigger/dependency/API/schema changes were made. Use [operational review template](availability-review-template.md) for the real evidence review and [BB-03 handoff](handoffs/BB-03.md) for this implementation's actual checks/limits. Ask Arnav to review; do not mark BB-03 Done just because its tooling PR merges.
