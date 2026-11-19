# Daily planned nutrition (SCRUM-182)

`GET /api/nutrition/daily?start=2026-11-18&end=2026-11-19` returns one entry
for each day in an inclusive date range. It uses the signed-in account's scheduled
meals and current saved recipes. It does not track what the user actually ate.

Use the existing session cookie. No account ID is accepted. The endpoint is read-only
and does not require the mutation verification header. A frontend using the existing
Vite `/api` proxy can fetch this URL with the same credentials as the meal API.

## Response

```json
{
  "start": "2026-11-18",
  "end": "2026-11-19",
  "days": [
    {
      "date": "2026-11-18",
      "mealCount": 1,
      "calories": 400,
      "protein": 25,
      "carbohydrates": 50,
      "fat": 12,
      "fiber": null,
      "missingNutrition": {
        "calories": 0,
        "protein": 0,
        "carbohydrates": 0,
        "fat": 0,
        "fiber": 1
      },
      "complete": false
    },
    {
      "date": "2026-11-19",
      "mealCount": 0,
      "calories": 0,
      "protein": 0,
      "carbohydrates": 0,
      "fat": 0,
      "fiber": 0,
      "missingNutrition": {
        "calories": 0,
        "protein": 0,
        "carbohydrates": 0,
        "fat": 0,
        "fiber": 0
      },
      "complete": true
    }
  ],
  "warnings": []
}
```

Days are ordered by date. Calories use the recipe's stored calorie values; the other
fields use its stored gram values. Each scheduled meal contributes its recipe once,
including when the same recipe is scheduled more than once on a day. There is no
servings field or serving-size scaling in the existing model. This endpoint therefore
does not infer portions, multiply by a serving count, or estimate nutrition from
ingredients. It sums the values exactly as stored for each recipe.

Recipe nutrition edits, added or removed meals, and normal recipe deletion are reflected
on the next request. No totals are cached or written to storage. Each request reads
one consistent account-specific recipe and calendar snapshot.

## Missing values and old data

* New recipe saves record which of the five nutrition fields were actually supplied.
  An explicitly supplied `0` is known zero. An omitted field is unknown, even though
  the existing recipe API still returns its numeric `0` default for compatibility.
  The backend trusts supplied values. It cannot distinguish a user-entered zero from
  a frontend that automatically sends zero for an empty field, so clients should omit
  unknown nutrition fields rather than populate them with zero.
* If any scheduled recipe is missing a nutrient, that day's total for that nutrient
  is `null`, and `missingNutrition` counts the affected scheduled meals. Other known
  totals still appear. `complete` is true only when every total is known.
* Old recipe files did not distinguish omitted values from zero. Without the new
  `knownNutrition` property, positive values are treated as known and zero values as
  unknown. This deliberately avoids presenting an unrecorded value as measured zero.
  Saving the recipe again with explicitly supplied nutrition resolves the ambiguity.
* A day with no scheduled meals returns zero totals and `complete: true`.
* If old or externally changed calendar data references an unavailable recipe, its
  meal still counts, every nutrient is unknown, and `warnings` includes its `mealId`,
  `recipeId`, `date`, and a message. Normal recipe deletion removes its scheduled meals
  through SCRUM-181. This fallback does not modify storage or silently omit damage.

The frontend must display `null` as unavailable or incomplete, never as zero. The
metadata remains inside the existing version-1 recipe properties file and survives
server restarts. Existing recipe response fields and routes are unchanged.

## Validation and errors

* `start` and `end` are required, each exactly once, in `YYYY-MM-DD` format, years
  0001–9999. Dates must exist and `start` must not be later than `end`.
* The maximum inclusive range is 366 days to bound the response size. Unknown query
  fields, duplicate fields, malformed dates, and longer ranges return `400`.
* No session: `401`. Unsupported authenticated method: `405` with `Allow: GET`.
  Mutating methods without the existing verification header are blocked first with
  `403`, consistent with the rest of the API.
* Unreadable or invalid account recipe/calendar storage: `500`, not a successful
  empty result. Responses keep the existing `Cache-Control: no-store` header.

This ticket supplies the backend API. It does not change Vanny's nutrition widget,
connect the page to this route, set calorie goals, or add consumed-meal tracking.

## Verification

After compiling the backend, run:

```text
python -m unittest discover -s tests -p test_daily_nutrition_api.py -v
```

The focused checks cover inclusive boundaries and leap years, repeated recipes,
empty days, account isolation with overlapping IDs, recipe edits, meal and recipe
removal, explicit zero versus omitted values, legacy data, persistence across restart,
unavailable recipes, strict validation, and storage failures.
