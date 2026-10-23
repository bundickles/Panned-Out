# SCRUM-132: shopping-list generation

Owner: Pranaya Poudel. This endpoint-only change builds on calendar storage
(PR #12 / SCRUM-56) and authentication (PR #11 / SCRUM-55). It extracts the
backend generation previously bundled into PR #15 / SCRUM-57. The UI integration
stays in PR #15; generation contract tests belong to SCRUM-119 and validation and
isolation tests belong to SCRUM-120, each with its own branch and PR.

Merge the persistent recipe ID fix in PR #10 before accepting generation with
recipe deletion: reused IDs in older builds can link a meal to a replacement
recipe. Existing ambiguous references created before that fix require manual
review. No generation code can reconstruct an already reused ID.

## Run locally

```sh
javac --release 11 -d backend/build backend/src/*.java backend/tests/*.java
java -cp backend/build RecipeServer
```

Register/sign in via `/api/auth/register` or `/api/auth/login`, create recipes
through `/api/recipes`, and schedule them through `/api/meals`. Use the session
cookie for generation. Responses are private to that account; no account selector
is accepted. Existing request verification still applies to non-GET methods.

## Contract

`GET /api/shopping-list?start=YYYY-MM-DD&end=YYYY-MM-DD`

Both dates are required, inclusive, and valid calendar dates; equal dates are
accepted. Bad, missing, repeated or reversed date parameters return 400. An
unauthenticated request returns 401. Authenticated POST/PUT/DELETE requests return
405 with `Allow: GET`. Storage failures return 500 with a JSON `error` string;
stored data is never overwritten by generation. Successful responses include
`Cache-Control: no-store` and JSON:

```json
{
  "start": "2026-10-01",
  "end": "2026-10-07",
  "items": [{
    "name": "1 cup rice",
    "occurrences": 1,
    "sources": [{
      "mealId": "scheduled-meal-uuid",
      "recipeId": 1,
      "date": "2026-10-04",
      "recipeName": "Rice bowl"
    }]
  }],
  "warnings": []
}
```

Ingredient text is split by line. Blank lines are skipped and Unicode whitespace
is collapsed to a single space before trimming. Lines differing only in case or
spacing are grouped, keeping the first normalized spelling and first-appearance
order. Meals are visited in stored insertion order, then ingredients in recipe
order. Each line occurrence contributes a source, so `occurrences` always equals
`sources.length`. Repeated ingredient lines in one recipe also count. Generating
the same range twice does not accumulate counts or write a saved list.

Quantities remain literal text: `1 cup rice` and `2 cups rice` are separate items.
There is no quantity math, unit conversion, or serving scaling. Ingredients come
from the current recipe, while the source name comes from the scheduled snapshot.
A range without meals returns empty `items` and `warnings` arrays.

A deleted recipe contributes only a warning, with its source:

```json
{"message":"Recipe unavailable; its ingredients were omitted.","source":{"mealId":"scheduled-meal-uuid","recipeId":1,"date":"2026-10-04","recipeName":"Rice bowl"}}
```

Legacy recipes without ingredient text also contribute a source warning rather
than crashing generation. Other available recipes still contribute ingredients.

The singular `/api/shopping-list` generates a read-only list. PR #13's plural
`/api/shopping-lists` persists saved snapshots and purchased state; its backend
ownership remains with Aayush. Saved-list UI wiring is SCRUM-133 and is not part
of generation. Vanny's Shopping/Sidebar collaboration decision remains unchanged.

## Acceptance checks

SCRUM-119 covers exact response shape, source fields matched against `/api/meals`,
inclusive dates, single-day and empty ranges, grouping, spelling, ordering,
counts, Unicode whitespace and repeat generation. SCRUM-120 covers invalid and
repeated dates, methods/Allow header, signed-out access, overlapping recipe IDs
across accounts, ignored owner parameters, deleted/legacy recipes, and corrupt
storage with recovery. Run those test files on their respective PR branches.

Before merging: review PR #10/#11/#12 dependencies, review the generation API,
and run UI QA on PR #15. These tickets stay in review until the team accepts them.
