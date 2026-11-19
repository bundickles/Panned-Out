# Calendar updates after recipe changes (SCRUM-181)

The existing authenticated recipe and meal endpoints now keep calendar entries
consistent with the signed-in account's recipes. No frontend changes or new
database are required.

## Rename a recipe

Use `PUT /api/recipes/{id}` with the existing recipe form fields. The next
`GET /api/meals` resolves each meal's name from the current recipe, including
after signing out or restarting the backend. Meal IDs, dates, selected meal types,
and the scheduling-time difficulty/preparation-time fields stay unchanged.

The file still contains its original name snapshot for backward compatibility.
Calendar reads use the recipe as the source for the current name. They do not
rewrite files. A legacy meal whose recipe is already missing is omitted from the
calendar response, so old orphaned records cannot produce ghost calendar cards.

## Delete a recipe

`DELETE /api/recipes/{id}` removes all scheduled meals for that recipe in the
same account, then deletes the recipe. It returns `200 {}` only after both
writes succeed. An unknown recipe returns 404. Every other recipe and scheduled
meal remains unchanged, including another account's matching numeric recipe ID.

The change persists across restart. Removing a calendar meal alone still leaves
its recipe intact. Saved shopping lists are historical snapshots: their contents,
source references, warnings and purchased flags are not changed or deleted.
Generated shopping lists use the remaining schedule on the next request.

The existing session cookie is required. Mutations also require
`X-Panned-Out-Request: 1`. Signed-out requests return 401 and invalid request
verification returns 403, following the existing API rules.

## Storage failures and limits

Reads and writes use the existing per-account properties files and atomic file
replacement. Calendar and recipe operations share locks in recipe-then-calendar
order. If the calendar cannot be read or written, deletion fails before deleting
the recipe. If the recipe write fails after the calendar write, the backend
attempts to restore the prior calendar and returns the existing storage error:

```json
{"error":"Storage unavailable. Please try again."}
```

HTTP 500 must be shown as a failure by the caller. A rollback failure also remains
an error, never a successful delete. These are two separate files, not a database
transaction: a process/power failure between file replacements can leave the
recipe present with its meals removed. Only one server process may write a store,
as before. Full crash-atomic multi-file transactions are not implemented here.

Legacy orphan records created by older versions or manual file changes are not
silently rewritten by GET. The shopping-list generator continues to warn about
their missing recipes. New successful recipe deletions remove their calendar
records physically.

## Verification

From the repository root with the actual JDK `bin` directory on PATH:

```powershell
javac --release 11 -d backend/build backend/src/*.java backend/tests/*.java
python -m unittest discover -s tests -p test_calendar_recipe_sync_api.py -v
python -m unittest discover -s tests -p '*_api.py' -v
```

The focused checks exercise renaming, multiple scheduled copies, account privacy,
restart persistence, unchanged saved shopping lists, and storage failures. Tests
use isolated temporary data, not the team's saved recipes.
