import time
import pytest
from playwright.sync_api import expect

BASE_URL = "http://localhost:5173"
TEST_PASSWORD = "demo-day-password-123"

# Demo Day End-to-End Flow (SCRUM-161)
# One test per step of the demo path, in the order it will be clicked through on demo day.
# Out of scope: AI photo recipe generation, My Saved Recipes screen, saving a meal plan to a collection.
# Each test needs the PR or ticket named in its skip reason. Remove the skip when that piece is merged.
# (TC-FLOW-02 lives in test_calendar.py as TC-68-01 and 68-02. These replace the old TC-FLOW-01 to 06. The old full-flow case is now TC-FLOW-13.)


def unique_email():
    return f"demo{time.time_ns()}@example.com"


def create_account(page, email):
    """Create a private account through the Login page. Ends signed in on /calendar."""
    page.goto(f"{BASE_URL}/login")
    page.get_by_role("button", name="Create an account").click()
    page.get_by_label("Email address").fill(email)
    page.get_by_label("Password").fill(TEST_PASSWORD)
    page.get_by_role("button", name="Create account").click()
    page.wait_for_url("**/calendar")


def sign_out(page):
    page.get_by_role("button", name="Log out").click()
    page.wait_for_url("**/login")


def week_range_of_today(page):
    """This week's Sunday and Saturday as YYYY-MM-DD, worked out in the browser (the same way the page does it)."""
    return page.evaluate("""() => {
        const key = d => d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
        const t = new Date();
        const start = new Date(t.getFullYear(), t.getMonth(), t.getDate() - t.getDay());
        const end = new Date(start); end.setDate(end.getDate() + 6);
        return [key(start), key(end)];
    }""")


def sign_in(page, email):
    page.goto(f"{BASE_URL}/login")
    page.get_by_label("Email address").fill(email)
    page.get_by_label("Password").fill(TEST_PASSWORD)
    page.get_by_role("button", name="Sign In").click()


def save_recipe(page, name):
    """Save a recipe from the Recipes page, then return to the calendar."""
    page.goto(f"{BASE_URL}/recipes")
    page.get_by_role("button", name="Add Recipe").first.click()
    page.get_by_label("Name").fill(name)
    page.get_by_label("Ingredients").fill("rice, beans")
    page.get_by_label("Instructions").fill("Cook together")
    page.get_by_role("button", name="Save recipe").click()
    expect(page.get_by_text(name)).to_be_visible()
    page.goto(f"{BASE_URL}/calendar")


def add_meal_to_selected_day(page, recipe_name, meal_type="Dinner"):
    """Add a meal to the day that is selected on the calendar (today, when the page first opens)."""
    page.get_by_role("button", name="Add Meal").first.click()
    page.get_by_label("Recipe", exact=True).select_option(label=recipe_name)
    page.get_by_label("Meal type").select_option(meal_type)
    page.get_by_role("button", name="Save meal").click()
    expect(page.get_by_role("heading", name="Add a meal for", exact=False)).not_to_be_visible()


#TC-FLOW-01: Sign in to a private account and land on the calendar (SCRUM-161 step 1)
@pytest.mark.skip(reason="Login not merged yet (PR #11)")
def test_sign_in_lands_on_calendar(page):
    # Precondition: a user account already exists and user is signed out on the Login page
    email = unique_email()
    create_account(page, email)
    sign_out(page)

    # Steps:
    # 1. Enter the account's email and password
    # 2. Click "Sign In"
    sign_in(page, email)

    # Expected Result: User lands on the Calendar home page and the session is active
    # (still signed in after a reload)
    expect(page).to_have_url(f"{BASE_URL}/calendar")
    page.reload()
    expect(page).to_have_url(f"{BASE_URL}/calendar")
    expect(page.get_by_role("button", name="Log out")).to_be_visible()


# TC-FLOW-02 (step 2, switch between day, week and month views) is not a separate test:
# TC-68-01 and TC-68-02 in test_calendar.py already run the same steps and checks.


#TC-FLOW-03: Browse suggested meal plans and filter by suggested, saved and all (step 3)
@pytest.mark.skip(reason="Meal plan filters not built yet (SCRUM-136, SCRUM-138)")
def test_browse_meal_plans_and_filter(page):
    # Precondition: user is signed in and has opened the Meal Plans page

    # Steps:
    # 1. View the list of meal plans
    # 2. Click the "Suggested" filter
    # 3. Click the "Saved" filter
    # 4. Click the "All" filter

    # Expected Result: Suggested shows only suggested plans, Saved shows only saved plans,
    # and All shows both
    assert False  # placeholder, replace with real check once SCRUM-136 and 138 are done


#TC-FLOW-04: Plans and recipes come from the database, not hardcoded data (step 4)
@pytest.mark.skip(reason="Plans load from the backend after SCRUM-136, 137 and 138")
def test_plans_and_recipes_come_from_database(page):
    # Precondition: user is signed in, and a test meal plan with a recipe was added to the database

    # Steps:
    # 1. Open the Meal Plans page
    # 2. Open that plan

    # Expected Result: The test plan and its recipe show on the page. A plan that is not in
    # the database does not appear.
    assert False  # placeholder, replace with real check once SCRUM-136, 137 and 138 are done


#TC-FLOW-05: Open a recipe from a meal card and from a plan, and go back (step 5)
@pytest.mark.skip(reason="Recipe Details page and Add Meal not merged yet (PR #12, #14)")
def test_open_recipe_from_meal_card_and_plan_then_go_back(page):
    # Precondition: user is signed in, has a meal on the calendar, and a plan with a recipe exists

    # Steps:
    # 1. Click the recipe on a meal card on the calendar
    # 2. Click Back
    # 3. Open a meal plan and click one of its recipes
    # 4. Click Back

    # Expected Result: Each click opens that recipe's detail page, and Back returns to the
    # calendar and to the plan page
    assert False  # placeholder, replace with real check once PR #12 and #14 are merged


#TC-FLOW-06: Add one recipe to a chosen day and see it on the calendar (step 6)
@pytest.mark.skip(reason="Add Meal not merged yet (PR #12)")
def test_add_one_recipe_to_chosen_day(page):
    # Precondition: user is signed in and has at least one saved recipe

    # Steps:
    # 1. Select a day on the calendar
    # 2. Click "Add Meal"
    # 3. Choose the recipe and a meal type, then click "Save"

    # Expected Result: A meal card with the recipe's name shows on that day
    name = f"Demo Tacos {time.time_ns()}"
    create_account(page, unique_email())
    save_recipe(page, name)

    # Steps:
    # 1. Select a day on the calendar (today is selected when the page opens)
    # 2. Click "Add Meal"
    # 3. Choose the recipe and a meal type, then click "Save meal"
    add_meal_to_selected_day(page, name)

    # Expected Result: A meal card with the recipe's name shows on that day
    expect(page.locator(".meal-card")).to_have_count(1)
    expect(page.locator(".meal-card").first).to_contain_text(name)


#TC-FLOW-07: Add a whole meal plan to the calendar and see every meal on its day (step 7)
@pytest.mark.skip(reason="Add meal plan to calendar not built yet (SCRUM-135)")
def test_add_whole_meal_plan_to_calendar(page):
    # Precondition: user is signed in and a meal plan with several meals exists

    # Steps:
    # 1. Open the meal plan
    # 2. Click "Add to calendar" and choose a start date
    # 3. Open the calendar

    # Expected Result: Every meal in the plan shows on its own day, starting on the chosen date
    assert False  # placeholder, replace with real check once SCRUM-135 is done


#TC-FLOW-08: Refresh the page and the added meals are still there (step 8)
@pytest.mark.skip(reason="Add Meal not merged yet (PR #12)")
def test_added_meals_stay_after_refresh(page):
    # Precondition: user is signed in and has added a meal to a day (TC-FLOW-06)

    # Steps:
    # 1. Reload the page

    # Expected Result: The added meal is still on that day
    name = f"Demo Pasta {time.time_ns()}"
    create_account(page, unique_email())
    save_recipe(page, name)
    add_meal_to_selected_day(page, name)
    expect(page.locator(".meal-card")).to_have_count(1)

    # Steps:
    # 1. Reload the page
    page.reload()

    # Expected Result: The added meal is still on that day
    expect(page.locator(".meal-card")).to_have_count(1)
    expect(page.locator(".meal-card").first).to_contain_text(name)


#TC-FLOW-09: Open Shopping List, choose the week and press Generate (step 9)
@pytest.mark.skip(reason="Shopping list generation not merged yet (PR #15, PR #16, SCRUM-132)")
def test_generate_shopping_list_for_week(page):
    # Precondition: user is signed in and has meals scheduled this week
    name = f"Demo Chili {time.time_ns()}"
    create_account(page, unique_email())
    save_recipe(page, name)
    add_meal_to_selected_day(page, name)
    expect(page.locator(".meal-card")).to_have_count(1)

    # Steps:
    # 1. Open Shopping List
    page.get_by_role("link", name="Shopping").first.click()
    expect(page.get_by_role("heading", level=1, name="Weekly Groceries")).to_be_visible()
    # 2. Choose this week's start and end dates (the page opens on this week, Sunday to Saturday)
    start, end = week_range_of_today(page)
    expect(page.get_by_label("Start date")).to_have_value(start)
    expect(page.get_by_label("End date")).to_have_value(end)
    # 3. Click "Generate from Meal Plan"
    page.get_by_role("button", name="Generate from Meal Plan").click()

    # Expected Result: A shopping list is generated for that week with no error
    expect(page.get_by_role("heading", name="Ingredients")).to_be_visible()
    expect(page.get_by_role("alert")).to_have_count(0)


#TC-FLOW-10: The list matches the meals scheduled for that week (step 10)
@pytest.mark.skip(reason="Shopping list generation not merged yet (PR #15, PR #16, SCRUM-132)")
def test_shopping_list_matches_scheduled_meals(page):
    # Precondition: user is signed in, has meals scheduled this week, and has generated the list (TC-FLOW-09)
    in_week = f"Demo Beans {time.time_ns()}"
    outside = f"Demo Outside {time.time_ns()}"
    create_account(page, unique_email())
    save_recipe(page, in_week)                       # its ingredients are "rice, beans"
    add_meal_to_selected_day(page, in_week)
    outside_id = page.request.post(f"{BASE_URL}/api/recipes", headers={"X-Panned-Out-Request": "1"}, form={
        "name": outside, "category": "My Recipes", "difficulty": "Easy", "mealType": "Dinner",
        "ingredients": "saffron threads", "instructions": "Cook", "prepTime": "5", "calories": "1",
        "protein": "1", "fat": "1", "carbohydrates": "1", "fiber": "1"}).json()["id"]
    next_month = page.evaluate("() => { const d = new Date(); d.setDate(d.getDate() + 30); "
                               "return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'); }")
    page.request.post(f"{BASE_URL}/api/meals", headers={"X-Panned-Out-Request": "1"},
                      form={"recipeId": str(outside_id), "date": next_month, "mealType": "Dinner"})
    page.get_by_role("link", name="Shopping").first.click()
    page.get_by_role("button", name="Generate from Meal Plan").click()

    # Steps:
    # 1. Compare the list items with the ingredients of the scheduled meals
    # Expected Result: Every ingredient from this week's meals is on the list, and nothing
    # from meals outside the week is
    expect(page.locator(".shopping-item")).to_have_count(1)
    expect(page.locator(".shopping-item")).to_contain_text("rice, beans")
    expect(page.locator(".shopping-item")).to_contain_text(in_week)
    expect(page.get_by_text("saffron threads")).to_have_count(0)


#TC-FLOW-11: A week with no meals shows an empty list, not an error (step 11)
@pytest.mark.skip(reason="Shopping list generation not merged yet (PR #15, PR #16, SCRUM-132)")
def test_empty_week_shows_empty_list(page):
    # Precondition: user is signed in and has no meals in the chosen week
    create_account(page, unique_email())

    # Steps:
    # 1. Open Shopping List
    page.get_by_role("link", name="Shopping").first.click()
    # 2. Choose a week with no meals
    page.get_by_label("Start date").fill("2026-12-06")
    page.get_by_label("End date").fill("2026-12-12")
    # 3. Click "Generate from Meal Plan"
    page.get_by_role("button", name="Generate from Meal Plan").click()

    # Expected Result: The empty list message shows and there is no error message
    expect(page.get_by_text("No ingredients found for these dates.", exact=False)).to_be_visible()
    expect(page.get_by_role("alert")).to_have_count(0)


#TC-FLOW-12: [OPTIONAL] Save the list, mark items as bought, sign out and back in (step 12)
@pytest.mark.skip(reason="Save list and purchased checkboxes not built yet (SCRUM-133, PR #13)")
def test_save_list_mark_bought_and_sign_back_in(page):
    # Precondition: user is signed in and has a generated shopping list

    # Steps:
    # 1. Click "Save list"
    # 2. Check two items as bought
    # 3. Sign out and sign back in
    # 4. Open Shopping List

    # Expected Result: The saved list and the two checked items are still there
    assert False  # placeholder, replace with real check once SCRUM-133 is done


#TC-FLOW-13: Run the whole flow start to finish with no errors in the console (step 13)
@pytest.mark.skip(reason="Needs every piece of the flow merged (SCRUM-134 to 138, PR #11, #12, #14, #15)")
def test_full_demo_flow_has_no_console_errors(page):
    # Precondition: a user account already exists and user is on the Login page
    console_errors = []
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

    # Steps:
    # 1. Run steps 1 to 12 of the demo flow in order (TC-FLOW-01 to TC-FLOW-12)

    # Expected Result: Every step works and the console shows no errors from start to finish
    assert console_errors == []
    assert False  # placeholder, replace with the full flow once every piece is merged


#TC-FLOW-14: A second account sees none of the first account's data (step 14)
@pytest.mark.skip(reason="Login and Add Meal not merged yet (PR #11, #12)")
def test_second_account_sees_no_data_from_first(page):
    # Precondition: account A is signed in and has a meal on the calendar and a generated list

    # Steps:
    # 1. Sign out of account A
    # 2. Sign in to a different account B
    # 3. Look at the calendar, recipes and shopping list

    # Expected Result: Account B sees none of account A's recipes
    # (meals are covered by TC-1-03 and the shopping list by TC-118-08)
    assert False  # placeholder, replace with real check once PR #11 and #12 are merged
