# SCRUM-141 — Recipe sorting

Recipes can be sorted by name, difficulty, or preparation time in either direction. Sorting applies after search and category filtering. The URL retains the selected order across reloads; an invalid order falls back to name A–Z. Missing/invalid values stay last in both directions, zero preparation time is valid, ties retain their original order, and sorting does not mutate API records.

Validation:
- `node --test tests/test_recipe_sorting.mjs`
- `node tests/test_recipe_sorting_ui.cjs` with the same Playwright/Chrome environment as the other browser tests.
- Frontend production build and lint.

This branch is stacked on `feature/SCRUM-133-saved-shopping-ui`; use that as the PR base to review only this ticket.
