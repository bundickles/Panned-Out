# SCRUM-183 — Delete a saved shopping list

A selected saved list now has a Delete list action with explicit Confirm delete and Cancel controls. Pending requests disable list actions. A successful deletion removes the selected savedList URL parameter, preserves date filters/generated results, refreshes the list picker, and announces success. A failed deletion retains the list and confirmation so the user can retry.

`DELETE /api/shopping-lists/{uuid}` returns 200 with `{"deleted":true}` on success; missing or other-account IDs return 404. Existing session/request verification applies. UUID validation and account-scoped storage prevent deleting another account's list. Repository deletion is synchronized with saves/purchased updates and persists on disk; recipes, meals, and other snapshots are untouched.

## Validation

- `npm --prefix frontend run build`
- `npm --prefix frontend run lint` (one existing RecipeForm warning)
- `node --test tests/*.mjs`
- `python3 -m unittest discover -s tests -p '*_api.py'`
- `BASE_URL=http://localhost:5181 PLAYWRIGHT_MODULE=/path/to/playwright CHROME_PATH=/path/to/chrome node tests/test_delete_saved_lists_ui.cjs`
- Run `tests/test_saved_shopping_ui.cjs` with the same browser environment for saving/checkmark regression.

Browser coverage: cancel/no request, failed delete and retry, disabled pending controls, date/URL preservation, other-list/source preservation, refresh/login persistence, and deletion of the final saved list. API coverage additionally checks unauthenticated/unverified requests, account isolation, repeated/missing delete and server restart persistence.

PR base: `feature/SCRUM-133-saved-shopping-ui` (PR #37). Separate follow-up to SCRUM-133; retarget to main after #37 merges. No merges performed.
