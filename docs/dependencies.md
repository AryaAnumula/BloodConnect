# Dependency-aware implementation plan

## Phase 0: approve one base

Arya coordinates the base PR. Ankitha reviews backend/auth interfaces, Arnav database and sessions, Yashwitha frontend/client. Approve D-01–06 before parallel feature code. Everyone runs the same base commit, migrates and runs smoke tests. No member should create a separate framework project.

## Phase 1: thin login flow

BB-02 session/password interfaces + BB-01 login with seeded account → protected current-user endpoint in BB-04. BB-05 audit model/interface can be developed independently, then login/denial hooks integrate. Do not interpret endpoint numbers as strict order: BB-01/02 collaborate through fixed interfaces, not circular completed-story prerequisites.

## Phase 2: donor flow in parallel

BB-06 User/Profile + agreed registration API → BB-07 screening under approved rules → BB-08 reason/result view; BB-09 search consumes profile/result. BB-10 usability extends BB-06, not a separate duplicate registration. BB-12 object policies are designed early and integrated before exposing donor data. BB-11 prepares validation matrix and reusable primitives early; owner-specific serializer fixes and tests happen during every feature, not at the end.

BB-03 monitoring runs alongside implementation; 99% acceptance waits for the approved observation window. BB-09 performance needs the approved load, not just a fast local request.

## Mock versus wait policy

- Missing API implementation but approved contract: use a clearly labeled frontend test mock/synthetic fixture to build a page; do not claim integration or story completion.
- Missing schema or unapproved clinical/authorization policy: stop affected implementation and record a decision blocker; do not guess it.
- Missing service implementation but approved signature: unit-test consumers with an explicit mock; require integration against the merged provider before Done.
- Mock users are synthetic role fixtures only. Do not seed real donor health data.

No BB-13–24 business implementation is part of this starter. Inventory/request/camp/report dependencies remain for later planning.
