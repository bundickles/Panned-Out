# SCRUM-134: Schedule from recipe details

Stacked on SCRUM-140 and SCRUM-138. Add to Calendar now opens a date/meal-type form and posts the recipe ID to /api/meals. Required fields are validated before submission; failures keep the chosen values for retry. Calendar reads a validated local-date query parameter so the saved meal is immediately visible on the correct day/month, including after refresh.

For suggested recipes the form explains that a private copy will be saved first. The returned numeric ID is retained after a scheduling failure and reused on retry. Namespaced catalog IDs are never sent as private recipe IDs.

Validation: production build and lint (existing RecipeForm warning), browser test tests/test_recipe_scheduling_ui.cjs with isolated accounts. Checks missing date, chosen date across month boundaries, month/week/day display, refresh persistence, the same recipe on two dates, and suggestion save/schedule retry without duplicate copies.

Run with BASE_URL, optional PLAYWRIGHT_MODULE/CHROME_PATH as described in SCRUM-138.md. Existing protected routes handle signed-out access.
