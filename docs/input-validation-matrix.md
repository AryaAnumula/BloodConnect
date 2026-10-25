# BB-11 input safety matrix — candidate and evidence boundaries

Approved source requirement: SEC-003. Exact adopted BB-11 story/criteria are unchanged in `docs/sources/adopted-sprint1-stories.md`. The source planning paragraph says Sprint 2 proposed; current team assignment brings BB-11 into the Sprint-1 work plan, not a change to the source requirement or proof of capacity.

Primary: Anumula Arya. Supporting reviewers: Ankitha and Arnav for server-side validation/integration. Yashwitha owns search/frontend consumers. No other member's runtime file is overwritten by the base BB-11 patch.

| Endpoint/input | Provider and candidate rule | Owner / decision gate | Tests and evidence boundary | Runtime status on base |
| --- | --- | --- | --- | --- |
| Login POST /api/v1/auth/login | LoginInputSerializer; object, email string/format/max254, password nonempty string unchanged; no unknown keys | Ankitha; D-03/04/05 and owner review | core.tests.test_validation; optional core.tests.test_login_input_integration uses actual endpoint only once wired | Original 501 stub; optional separate owner-reviewed PR30 integration patch supplied outside repo |
| Registration POST /api/v1/auth/register | RegistrationInputSerializer; current proposed full_name/location 1..120, email max254, E.164 mobile, password min12, blood-group enum | Ankitha + Arnav; D-04/05 | Component tests only; actual duplicate/atomic registration tests belong to BB-06 | UNWIRED; no User/Profile schema or registration writes implemented |
| Screening POST /api/v1/donors/{donor_id}/eligibility | ScreeningInputSerializer; JSON integer age>=0; decimal-string weight; required nullable ISO date | Ankitha; D-07/08/09 | Type/format/null/calendar tests; NOT clinical eligibility tests | UNWIRED; no clinical range, first-time or freshness rule guessed |
| Search GET /api/v1/donors | SearchInputSerializer; proposed blood/eligibility enums, optional location<=120, page>=1, page_size1..100, reject repeated query values | Yashwitha + Arnav; D-08/09/12 | Component tests for QueryDict, encoded +, boundaries and unknown fields; NOT real database filtering/access/performance | UNWIRED; real search tests pending |
| JSON decoding | core.parsers.StrictJSONParser; duplicate keys (including nested), malformed syntax, nonfinite numbers/invalid encoding and decoder-reported recursion failures rejected generically | Feature endpoint owner; opt in per endpoint | core.tests.test_validation.StrictParserTests and test-only direct-request probe | NOT globally enabled; optional login patch opts in |
| Shared text renderer | Existing showStatus uses textContent | Yashwitha; no shared client change in this patch | tests/frontend-input-safety.test.mjs checks actual helper with a controlled DOM sink | Existing helper unchanged; real-browser and future stored-value flows pending |

## Implemented shared providers

`validate_shared_input(*, value, rule_name)` keeps the existing signature. Rules: email, mobile, full_name, location. Returns validated value; raises DRF ValidationError for invalid/unknown rules. Does not access DB, create audit events, authorize actors or own transactions. Email/mobile normalization reflect existing D-05 proposals, not clinical rules. No destructive SQL/HTML stripping, no blanket escaping before storage. Do not invent stricter clinical/field rules without review.

`StrictInputSerializer` rejects non-objects, unknown/read-only keys and repeated QueryDict values without echoing attacker-controlled keys/values. Numeric/bool inputs cannot become strings implicitly. Passwords are write-only in representation and are not trimmed, lowercased or logged. Callers must never log serializer.initial_data/validated_data (which necessarily contain the submitted password during validation). Error fields are controlled rule messages.

`StrictJSONParser` is opt-in, compatible with JSON media type. A serializer cannot recover duplicate keys discarded by a normal JSON decoder; use the parser as well. No parser/settings/global middleware has been silently added to all endpoints. The decoder recursion-failure branch uses explicit failure injection because supported Python JSON decoders differ; no fixed nesting-depth threshold is claimed. Body-size limits remain Django settings; no arbitrary new per-field/password/hash-cost limit is invented. D-04 should resolve any maximum password/hash-cost policy before final production review.

## Required wiring sequence (feature owner)

1. Inspect current approved API/schema/policy and existing serializer; reuse/extend the provider or agree one owner before replacing it. Do not create duplicate normalization/permission implementations.
2. Keep CSRF/auth/role/object gates. Use StrictJSONParser on JSON ingress; pass raw request.data to the serializer, not a prefiltered dict that hides unknown keys. Search uses raw request.query_params.
3. `serializer.is_valid(raise_exception=True)` BEFORE calling any service that mutates state. Call service with validated_data only. Preserve field names/function contracts.
4. Registration owner enforces DB-backed normalized uniqueness, atomic account/profile creation and approved Django password policy separately. This provider does not replace those invariants.
5. Screening owner invokes approved clinical policy after shape validation; no eligibility result from malformed input. Search owner uses allowlisted filters/parameterized ORM, permissions and minimal safe projections. Raw SQL string interpolation is prohibited.
6. Use Django template autoescaping/textContent for untrusted strings in HTML text. No innerHTML, safe-marking, JS-template interpolation or unvalidated URL navigation for submitted values. Safe handling is contextual; textContent does not sanitize a URL or CSS context.
7. Keep errors in the existing envelope; never return raw database/parser exceptions or input values. Validation does not prevent every downstream business/database exception: feature owners need safe exception translation.
8. Add actual endpoint tests proving invalid requests cannot alter protected domain records. Security audit entries for genuine failed credentials are intentional metadata, not corrupt domain changes. Do not suppress SEC-006 audit behavior to make no-write assertions pass.

## Test-only probes — NOT new business functionality

`core.tests.test_validation_api` enables a tiny synthetic User.first_name write probe ONLY through an overridden test URLconf. No runtime URL maps to it. It proves validation-before-write ordering and parameterized ORM behavior in that bounded test. It does not implement donor registration, expose a new profile endpoint or prove every future query safe. Authentication is force-injected in this probe only, not in conditional real-login tests.

SQL-like and script-like name fixtures are synthetic local data. An ORM test keeps the SQL-like string literal and preserves the table; a JSON response is not executable HTML. The Node test calls the actual existing showStatus helper and rejects use of an HTML sink with a controlled DOM object. A local headless-browser attempt timed out in the build environment, so real-browser execution is NOT certified. Future rendered/stored-value end-to-end tests remain required.

## Acceptance status — do not count component tests as full endpoints

| Exact adopted criterion (summary only; source is authoritative) | Status |
| --- | --- |
| Agreed server-side types/lengths/formats/values on implemented fields | Candidate providers tested; current main endpoints remain stubs; owner wiring/decisions pending |
| Malformed input rejected before invalid state change | Test-only write probe verified; conditional actual login tests included; registration/screening transactions pending |
| Injection/script fixtures cannot execute SQL/browser script | Parameterized ORM probe and existing textContent sink unit tested; complete feature/browser flows NOT certified |
| Direct API bypass cannot bypass validation | Direct-request test probe; actual login only after optional patch; other real feature endpoints pending |
| Errors exclude internals/secrets/health data | Controlled parser/validator errors tested; future business/DB error paths must be tested by owners |
| Feature tests linked, not duplicated/counting twice | Matrix links exact modules; no invented formal SRS/test IDs, no reclassification of existing tests as new independent story completion |

D-04/05/07/08/09 decisions remain proposed in current main. Do not mark approvals or all acceptance criteria complete from this patch. See docs/handoffs/BB-11.md.

## Provider-first ownership clarification

Arya's shared provider is independently reviewable/testable. BB-01/06/07/09 feature owners consume it in their own code; BB-10 aligns its UI with the approved registration contract. BB-02/04/05/08/12 are regression/review touchpoints, not mandatory rewrites. BB-03 has no direct validation change. See docs/bb11-consumer-handoff.md for exact responsibilities and adoption order. Provider delivery does not mean all real-feature acceptance criteria have passed.
