# Source and status notes

Inspected actual main a46f81817d7ee26bff7b3ce6e423785a34f951c7, existing docs/decisions.md approval records, docs/interfaces.md, docs/data-model.md, both existing OpenAPI documents, Django settings/root URLs, notification_adapter/client.py and notification-service/src/server.mjs. Also inspected the supplied adopted24-story Markdown and SRS/SAD/STP inventory/request/scheduling/reporting contract and data-model sections.

Existing main has donor/auth/screen/result/search functionality. There are no installed inventory, blood_requests, scheduling or reporting Django apps. Node authenticated delivery is still501. Notification adapter raises NotImplementedError. Shared app includes and durable delivery therefore are true Sprint2 gaps, not completed infrastructure.

The adopted source's historical Sprint3–5/owner-role/TBD planning text is retained verbatim in stories.json body; named owner, Sprint2 and points are explicit team planning overrides in the record fields/ownership table, not rewritten acceptance criteria. Exact requirements/criteria retained. Source PDF remains docs/sources/Team5_SRS_SAD_STP.pdf; do not alter its checksum or invent clinical rules/SRS IDs.

SAD examples are not automatically approved: its sample routes are versioned into /api/v1 here and same-origin session403 behavior follows current implemented policy, not old generic401 wording. Camp role conflict, quantities, shelf-life values, collection history and report semantics remain approval gates. No real notification carriers, cloud services, React or new scheduler infrastructure.
