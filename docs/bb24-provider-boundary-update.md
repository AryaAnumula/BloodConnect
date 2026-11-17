Publication update16November2026: Arya explicitly authorized this supporting follow-up in the
existing story PR. Earlier UNCOMMITTED/preflight wording below is a dated checkpoint, not the
current publication state. Whole-story browser/review/final-source gates still apply.

# BB24 provider-loading correction

Local16November2026 follow-up, UNCOMMITTED while Arya's no-commit instruction remains active.
An absent agreed provider/parent remains redacted503 reporting_unavailable, as does a missing or
non-callable expected function. A broken internal import or provider programming exception now
surfaces for diagnosis instead of being silently treated as unavailable implementation. Storage
and decision/config errors retain the existing redacted503 handling. No success fallback is added.

The same correction lives separately in BB23; retain identical common adapter/test files when
both story branches are composed. Five focused provider-loading tests cover missing vs broken
imports, callable shape, argument/result preservation and storage/programming errors.
All26 reporting tests passed locally using the existing Python environment with explicit SQLite
smoke settings. This is not PostgreSQL concurrency or real issue/inventory-provider evidence.

BB24 remains WIP: actual collection/discard and issue-history providers, Kolkata-boundary/source
reconciliation and final integrated/browser acceptance are still required. Keep in BB24/PR61.
