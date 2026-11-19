# SCRUM-138: Load meal-plan recipes from the backend

Based on current main; no teammate PRs are merged into this branch. The existing authentication wrapper protects Meal Plans and Recipe Details.

Each dietary collection loads GET /api/recipes?filter=suggested and matches the catalog plan field. Browse Recipes supports suggested, saved, and all sources. Namespaced suggestion IDs remain intact in detail links. Filter and selected plan are URL-backed, including after returning from details. Includes loading, empty, failure/retry, session-expiry handling, and stale-response protection. No catalog recipes are hardcoded in the UI.

Saving suggestions and scheduling remain separate stories. Existing browser-local custom collections are unchanged by this ticket.

## Verification

Run the backend and Vite with isolated test storage, then:

```sh
npm --prefix frontend run build
npm --prefix frontend run lint
node --test tests/test_recipe_search.mjs
BASE_URL=http://localhost:5180 node tests/test_meal_plans_ui.cjs
```

The browser test needs Playwright and Chromium. Optional PLAYWRIGHT_MODULE points to an external Playwright package and CHROME_PATH selects installed Chrome. It creates test accounts and one private recipe: never point it at production data. Covers real catalog/grouping, detail refresh/return, all source filters, failure/retry, empty catalog, loading/stale results, and expired sessions.
