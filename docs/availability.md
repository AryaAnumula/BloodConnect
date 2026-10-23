# BB-03 availability evidence plan — incomplete

Health/live checks process reachability; health/ready checks DB connectivity only, not migrations or feature completeness. Approve D-11 before measuring the NFR-002 operating window.

Record: environment/commit, scheduled window, actual observation coverage, sample interval/method, observed downtime, planned-maintenance exclusions and missing-data treatment. Availability is (eligible operating time minus unplanned downtime) / eligible operating time; do not assume missing samples mean uptime. An empty or partial window cannot establish acceptance. No 99% result is claimed by this starter.
