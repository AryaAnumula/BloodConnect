# BB-11 provider-first handoff: feature owners consume the shared contracts

## Workflow and status

Arya delivers and tests a shared validation provider independently of unfinished feature implementations. Feature owners integrate that provider into their own stories. They do not wait for Arya to rewrite their controllers or finish their feature work. This is an ownership/handoff clarification, not a change to the adopted BB-11 acceptance criteria or a claim that all of SEC-003 has passed.

Review the provider PR first. After actual contract/policy approvals and independent review, merge the reviewed shared component into main as a prerequisite; feature stories then merge main into their branches and consume it. Main must still pass its agreed checks. No need to wait until registration/screening/search are finished merely to review this component. Do not merge an unreviewed/unapproved contract or unfinished authentication code just to satisfy a dependency.

Unapproved D-04/05/07/08/09 behavior stays proposed. Basic reusable validation can be reviewed independently; adopting provisional field/clinical/authorization conventions still requires the appropriate decision. This plan changes work order, not approval authority.

## Arya's bounded implementation handoff

- Own shared field validators, StrictInputSerializer and validate_shared_input signature.
- Own candidate input schemas and opt-in StrictJSONParser, documented invariants and component tests.
- Supply consumer examples/one-file login candidate patch, integration tests and traceability links.
- Record exact revision, tests, limitations and approvals. Keep provider code/contracts consistent.
- Coordinate cross-feature acceptance evidence and review; do not silently complete teammates' endpoints.

This provider implementation can be handed off as implemented/tested after the checks pass. The BB-11 issue remains acceptance pending until adopted criteria are demonstrated on the relevant real features. Do not rename the adopted story to make component tests stand in for integrated security evidence.

## Directly affected stories: feature-owned changes required

| Story | Owner | Required adoption/change |
| --- | --- | --- |
| BB-01 login | Ankitha | Use LoginInputSerializer and StrictJSONParser on raw input before authentication; preserve exact passwords, current CSRF/session/audit contracts. Review optional-login-integration patch against CURRENT code; do not blindly overwrite. Add actual invalid-input/no-session-or-account-change tests. |
| BB-06 registration | Ankitha; Arnav reviews DB constraints | Use RegistrationInputSerializer after D-04/05 approval before register_donor; reject privilege/unknown fields. Own normalized DB uniqueness, approved password policy and atomic User/Profile creation; add invalid/duplicate/no-partial-write tests. |
| BB-07 screening | Ankitha | Use ScreeningInputSerializer and StrictJSONParser after field/policy review before screening writes. Own approved clinical rules, authorization, first-time/freshness semantics; test malformed input cannot create a result. Shape validation is not clinical eligibility. |
| BB-09 donor search | Yashwitha | Use SearchInputSerializer on raw request.query_params; handle repeated/unknown filters and bounded pagination. Own approved state/freshness/access policy, parameterized ORM filters and safe projection; add actual endpoint query/access/boundary tests. |
| BB-10 registration UI | Yashwitha, coordinated with Ankitha | Align client fields and displayed errors to the approved registration contract, render untrusted values through textContent/escaped templates. Client checks are convenience only; bypass them in direct API tests. Do not fork the registration API or server validation rules. |

## Secondary regression/review only: no automatic rewrite required

| Story | Owner | What to verify |
| --- | --- | --- |
| BB-02 sessions | Arnav | Login input validation must not break session creation/rotation/expiry/logout or CSRF. No validator import is needed inside session helpers just to satisfy this handoff. Known session-success/audit-failure compensation remains a separate integration issue. |
| BB-04 authorization | Arnav | Validation must not bypass role/object checks or enable client-selected privilege fields. Preserve feature authorization; no duplicate permission implementation. |
| BB-05 audit | Arya, Ankitha caller hooks | Keep one safe event per required denial/failed credential attempt, never log raw input. Malformed-input rejection before credential verification is not automatically a failed-credential event; approve event policy. No rewrite of the writer is required just for BB11 adoption. |
| BB-08 eligibility result UI | Yashwitha | Verify returned reasons/untrusted values use safe text rendering and permitted projections; not a new screening-input implementation. |
| BB-12 donor privacy | Arnav | Safe validation does not replace ownership/clinical authorization or allowed-field projections. Verify regression tests on integrated endpoints. |

BB-03 has no direct change for this handoff. Its monitoring test suite must simply be preserved when shared runners merge. Not every secondary story needs a code change: its owner reviews/tests and changes code only if the check reveals a defect.

## Agreed shared imports to consume (candidate until reviewed)

```python
from core.input_schemas import (
    LoginInputSerializer, RegistrationInputSerializer,
    ScreeningInputSerializer, SearchInputSerializer,
)
from core.parsers import StrictJSONParser
from core.validation import validate_shared_input
```

For an existing JSON feature view, retain its auth/CSRF/role gates, opt into StrictJSONParser, validate raw request.data, then call the existing service with serializer.validated_data. Search validates raw request.query_params. Do not prefilter unknown keys away, log credentials or copy implementations into each app. Only the endpoint owner changes that view after review.

Serializer declarations and field shapes are in docs/input-validation-matrix.md and current OpenAPI. If the owner's current approved contract differs, coordinate one shared change with Arya; do not silently rename fields or add a competing schema. No generic clinical rule, database invariant or permission is supplied by these providers.

## Branch and evidence handoff

1. Arya opens a separate provider PR on story/arya-bb11; reviewers inspect contracts and real component test results.
2. Record actual decisions/review, then merge the reviewed shared component to main when ready; the complete story is still acceptance pending.
3. With a clean member branch, each feature owner runs git fetch origin then git merge origin/main (no force push/rebase). Resolve shared file overlaps with owners.
4. Owner adopts the provider in the directly affected story, runs feature-specific positive/negative/boundary/transaction/access tests, and commits on their own branch.
5. Link owner test modules, feature commit/PR, actual engine and evidence in docs/input-validation-matrix.md. Do not count the same shared test as multiple completed stories.
6. Arya reviews the combined evidence against the unchanged BB-11 criteria. Only then consider full BB-11 acceptance; PostgreSQL/browser/CI and unresolved feature coverage are not silently waived.

Owners may implement independent non-validation parts while a reviewed provider PR is pending. For validation integration, use the agreed provider revision or a clearly identified test-only contract-compatible mock; do not paste this whole ZIP into their repo or claim mock success proves integration. Shared file changes/dependencies still require coordination.
