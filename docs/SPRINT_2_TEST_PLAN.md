# Sprint 2 Test Plan: Panned Out UI and flow tests

Author: Jamiyah Coats (QA and testing lead). Tests live in `tests/` and are in PR #29.
Checked against PR #14 merged with main (Oct 22, 2026).

## 1. What this covers
- Browser tests written with Python, pytest and Playwright, one file per app component.
- Each test has a header like `#TC-66-03: title`, then Precondition, Steps and Expected Result comments, the same layout as Sprint 1.
- Backend API checks are not in this plan. Teammates test those, and they are tracked in `backend-api-test-cases.md`.
- Backlog items outside Sprint 2 (themes, minimized cards, settings, AI photo) are not covered.

## 2. Test files by component

| File | Component | Jira tickets (Sprint 2 and Sprint 1) | Tests |
|---|---|---|---|
| `test_login.py` | Sign in, sign out, accounts | SCRUM-26, 27, 44 to 46, 126 | 15 |
| `test_calendar.py` | Calendar, Add Meal, month, week, day views | SCRUM-1, 17, 28, 30, 32, 34, 40 to 43, 62, 65 to 70, 124, 129, 150 | 45 |
| `test_recipe_management.py` | Recipe list, form, edit, search, filters | SCRUM-16, 25, 29, 31, 35 to 39 | 30 |
| `test_recipe_info.py` | Recipe detail page | SCRUM-50 to 53, 125, 131, 145, 146 | 17 |
| `test_meal_plans.py` | Meal plan cards, custom plans, suggested recipes | SCRUM-64, 76 to 80, 142, 152 to 155 | 26 |
| `test_shopping_list.py` | Generated shopping list | SCRUM-63, 71 to 75, 92, 117, 118, 127, 128, 130, 147, 148 | 24 |
| `test_login_mealplan_flow.py` | Full demo flow across pages | SCRUM-161 | 13 |
| `test_app_navigation.py` | Sidebar and navigation | SCRUM-143, 156, 157, 162 | 1 |

SCRUM-144, 158 and 159 (UI cleanup regression) are covered by rerunning the Sprint 1 files against the new build.

Total: 171 test functions. Some are parametrized, so pytest reports more runs.

## 3. How to run
1. Start the backend on port 8080 (Java `RecipeServer`).
2. Start the frontend on port 5173 (`npm run dev` in `frontend/`).
3. From the repo root run `pytest tests/` (add `-v` to see names, or `tests/test_calendar.py` for one file).
4. `tests/conftest.py` creates an account and signs in once for the whole run. Login tests start signed out.
5. Sign-in limit: 20 sign-ins per IP in 15 minutes, and successes count. A long run can lock itself out. Restart the backend to reset it.

## 4. Conventions
- **Skip lines:** a test for a feature in an open PR has `@pytest.mark.skip(reason="... (PR #nn)")`. Remove the line when that PR merges.
- **BUG FOUND:** a test that finds a real bug has a `# BUG FOUND (BUG-nn)` comment under its heading and fails until the bug is fixed.
- **Retired:** a case that no longer applies keeps its heading with a one-line note saying why.
- **Placeholders:** 35 tests are `assert False` placeholders for features that do not exist yet (see section 7).
- **Time:** tests that need a known date freeze the browser clock to 2026-10-15.

## 5. Bugs found
| ID | Test | Summary |
|---|---|---|
| BUG-01 | TC-53-01 | Back from the recipe detail page clears the Recipes search |
| BUG-02 | TC-29-14 | The recipe form never saves the image |
| BUG-03 | TC-32-02 | A renamed recipe is not updated on its meal card |
| BUG-04 | TC-32-03 | A deleted scheduled recipe leaves a ghost meal card |
| BUG-05 | TC-66-03 | Week view meal card shows no meal type |
| BUG-06 | TC-69-03 | Calendar meal cards do not open the recipe |
| BUG-07 | TC-70-02 | Week header only names the first month |

The full list with fixed items and merge issues is in `bugs-and-issues.md`.

## 6. Retired cases
- TC-69-01 (covered by TC-66-03 and 67-01)
- TC-52-05 (covered by TC-50-04)
- TC-78-01 (covered by TC-GAP-85-01)
- TC-75-02 (folded into TC-118-06)
- TC-FLOW-02 (covered by TC-68-01 and 68-02)
- Manual shopping list cases TC-71-03, 72-02, 73-01, 73-03, 74-01, 74-03, GAP-81-02, GAP-81-03: the Shopping page now builds its list from the calendar, so there is no manual list.

## 7. Not testable yet
- Meal plan recipes, filters and loading from the database (SCRUM-136, 137, 138): TC-FLOW-03, 04, 05, 07, 12, 13, 14 and the suggested recipe cases.
- Detail page Edit, Delete, Add to Calendar and macros: TC-53-03, 53-04, GAP-82-03, GAP-85-02, GAP-85-03.
- Waiting on a team answer: custom meals (TC-1-07), delete confirmation, and the shopping cases marked CONFIRM.

## 8. Results (Oct 22)
Run against PR #14 merged with main, with PR skip lines removed: 135 passed, 30 failed, 13 skipped. The 30 failures are the 7 bug tests plus the placeholders in section 7.

## 9. My contributions
- Wrote and organized all 171 tests above, plus the Sprint 1 tests they build on.
- Ran every test against each open PR and reported the results.
- Found the 7 bugs in section 5 and traced each to a PR.
- Wrote the merge-day checklist (`merge-day-checklist.md`) so each skip line can be removed when its PR merges.
- Reviewed teammates' PRs (#10 to #20 and #28) and left feedback.
