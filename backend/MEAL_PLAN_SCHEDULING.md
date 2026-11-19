# SCRUM-135: Schedule a premade meal plan

Open Meal Plans, choose a preset, select saved recipes and a start date, then
choose Add to Calendar. One recipe is scheduled per consecutive day at the
selected meal type. Existing meals on those dates are preserved. The success
message links to the start date on Calendar.

## Ownership and independent scope

Recipes must already be saved in the signed-in account. High Protein, Low Calorie,
and Keto show saved recipes in the matching category. Balanced offers the saved
collection without asserting any nutritional classification. The first seven
eligible recipes are selected initially; users can select 1–31, in displayed order.
No suggested recipe is copied into an account automatically. An empty collection
links to Recipes. This choice uses the existing main APIs and does not require
SCRUM-138, SCRUM-140, or SCRUM-134's open PRs. Custom collections are out of scope.

## API

POST /api/meals/plan uses existing session authentication and the
X-Panned-Out-Request: 1 header. Send form-encoded fields:

- plan: High Protein, Low Calorie, Keto, or Balanced
- startDate: YYYY-MM-DD
- mealType: Breakfast, Lunch, Dinner, or Snack (default Dinner)
- recipeIds: comma-separated unique numeric IDs, in desired day order (1–31)

The server resolves only the caller's saved recipes and validates all IDs,
categories, dates and meal types before writing. The calendar is updated once
using the existing atomic-file replacement. Invalid, missing or mismatched
recipes do not add any meals. Storage read/replacement failures preserve prior
data. Success returns 201 and the added meal objects. GET on this route is 405.
Submitting the same successful plan again intentionally adds another copy;
the UI disables submissions while pending and replaces the form on success.

## Validation

    javac --release 11 -d backend/build backend/src/*.java backend/tests/*.java
    python3 -m unittest discover -s tests -p test_plan_schedule_api.py
    python3 -m unittest discover -s tests -p test_meal_api.py
    PLAYWRIGHT_CHANNEL=chrome python3 -m unittest discover -s tests -p test_plan_schedule_ui.py
    npm --prefix frontend run build
    npm --prefix frontend run lint

The browser test starts isolated Java/Vite servers, registers a disposable account,
checks failure/retry and calendar navigation, and verifies persistence on reload.
