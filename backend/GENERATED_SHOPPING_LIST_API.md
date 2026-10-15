# SCRUM-57: generated shopping-list integration

This branch builds on PR #12 (calendar storage), which builds on PR #11
(authentication and private recipes, including PR #10's edit logic).
It reuses the Shopping page styling and shared Sidebar from PR #14. It does not
merge those pull requests. Merge dependencies first and coordinate the overlapping
Shopping/Sidebar files with the UI owner before merging this branch.

## Local setup

Use JDK 11+ and the Node version supported by the frontend lockfile:

```sh
javac --release 11 -d backend/build backend/src/*.java backend/tests/*.java
java -cp backend/build RecipeServer
# In another terminal:
cd frontend
npm ci
npm run dev
```

Register or sign in, create recipes with one ingredient per line, schedule them
on the Calendar, and use the Shopping List sidebar link. Vite proxies `/api` to
the backend. Production hosting must route `/api` to the same trusted backend.

## Contract

`GET /api/shopping-list?start=YYYY-MM-DD&end=YYYY-MM-DD` requires the existing
HttpOnly session cookie. Both dates are required, valid calendar dates, and
inclusive. Reversed ranges or duplicate query parameters return 400. No owner
parameter is honored: both meals and recipes always come from the signed-in
account. Responses have `Cache-Control: no-store`.

```json
{
  "start": "2026-10-01",
  "end": "2026-10-07",
  "items": [{
    "name": "1 cup rice",
    "occurrences": 2,
    "sources": [
      {"mealId": "calendar-meal-uuid", "recipeId": 1, "date": "2026-10-01", "recipeName": "Rice bowl"},
      {"mealId": "another-calendar-meal-uuid", "recipeId": 1, "date": "2026-10-07", "recipeName": "Rice bowl"}
    ]
  }],
  "warnings": []
}
```

Ingredient lines are trimmed, whitespace is collapsed, and identical lines are
grouped case-insensitively. Quantities remain literal text: `1 cup rice` and
`2 cups rice` remain separate. Occurrences count ingredient-line appearances,
including repeated lines within a recipe. Source entries correspond one-to-one
with occurrences. No unit conversion, serving scaling, aisle inference or AI
parsing occurs. Current recipe ingredients are used; meal names come from the
calendar snapshot. A deleted recipe produces a warning:

```json
{"message":"Recipe unavailable; its ingredients were omitted.","source":{"mealId":"calendar-meal-uuid","recipeId":1,"date":"2026-10-01","recipeName":"Rice bowl"}}
```

An empty result returns `items: []` and `warnings: []` (or missing-recipe warnings).
Errors return `{ "error": "message" }`: 401 for missing/expired sessions, 400 for
invalid ranges, 405 for other methods, 500 for storage failures. The frontend
uses same-origin credentials, redirects expired sessions through the established
session flow, supports retry with the selected range intact, and cancels and
ignores obsolete requests. Results are never written to localStorage. The
protected route remounts when the account changes.

This singular generation endpoint is separate from PR #13's plural
`/api/shopping-lists` saved snapshots. Saved lists and purchased-state persistence
are outside SCRUM-57. Coordinate generation ownership and this schema with Aayush;
review the reused layout with Pratap and QA scenarios with Jamiyah. Team review
and endpoint-owner agreement remain required before closing Jira.

## Review fixes included

Recipe storage now persists `lastId` atomically with the collection; deleting the
highest recipe and restarting cannot reuse its ID. Legacy files initialize the
counter from their maximum surviving ID. Historical IDs deleted before this
upgrade cannot be reconstructed; existing ambiguous meal references need manual
review. The authenticated update handler continues to use `form()`.

Authentication throttling now keys by normalized email and counts failed
credential/validation attempts, clearing failures on success. A blocked address
behind Vite no longer blocks unrelated accounts; 20 failures for the same email
still enforce the existing 15-minute window.

## Verification and QA handoff

```sh
java -cp backend/build RecipeRepositoryTest
java -cp backend/build AuthSessionTest
python3 -m unittest discover -s tests -p '*_api.py'
node --test tests/*.mjs
# Requires Python Playwright and installed Edge (or PLAYWRIGHT_CHANNEL=chrome):
python3 -m unittest discover -s tests -p 'test_*_ui.py'
cd frontend
npm run build
npm run lint
```

For QA: create two accounts. In the first, schedule a recipe twice inside a
selected range and once outside it. Verify counts and source dates, adjust the
range, try reversed dates, and test an empty range. Stop the API, change dates,
restart and Retry; dates should remain selected. Delete a scheduled recipe and
verify its warning without ingredients from a replacement recipe. Refresh and
restart the API, sign in again, and verify the list. Check logout, expired-session
redirection and a second account's empty list. Delay an old range response while
loading a new range and verify it never replaces the current results. Check
390px and desktop layouts. Browser tests cover these UI states, including a
synthetic 401 and delayed responses; Java separately verifies actual timed expiry.
