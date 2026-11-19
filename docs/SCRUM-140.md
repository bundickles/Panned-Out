# SCRUM-140: Save suggested recipes

Stacked on SCRUM-138. Suggested recipe cards and details expose Save to My Recipes. Users choose a meal type because the catalog has no meal-type field. Success displays saved state, including after refresh. Failures preserve the form for retry.

POST /api/recipes/{suggested:id}/save accepts form-encoded mealType and requires the existing session/request-verification header. The server copies only catalog-owned fields into the authenticated account. It returns 201 for a new copy and 200 for an existing one. A persisted optional suggestedId on private recipes provides idempotence across repeat requests, edits, and restarts; legacy recipe files remain readable. Deleting a copy permits saving it again. Originals stay read-only. Unknown nutrition retains the existing storage defaults; the UI does not invent catalog nutrition.

Validation:
- javac -d backend/build backend/src/*.java
- python3 -m unittest discover -s tests -p test_save_suggestions_api.py -v
- npm --prefix frontend run build; npm --prefix frontend run lint
- BASE_URL=http://localhost:5180 node tests/test_save_suggestions_ui.cjs (Playwright; optional PLAYWRIGHT_MODULE and CHROME_PATH)

API tests cover provenance/content, account isolation, duplicate prevention after editing/restart, missing sessions, request verification, invalid meal type, missing catalog ID, and unsupported method. Browser checks cover card and detail saved state, refresh, and failure/retry.
