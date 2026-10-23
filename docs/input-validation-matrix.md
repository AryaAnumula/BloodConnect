# BB-11 input safety matrix — planned, not executed

| Endpoint/input | Rule/schema | Structural owner | Test/fixture | Rejected without write? | Result/evidence |
| --- | --- | --- | --- | --- | --- |
| Login | LoginInput | Ankitha | synthetic valid/invalid shape | Record actual | Not run |
| Registration | RegistrationInput, D-05 | Ankitha | normalized duplicates/forbidden role fields | Record actual | Not run |
| Screening | ScreeningInput, D-07/08 | Ankitha | malformed/boundary/null fixture | Record actual | Not run |
| Search | query schemas, D-09/12 | Yashwitha | bounded pagination/filter values | Read only | Not run |

Enforce on the server; use ORM parameterization and context-aware escaping/textContent. Blanket removal of punctuation or HTML escaping before storage is not a substitute for validation and can corrupt legitimate data. Do not duplicate tests as multiple story completions.
