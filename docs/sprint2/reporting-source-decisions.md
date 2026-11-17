# Shared reporting source decisions — BC-D037 and BC-D039

Arya explicitly requested separate BB23/BB24 feature PRs and canonical synthetic dataset integration on16 November2026. This document records only their common approved source/access rules; each feature implementation stays in its own PR. Routine decision updates are bundled under BC-D041.

BC-D037: BB23 and BB24 use separate story PRs. Reporting requires an authenticated, active, non-superuser ADMIN. Preserve approved source, date and aggregate definitions. Missing or malformed sources fail closed503, not invented totals. This does not approve a merge or whole-story acceptance.

BC-D039: Both features may explicitly select a DEBUG-only read-only canonical synthetic source with a verified manifest. Compute aggregates from one source snapshot and label the source. Default domain selectors remain separate and fail closed. Do not read expected.json totals at runtime, silently fall back, duplicate domain models or claim live-provider integration. Dataset-source support does not approve a merge or full-story acceptance.

Both independent branches carry identical wording for these shared rules so integrating one does not overwrite the other. Source: central jackfruit/PROJECT_DECISION_LOG.md BC-D037/039 and Arya's explicit16November requests. No clinical policy, role, numeric limit or API DTO changes.
