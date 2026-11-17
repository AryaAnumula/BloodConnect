# Branch coverage report

Measured on `testing` commit `d6e377d3ba361730841f51e0fe48720cce0c056f`, PostgreSQL 16.16, coverage.py 7.17.3. The measured run executed the broad application suites while omitting the eight fixed-size 515-account demo-seeder tests at Arya's request to reduce account usage. Individual small role fixtures remain; this is not an exact 25% representative account sample. Tests, migrations and explicit acceptance modules are omitted from the measured backend production-source denominator. Frontend JavaScript is not measured. No account or production module is hidden from this backend coverage denominator. The result is not a full suite and contains two errors and eight skips; see unit and validation reports.

**770 / 972 = 79.22%**; 104 partially covered source lines. This is **below 85%**; more meaningful branch tests and rerunning the completed integrated source are needed.

| Area | Covered | Branch destinations | Coverage |
| --- | ---: | ---: | ---: |
| accounts | 35 | 48 | 72.92% |
| audit | 4 | 4 | 100.00% |
| blood_requests | 143 | 144 | 99.31% |
| config | 2 | 6 | 33.33% |
| core | 137 | 230 | 59.57% |
| donors | 80 | 84 | 95.24% |
| inventory | 150 | 196 | 76.53% |
| manage.py | 0 | 2 | 0.00% |
| notification_adapter | 105 | 132 | 79.55% |
| reporting | 34 | 36 | 94.44% |
| scheduling | 80 | 90 | 88.89% |

Full machine-readable coverage is `coverage.json.gz`.
