# BB10 registration walkthrough and screen count

## Counting convention for team confirmation

A primary registration screen is a distinct page or required registration step where the donor supplies/validates registration information. Inline field errors,select dropdowns and an inline success message are states of the same screen,not additional screens. Login occurs after registration and is not another registration step. This is a documented counting convention proposed for team confirmation in the PR,not a fabricated historical approval.

Observed flow: /register contains all six fields;submit →201 →inline account-created message on /register. **One primary registration screen**,within the five-screen maximum under this convention. No extra wizard needed.

## Actual builder browser walkthrough

Local headless Chromium,Django development server,SQLite,synthetic example.test data,real APIs/no mocked providers:
- Registration completed at viewport390x900 and1280x900. All form input/select/button boxes were visible and within viewport;responses201;success stayed on same registration page.
- Real login →screening →saved ELIGIBLE result through served UI.
- Real authorized staff login →search UI with blood group/location/eligibility AND filters →matching real saved donor.

Machine-readable actual results and commands are in the downloadable workpack evidence. This is two Chromium viewport checks,not all possible devices,browsers,accessibility certification or a claim of approved-load performance. No real donor data was used. Do not copy builder evidence as your own local run.

## Short local handoff check

Run the devserver with local synthetic data only. At phone-size and desktop-size browser widths,register a fresh synthetic account,observe one-page success,login,screen using the returned profile UUID,load the saved result. With maintainer-provisioned non-superuser STAFF+view_donor_health,search the same donor. Confirm keyboard controls are reachable. Record actual result/screenshots without passwords/cookies/real health data. If no browser check was run locally,say NOT RUN and refer separately to builder evidence.
