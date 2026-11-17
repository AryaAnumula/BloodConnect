# Code coverage report — statements / lines

Measured on `testing` commit `d6e377d3ba361730841f51e0fe48720cce0c056f`, PostgreSQL 16.16, coverage.py 7.17.3. The measured run executed the broad application suites while omitting the eight fixed-size 515-account demo-seeder tests at Arya's request to reduce account usage. Individual small role fixtures remain; this is not an exact 25% representative account sample. Tests, migrations and explicit acceptance modules are omitted from the measured backend production-source denominator. Frontend JavaScript is not measured. No account or production module is hidden from this backend coverage denominator. The result is not a full suite and contains two errors and eight skips; see unit and validation reports.

**3729 / 4162 = 89.60%**. This exceeds the requested 85% line target for this reduced run, but the suite is not green and full-plan coverage has not been established.

| Area | Covered | Statements | Coverage |
| --- | ---: | ---: | ---: |
| accounts | 238 | 263 | 90.49% |
| audit | 52 | 52 | 100.00% |
| blood_requests | 675 | 678 | 99.56% |
| config | 45 | 53 | 84.91% |
| core | 512 | 725 | 70.62% |
| donors | 378 | 393 | 96.18% |
| inventory | 700 | 816 | 85.78% |
| manage.py | 0 | 6 | 0.00% |
| notification_adapter | 365 | 382 | 95.55% |
| reporting | 234 | 244 | 95.90% |
| scheduling | 530 | 550 | 96.36% |

Full machine-readable coverage is `coverage.json.gz`.
