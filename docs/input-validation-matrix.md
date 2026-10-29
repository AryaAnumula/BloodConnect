# BB11 evidence register — current implemented endpoints

Adopted SEC003 criteria remain authoritative. This independent follow-up runs without BB08/09/10 master. Linked evidence is not counted twice as new feature work.

| Surface | Actual provider/evidence | Status |
| --- | --- | --- |
| Login | LoginInputSerializer,StrictJSONParser;accounts.tests.test_login;core.tests.test_login_input_integration;core.tests.test_bb11_reference_flow | real auth/session/audit and strict ingress |
| Registration | RegistrationInputSerializer,atomic register_donor;accounts.tests.test_registration;core.tests.test_sprint1_input_integration | real fields/types/lengths/privilege/no-write/duplicate-contact checks |
| Screening | ScreeningInputSerializer,BB07 service/config/history;donors.tests.test_screening_api;test_screening_service;test_evaluation;core.tests.test_sprint1_input_integration | real direct-API invalid/future/duplicate/nonfinite input,no invalid assessment save |
| Profile | BB12 shared role/object helpers,allowlisted response;donors.tests.test_profile_api;accounts.tests.test_donor_health_policy | real own/staff access,hidden404,superuser denial |
| Audit | audit.tests.test_events;test_denials;test_merged_endpoints | metadata only;recording/failure redaction;no domain payload persisted |
| Safe frontend sinks | tests/frontend-input-safety.test.mjs;frontend-eligibility.test.mjs;frontend-search-behavior.test.mjs | controlled DOM/Node checks,not a native-browser security proof |
| Search filters | SearchInputSerializer component tests in core.tests.test_validation | provider exists;actual BB09 endpoint adoption PENDING |
| Saved-result projection | shared model/config/policy exist,BB08 API still stub | actual BB08 integration PENDING |
| Registration UI | current real form exists | BB10 field-error/submit-state follow-up separate |

Wrong or malformed requests are validated before domain writes;security denial audit entries are intentional evidence,not corrupt domain writes. ORM literal handling and context-appropriate text rendering are used,not blanket stripping of valid punctuation. No schema,clinical threshold,password rule or requirement ID is invented.

Recorded D04/D05/D07/D08 approvals in decisions.md are retained. D10 operational access/retention and NFR performance/availability are separate. Remaining BB08/09 checks must be added when their real endpoints land;this does not falsely mark every SEC003 criterion completed for future features. Record actual local counts/engine/NOT RUN in PR;don't copy builder evidence as Windows results.
