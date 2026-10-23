# Saved shopping lists (SCRUM-59 and SCRUM-60)

This backend stores a supplied shopping-list snapshot and updates purchased status.
It does **not** generate ingredients, combine items, or add shopping-list UI.
It builds on the account/session and calendar code in PRs #11 and #12.

## Integration dependency

PR #15's shopping page calls the **singular**
`GET /api/shopping-list?start=...&end=...` endpoint supplied by PR #16 to generate
current ingredients from calendar meals. PR #13 supplies the **plural**
`/api/shopping-lists` endpoints for saved snapshots and purchased status.
Generating a list does not save it, and fetching a saved snapshot does not
regenerate it. These routes must remain distinct in frontend helpers.

The fetched PR #15 page currently supports generation only; it does not call the
saved-list endpoints. Saving and persistent checkboxes still need frontend wiring.
The following is the handoff for that work, not a claim that the page already
implements it. Merge the account/calendar and generation dependencies before
checking the full page flow.

### Wiring generation to saved lists

1. Generate with the singular GET endpoint and keep its `start`, `end`, `items`,
   and `warnings` response. Keep warnings visible, including warning-only results.
2. On an explicit Save action, encode that response using the mapping below and
   POST to plural `/api/shopping-lists`. A successful 201 returns the saved list
   and item UUIDs. Switch the page to this returned snapshot for saved-state work.
3. Restore saved lists using plural GET, and update checkboxes with the plural
   PATCH endpoint and returned list/item UUIDs. Generated items have no saved
   UUIDs, so they cannot be used directly for purchased-status updates.
4. If saving returns 409 because calendar sources changed, regenerate and let the
   user review the result before saving again. Do not silently discard warnings.
   A new POST creates another snapshot; do not automatically repeat it after an
   uncertain network failure. Keep the existing 401/session-expired handling.

| Generated response field (PR #15/#16) | Saved-list form field (PR #13) |
| --- | --- |
| `start`, `end` | `start`, `end` |
| `items.length` | `itemCount` |
| `items[i].name` | `item.i.text` (name becomes text) |
| `items[i].occurrences` | `item.i.occurrences` |
| `items[i].sources.length` | `item.i.sourceCount` |
| `items[i].sources[j].mealId`, `.recipeId` | `item.i.source.j.mealId`, `.recipeId` |
| `warnings.length` | `warningCount` |
| `warnings[i].message` | `warning.i.message` |
| `warnings[i].source.mealId`, `.recipeId` | `warning.i.mealId`, `.recipeId` |

Source `date` and `recipeName` are generation display metadata; this saved schema
stores only meal/recipe references. Preserve every source entry and occurrence
count; do not re-aggregate the generator's output. Saved snapshots keep their
original contents when recipes or meals later change. Counts and the 64 KiB body
limit below still apply; handle a rejected save without claiming it succeeded.

## Endpoints

All endpoints require the existing authenticated session cookie. Mutations also
require `X-Panned-Out-Request: 1` and `application/x-www-form-urlencoded`, matching
the other backend APIs. Use `URLSearchParams` to encode fields. Responses are JSON
with `Cache-Control: no-store`.

| Method | Path | Result |
| --- | --- | --- |
| POST | `/api/shopping-lists` | 201, newly saved list; `Location` points to it |
| GET | `/api/shopping-lists` | 200, array of the current account's saved lists; `[]` when empty |
| GET | `/api/shopping-lists/{listId}` | 200, one complete saved list |
| PATCH | `/api/shopping-lists/{listId}/items/{itemId}/purchased` | 200, complete list after updating one item's status |

List order is stable by UUID, **not chronological**. Every save creates a new list;
there is no replacement, deletion, naming, manual item editing, or automatic
refresh of a saved list in these tickets.

## Saving a snapshot

Flatten the generated data into these form fields. Indices start at zero.

| Field | Meaning |
| --- | --- |
| `start`, `end` | Inclusive date range, `YYYY-MM-DD`; start must not be after end |
| `itemCount` | Number of items, 0–500 |
| `item.i.text` | Ingredient text, preserved exactly (including Unicode/whitespace); nonblank, up to 10,000 characters |
| `item.i.occurrences` | Supplied occurrence count, 1–1,000,000; not recalculated here |
| `item.i.sourceCount` | Number of source references for this item, 1–500 |
| `item.i.source.j.mealId` | Existing scheduled-meal UUID belonging to the signed-in account |
| `item.i.source.j.recipeId` | Positive recipe ID matching that scheduled meal |
| `warningCount` | Number of warnings, 0–500 |
| `warning.i.message` | Warning text, nonblank, up to 10,000 characters |
| `warning.i.mealId`, `warning.i.recipeId` | Source reference for the warning |

The existing 64 KiB encoded request-body limit still applies. An empty snapshot
uses both counts set to zero. A warning-only snapshot is supported, including when
a scheduled meal's original recipe has been deleted.

IDs are generated by the server and purchased status starts as `false`. Caller
fields such as `id`, `ownerId`, and initial purchased flags cannot select another
list/account or override those defaults. Reference validation checks only the
signed-in account's calendar: each source meal must still exist, belong to the
selected range, and match the supplied recipe ID. Unknown/foreign/out-of-range
references return 409 without saving. Refresh generated results before retrying.

This is snapshot storage, not verification of the generation algorithm: ingredient
text, counts, and warning messages are supplied by the client. No other account's
data is looked up or copied. Source validation happens on save only; later recipe
edits/deletion or meal removal do not break retrieval or purchased-status updates.

Example (replace the meal ID with a real meal in the user's selected range):

```js
const fields = new URLSearchParams({
  start: '2026-10-15', end: '2026-10-17',
  itemCount: '1',
  'item.0.text': '1 cup rice',
  'item.0.occurrences': '2',
  'item.0.sourceCount': '1',
  'item.0.source.0.mealId': meal.id,
  'item.0.source.0.recipeId': String(meal.recipeId),
  warningCount: '0',
});
const response = await fetch('/api/shopping-lists', {
  method: 'POST', credentials: 'same-origin',
  headers: { 'X-Panned-Out-Request': '1' }, body: fields,
});
const data = await response.json();
// Check response.ok and handle errors before displaying data as a saved list.
```

Response shape (IDs shown are illustrative):

```json
{
  "id": "cc7d8b21-4d38-479f-80aa-86162fcd74ca",
  "start": "2026-10-15",
  "end": "2026-10-17",
  "items": [{
    "id": "d9cd011d-06f9-43f6-a232-c0e3933a2bb7",
    "text": "1 cup rice",
    "occurrences": 2,
    "purchased": false,
    "sources": [{"mealId": "f359234e-fabb-4c9c-85fe-813c1d965c30", "recipeId": 1}]
  }],
  "warnings": []
}
```

Each warning is `{ "message": "...", "source": { "mealId": "...", "recipeId": 1 } }`.
Warnings and source arrays retain their supplied order. They remain visible when
the saved list is retrieved; checking items off does not remove warnings.

## Purchased status

Send **only** `purchased=true` or `purchased=false` to the PATCH endpoint. Use the
saved list/item UUIDs returned by POST/GET, not a recipe ID or array index.
The endpoint sets an explicit status rather than toggling, so retrying the same
update is safe. It preserves the list date range, all item contents/IDs/references,
other purchased flags, and warnings. Extra mutation fields are rejected.

```js
await fetch(`/api/shopping-lists/${list.id}/items/${item.id}/purchased`, {
  method: 'PATCH', credentials: 'same-origin',
  headers: { 'X-Panned-Out-Request': '1' },
  body: new URLSearchParams({ purchased: String(checked) }),
});
```

Errors use `{ "error": "message" }`: 400 invalid fields/IDs/status, 401 signed out,
403 request verification failure, 404 unknown or another account's list/item,
405 unsupported method, 409 stale/unavailable source reference on save, 413 body
too large, 415 unsupported content type, 500 storage failure. The frontend should
handle 401 through the existing session-expired flow and preserve user input on
other failures. Do not retry POST blindly after an uncertain network result: each
successful POST creates a new snapshot.

## Storage and tests

Files live at `<recipe-filename>.accounts/users/<account UUID>/shopping-lists/<list UUID>.properties`.
The account directory is resolved from the server session, never from request
fields. UTF-8 properties files are written through a temporary file and atomic
replacement, following existing storage conventions. Updates are synchronized on
the per-account repository. Run only one server process against a storage directory.
Malformed saved data produces an error instead of being silently reset/overwritten.
Accounts, snapshots, and purchased status survive restart; sessions do not.

From the repository root with the JDK on PATH:

```sh
javac -d backend/build backend/src/*.java backend/tests/*.java
python -m unittest discover -s tests -p test_saved_shopping_lists_api.py
```

The focused HTTP tests cover exact snapshot round trips, stable IDs, empty and
warning-only lists, Unicode text, restart persistence, recipe/meal changes,
checking/unchecking, unchanged neighboring items/lists, account/source isolation,
invalid requests, CSRF, and storage read/write failures. They use temporary data.
UI integration and real generator-to-save acceptance require the separate team work.
