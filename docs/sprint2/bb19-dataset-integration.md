# BB19 canonical dataset integration — BC-D039

User authorizes progress using the completed dataset while retaining one story per PR. This BB19 verification remains in PR53/team/arya-bb19; no BB22/23/24 or shared-data commits are merged/cherry-picked here. Existing API/DTO/closure/model/migration code is unchanged.

```powershell
python scripts/verify_bb19_dataset.py --dataset ../BloodConnect-Synthetic-Data/datasets/synthetic/bloodconnect-demo-v1/dataset.json
```

The verifier reads the canonical JSON/manifest from shared PR62 and creates only its own disposable local SQLite database. It migrates the actual schema, creates the source's normal requester/staff actors with ephemeral credentials, logs all12 actors in through actual session/CSRF endpoints, submits80 source requests through real BB17 API and reviews40 through real BB18 API. It then verifies all80 BB19 own-list/detail records across8 requesters, including status/quantity/fulfilled0/rejection reasons, foreign/missing identical404s, anonymous denial, invalid-query handling and CSRF protection. One additional real review verifies an immediate requester refresh. Closing an unissued request is refused422, not simulated by changing a status in the database. No browser walkthrough is claimed.

Canonical source states independently verified:40 SUBMITTED,20 APPROVED-unfulfilled,20 REJECTED. After that check one submitted request is approved to demonstrate live refresh. The60 partial/full issue-linked source requests are explicitly deferred because actual BB16 IssueRecord/service is not implemented; source fixture ISSUED/CLOSED values are never copied into BloodRequest without their issue records. No issue endpoint, mutable inventory model, stock counter or fabricated fulfilment is added.

Local full canonical verifier passed:80 submissions,40 source reviews plus1 refresh review,8 requester lists/all details, source reconciliation and access/CSRF/close guards. Existing PostgreSQL regression is separately run on the actual committed branch; verification evidence and remaining acceptance limits are recorded with the PR. PR62's supported foundation seeder is also available after Arya personally integrates that shared-data PR; this verifier intentionally needs no import/merge of its code.

Full BB19 issue→partial/final tracking→close acceptance still depends on Arnav16 and Yashwitha's real allocation provider. Current unblocked submit/review/tracking integration is demonstrated using the dataset. Only Arya merges; existing attribution/manual CI preserved.

## Exact committed-source regression

Source95efe9563f1dee1f776b076a5f43b61c5ea8db18 passed [manual PostgreSQL16 run43843864066](https://github.com/AryaAnumula/BloodConnect/actions/runs/43843864066):416 Django/91 Node/29 availability, zero skips, clean migration/system/repository checks. [Cross-story evidence and limits](arya-dataset-integration-verification.md) distinguish actual canonical file/API/private transport verification from PostgreSQL and browser scope. Later documentation-only commits retain tested runtime/test/config source.
