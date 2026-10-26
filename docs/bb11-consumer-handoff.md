# BB-11 provider-first handoff

**Status: implemented shared provider + actual login reference; full feature acceptance pending.** Read [start here](bb11-start-here.md) and [exact owner recipes](api/bb11-feature-recipes.md). Main base is fcf58cf, existing PR #33 is e288514. No reassignment or source-criteria changes.

| Owner | Story | Required action | Existing/future dependencies |
| --- | --- | --- | --- |
| Ankitha | BB-01 | Review this small parser/serializer wiring in existing login; preserve session/audit/CSRF and run real integration | BB-02/04/05 already on main; BB-11 refresh adds real reference tests |
| Ankitha | BB-06 | Use RegistrationInputSerializer + StrictJSONParser, own atomic registration and uniqueness | D-04 password + D-05, coordinated profile model/migrations |
| Ankitha | BB-07 | Use ScreeningInputSerializer + StrictJSONParser, own approved rule evaluation/result persistence | D-07/08, real donor records and BB-12 object checks |
| Yashwitha | BB-08 | Safe result projection/reason rendering, no raw health leakage | BB-07 results, D-08, BB-12 |
| Yashwitha | BB-09 | Raw-query SearchInputSerializer + IsAuthorizedStaff, safe ORM summary, real page/filter tests | Donor records, D-08/12; Arnav gate review |
| Yashwitha | BB-10 | Approved registration fields/errors and safe DOM; inspect shared helper's 204 fix | Ankitha contract, D-05 and screen definition; mocks not end-to-end proof |
| Arnav | BB-12 | Implement reusable ownership helper/profile projection and coordinate endpoint wiring | Profile ownership schema + visibility/denial policy; don't duplicate feature controllers |
| Arnav | BB-02/04 | Review/regress sessions and role gates against real reference; no mandatory validator imports inside session helpers | Current real providers, no auth redesign |
| Arya | BB-03/05/11 | Preserve availability/audit suites, deliver provider/reference, collect combined evidence | D-10/11 operational decisions still open |

## Work sequence

1. Review this provider/reference component and actual results. AI-assisted checks are not teammate/human approval; record the real review and any waived review requirement transparently.
2. Merge the reviewed component when main's checks pass; do not label all SEC-003 acceptance complete. Do not wait for six unfinished features just to integrate a working shared provider.
3. Owners merge latest main into their own clean branch (origin/main; fork uses upstream/main), resolving shared files jointly; no rebase/force push. Keep scoped story commits and PRs.
4. Implement independent domain/UI work in parallel; complete dependent transactions/results/search/privacy when real providers exist. No mock-based integration claims.
5. Add feature-specific tests/PR revisions and decisions to [coverage matrix](input-validation-matrix.md). Arya reviews combined criteria; nobody silently rewrites others' entire modules.

Internal variable names may differ. Shared imports, named arguments, routes, JSON keys and status values must match. Change those through one coordinated contract update, not duplicate implementations. See the recipes for side effects/transactions/errors and test obligations.
