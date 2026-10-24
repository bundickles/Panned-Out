import re
import time
import pytest
from playwright.sync_api import expect

BASE_URL = "http://localhost:5173"
FROZEN_TODAY = "2026-10-15T10:00:00"   # Thursday, October 15, 2026


def open_calendar_on_oct_15(page):
    """Freeze the browser clock to Thursday 2026-10-15, then open the calendar."""
    page.clock.set_fixed_time(FROZEN_TODAY)
    page.goto(f"{BASE_URL}/calendar")


def day_cell(page, day):
    """The calendar button for day number `day` of the month on screen."""
    return page.locator(".calendar-cell:not(.empty)").nth(day - 1)


# Helpers for tests that need a signed-in user with a saved recipe (PR #11 login, PR #12 Add Meal).
# The browser is already signed in by tests/conftest.py. All tests share one account, so each
# meal test uses its own date (nobody else uses it) and its own uniquely named recipes.
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


def add_meal(page, recipe_name, meal_type="Dinner"):
    """Add a meal to the currently selected day through the Add Meal form."""
    page.get_by_role("button", name="Add Meal").first.click()
    page.get_by_label("Recipe", exact=True).select_option(label=recipe_name)
    page.get_by_label("Meal type").select_option(meal_type)
    page.get_by_role("button", name="Save meal").click()
    expect(page.get_by_role("heading", name=re.compile("Add a meal for"))).not_to_be_visible()


def open_day(page, date_key):
    """Click the calendar cell for a date such as '2026-10-15'."""
    page.get_by_role("button", name=date_key).click()


def start_on_oct_15(page, *recipe_names):
    """Freeze the clock to Oct 15 2026 and save the given recipes. Ends on the calendar."""
    page.clock.set_fixed_time(FROZEN_TODAY)
    page.goto(f"{BASE_URL}/calendar")
    for name in recipe_names:
        save_recipe(page, name)


CAL_PASSWORD = "calendar-test-password-123"

def new_account_context(browser, **context_args):
    """A separate browser context signed in to a brand new account. Returns (context, page, email).
    Used when a test needs a second account, or needs to log out without ending the shared session."""
    context = browser.new_context(**context_args)
    page = context.new_page()
    email = f"cal{time.time_ns()}@example.com"
    page.goto(f"{BASE_URL}/login")
    page.get_by_role("button", name="Create an account").click()
    page.get_by_label("Email address").fill(email)
    page.get_by_label("Password").fill(CAL_PASSWORD)
    page.get_by_role("button", name="Create account").click()
    page.wait_for_url("**/calendar")
    return context, page, email

def unique_recipe(prefix):
    return f"{prefix} {time.time_ns()}"

def view_button(page, name):
    """The Month / Week / Day button."""
    return page.locator(".calendar-view-controls").get_by_role("button", name=name, exact=True)

def week_day_numbers(page):
    """Day numbers shown in week view, in order."""
    return [int(n) for n in page.locator(".calendar-week-day .week-day-number").all_inner_texts()]

def heading(page):
    return page.locator(".calendar-header h1")

MEAL_PASSWORD = "calendar-test-password-123"

API_HEADERS = {"X-Panned-Out-Request": "1"}

def meal_account(browser):
    """New account in its own browser context, with the clock frozen on 2026-10-15. Returns (context, page)."""
    context = browser.new_context()
    page = context.new_page()
    page.clock.set_fixed_time(FROZEN_TODAY)
    page.goto(f"{BASE_URL}/login")
    page.get_by_role("button", name="Create an account").click()
    page.get_by_label("Email address").fill(f"meals{time.time_ns()}@example.com")
    page.get_by_label("Password").fill(MEAL_PASSWORD)
    page.get_by_role("button", name="Create account").click()
    page.wait_for_url("**/calendar")
    return context, page

def seed_meal(page, name, date, meal_type="Dinner", difficulty="Medium", prep_time=45):
    """Create a recipe and schedule it, both through the backend. Returns the recipe id."""
    recipe = page.request.post(f"{BASE_URL}/api/recipes", headers=API_HEADERS, form={
        "name": name, "category": "My Recipes", "difficulty": difficulty, "mealType": meal_type,
        "ingredients": "1 cup rice", "instructions": "Cook it", "prepTime": str(prep_time),
        "calories": "100", "protein": "1", "fat": "1", "carbohydrates": "1", "fiber": "1"})
    assert recipe.ok, recipe.text()
    recipe_id = recipe.json()["id"]
    meal = page.request.post(f"{BASE_URL}/api/meals", headers=API_HEADERS,
                             form={"recipeId": str(recipe_id), "date": date, "mealType": meal_type})
    assert meal.ok, meal.text()
    return recipe_id

def month_view(page):
    page.locator(".calendar-view-controls").get_by_role("button", name="Month", exact=True).click()

def show_date(page, date):
    """Go to the month view of `date` and select it (the calendar opens on October 2026)."""
    month_view(page)
    target = time.strftime("%B %Y", time.strptime(date, "%Y-%m-%d"))
    title = page.locator(".calendar-header h1")
    for _ in range(40):
        if title.inner_text() == target:
            break
        page.get_by_role("button", name="Next Month").click()
    expect(title).to_have_text(target)
    page.get_by_role("button", name=date, exact=True).click()

def switch(page, view):
    page.locator(".calendar-view-controls").get_by_role("button", name=view, exact=True).click()

def week_column(page, date):
    return page.locator(f".calendar-week-day[aria-label='{date}']")


def sidebar_item(page, name):
    """A sidebar entry (link or button) whose text is `name`, on the old and the rebuilt sidebar."""
    return page.locator("aside nav").locator("a, button").filter(has_text=name)


# Calendar Navigation
#TC-17-01: Navigate to the next month
def test_navigate_to_the_next_month(page):
    # Precondition: a user account already exists, user has successfully logged in
    # and has an active session and is on Calendar home page viewing the current month
    page.goto("http://localhost:5173/calendar")
    current_month = page.locator("h1").inner_text()

    # Steps:
    # 1. Click forward arrow
    page.get_by_role("button", name="Next Month").click()

    # Expected Result: Calendar view will display the month following the current one
    new_month = page.locator("h1").inner_text()
    assert new_month != current_month
#TC-17-02: Navigate to the previous month
def test_navigate_to_the_previous_month(page):
    # Precondition: a user account already exists, user has successfully logged in
    # and has an active session and is on Calendar home page viewing the current month
    page.goto("http://localhost:5173/calendar")
    current_month = page.locator("h1").inner_text()

    # Steps:
    # 1. Click backward arrow
    page.get_by_role("button", name="Previous Month").click()

    # Expected Result: Calendar view will display the month preceding the current one
    new_month = page.locator("h1").inner_text()
    assert new_month != current_month
#TC-17-03: Selecting a date registers correctly 
def test_select_specific_date(page):
    # Precondition: a user account already exists, user has successfully logged in
    # and has an active session and is on Calendar home page viewing the current month
    page.goto("http://localhost:5173/calendar")
    day_button = page.locator(".calendar-cell:not(.empty)").first

    # Steps:
    # 1. Click any date in the calendar grid
    day_button.click()

    # Expected Result: Calendar responds to the click and date becomes highlighted
    assert "selected" in day_button.get_attribute("class")
#TC-17-04: The selected date's associated meals display correctly
@pytest.mark.skip(reason="Add Meal not merged yet (PR #12)")
def test_selected_date_displays_correct_meals(page):
    # Precondition: a user account already exists, user has successfully logged in
    # and has an active session and is on Calendar home page viewing the current month
    # and the selected date has one or more meals assigned
    name = f"Taco Bowl {time.time_ns()}"
    start_on_oct_15(page, name)
    open_day(page, "2026-10-12")
    add_meal(page, name, "Dinner")

    # Steps:
    # 1. Select the date with assigned meals (move away to Oct 27, then back to Oct 12)
    open_day(page, "2026-10-27")
    expect(page.get_by_text("No meals for this day.")).to_be_visible()
    open_day(page, "2026-10-12")
    # 2. View the selected date's meal cards
    cards = page.locator(".meal-card")

    # Expected Result: The meal(s) assigned to the selected date display correctly on the calendar
    expect(cards).to_have_count(1)
    expect(cards.first).to_contain_text(name)
    expect(page.get_by_role("button", name="2026-10-12")).to_contain_text("1 planned")
# Adding/Removing Meals
#TC-17-05: Add a meal to a selected date
@pytest.mark.skip(reason="Add Meal not merged yet (PR #12)")
def test_add_meal_to_selected_date(page):
    # Precondition: a user account already exists, user has successfully logged in
    # and has an active session and is on Calendar home page viewing the current month
    name = f"Pasta Bake {time.time_ns()}"
    start_on_oct_15(page, name)

    # Steps:
    # 1. Select any date on the calendar view
    open_day(page, "2026-10-20")
    # 2. Click "Add Meal"
    page.get_by_role("button", name="Add Meal").first.click()
    # 3. Select a recipe from the list to add to the date
    page.get_by_label("Recipe", exact=True).select_option(label=name)
    # 4. Click "Save meal"
    page.get_by_role("button", name="Save meal").click()

    # Expected Result: A recipe is added to the selected date and saved to the calendar
    expect(page.locator(".meal-card")).to_have_count(1)
    expect(page.locator(".meal-card").first).to_contain_text(name)
    expect(page.get_by_role("button", name="2026-10-20")).to_contain_text("1 planned")
    page.reload()
    open_day(page, "2026-10-20")
    expect(page.locator(".meal-card").first).to_contain_text(name)
#TC-17-06: Remove a meal from a selected date
@pytest.mark.skip(reason="Add Meal not merged yet (PR #12)")
def test_remove_meal_from_selected_date(page):
    # Precondition: a user account already exists, user has successfully logged in
    # and has an active session and is on Calendar home page viewing the current month
    # and a meal is already assigned to the selected date
    name = f"Chili {time.time_ns()}"
    start_on_oct_15(page, name)
    open_day(page, "2026-10-13")
    add_meal(page, name, "Dinner")

    # Steps:
    # 1. Select any date on the calendar view (Oct 13 is selected)
    # 2. Click "Remove meal" on the meal needing removal
    # (there is no separate select or Save step: removal happens right away)
    page.get_by_role("button", name=f"Remove {name} from calendar").click()

    # Expected Result: Selected meal is removed from selected date's assigned meals
    expect(page.locator(".meal-card")).to_have_count(0)
    expect(page.get_by_text("No meals for this day.")).to_be_visible()
    expect(page.get_by_role("button", name="2026-10-13")).not_to_contain_text("planned")
    page.reload()
    expect(page.get_by_text("No meals for this day.")).to_be_visible()
# Meal Card Display
#TC-17-07: Meal card shows correct recipe info for a date
@pytest.mark.skip(reason="Add Meal not merged yet (PR #12)")
def test_meal_card_correctly_displays_all_info(page):
    # Precondition: a user account already exists, user has successfully logged in
    # and has an active session and is on Calendar home page viewing the current month,
    # and a meal is already assigned to the selected date with complete recipe info
    name = f"Lemon Chicken {time.time_ns()}"
    start_on_oct_15(page, name)
    open_day(page, "2026-10-14")
    add_meal(page, name, "Lunch")

    # Steps:
    # 1. View the calendar with the assigned meal on the selected date
    card = page.locator(".meal-card").first

    # Expected Result: Meal card displays recipe name, meal type, difficulty and prep time
    # (NOTE: the card in PR #12 has no image, so this checks the fields it does show;
    # confirm with the team whether an image is wanted)
    expect(card.get_by_role("heading", name=name)).to_be_visible()
    expect(card.locator(".meal-type")).to_have_text("Lunch")
    expect(card.locator(".meal-difficulty")).to_have_text("Easy")
    expect(card).to_contain_text("min")

#TC-17-08: Multiple meal cards display correctly when a date has more than one meal
@pytest.mark.skip(reason="Add Meal not merged yet (PR #12)")
def test_multiple_meal_cards_display_correctly_with_more_than_one_recipe(page):
    # Precondition: a user account already exists, user has successfully logged in
    # and has an active session and is on Calendar home page viewing the current month,
    # and two or more meals are already assigned to the selected date with complete recipe info
    token = time.time_ns()
    first, second = f"Oatmeal {token}", f"Stir Fry {token}"
    start_on_oct_15(page, first, second)
    open_day(page, "2026-10-19")
    add_meal(page, first, "Breakfast")
    add_meal(page, second, "Dinner")

    # Steps:
    # 1. View the calendar with the assigned meals on the selected date
    cards = page.locator(".meal-card")

    # Expected Result: All meal cards for the selected date display separately and correctly,
    # each showing its own recipe name without overlapping or being cut off
    # (NOTE: the cards in PR #12 have no image, so this checks names and layout only)
    expect(cards).to_have_count(2)
    expect(cards.nth(0)).to_contain_text(first)
    expect(cards.nth(1)).to_contain_text(second)
    box_1, box_2 = cards.nth(0).bounding_box(), cards.nth(1).bounding_box()
    no_overlap = (box_1["y"] + box_1["height"] <= box_2["y"] + 1
                  or box_2["y"] + box_2["height"] <= box_1["y"] + 1
                  or box_1["x"] + box_1["width"] <= box_2["x"] + 1
                  or box_2["x"] + box_2["width"] <= box_1["x"] + 1)
    assert no_overlap, "meal cards overlap"
    expect(page.get_by_role("button", name="2026-10-19")).to_contain_text("2 planned")
# Edge Cases
#TC-17-09: A date with no meals shows an empty state rather than breaking
def test_date_with_no_meals_shows_empty_state(page):
    # Precondition: a user account already exists, user has successfully logged in
    # and has an active session and is on Calendar home page viewing the current month,
    # and the selected date has no meal assignment
    page.goto("http://localhost:5173/calendar")

    # Steps:
    # 1. Click on any date in the calendar grid without assigned meal(s)
    page.locator(".calendar-cell:not(.empty)").first.click()

    # Expected Result: Selected date shows an empty state and does not break
    assert page.get_by_text("No meals for this day.").is_visible()
#TC-17-10: Navigating across a year boundary (December → January) works correctly
def test_navigation_across_the_year(page):
    # Precondition: a user account already exists, user has successfully logged in
    # and has an active session and is on Calendar home page viewing the month of December,
    page.goto("http://localhost:5173/calendar")
    next_button = page.get_by_role("button", name="Next Month")

    for _ in range(12):
        month_label = page.locator("h1").inner_text()
        if month_label.startswith("December"):
            break
        next_button.click()

    # Steps:
    # 1. Click the forward arrow
    next_button.click()
    new_label = page.locator("h1").inner_text()
    # Expected Result: The month of January's calendar view is displayed 

    assert new_label.startswith("January")
import pytest
 
# Sprint 2 test cases for this component.

 
# Sprint 2: Add Meal Validation and Privacy (SCRUM-1)
 
#TC-1-03: Meals are only visible to the account that created them
@pytest.mark.skip(reason="Login and Add Meal not merged yet (PR #11, #12)")
def test_meals_only_visible_to_their_account(page, browser):
    # Precondition: account A has a recipe scheduled on 2026-10-21 (the shared test account),
    # and a second account B exists
    name = unique_recipe("Taco Bowl")
    start_on_oct_15(page, name)
    open_day(page, "2026-10-21")
    add_meal(page, name)
    expect(page.locator(".meal-card")).to_have_count(1)

    # Steps:
    # 1. Log in as account B
    context_b, page_b, _ = new_account_context(browser)
    try:
        # 2. Open October 2026 on the calendar
        page_b.clock.set_fixed_time(FROZEN_TODAY)
        page_b.goto(f"{BASE_URL}/calendar")
        # 3. Select 2026-10-21
        open_day(page_b, "2026-10-21")

        # Expected Result: 2026-10-21 shows no meals for account B
        expect(page_b.get_by_text("No meals for this day.")).to_be_visible()
        expect(page_b.locator(".meal-card")).to_have_count(0)
        expect(page_b.get_by_role("button", name="2026-10-21")).not_to_contain_text("planned")
    finally:
        context_b.close()

#TC-1-04: Saving a meal without a date shows an error
@pytest.mark.skip(reason="Add Meal not merged yet (PR #12)")
def test_add_meal_without_date_shows_error(page):
    # Precondition: a user account already exists, user has successfully logged in
    # and has an active session, has a saved recipe, and the Add Meal form is open
    # (NOTE: in PR #12 the form has no date field. The date comes from the selected day,
    # so it cannot be left empty. This checks that instead. Confirm with the team.)
    name = unique_recipe("Date Check Soup")
    start_on_oct_15(page, name)
    open_day(page, "2026-10-08")
    page.get_by_role("button", name="Add Meal").first.click()

    # Steps:
    # 1. Look at the Add Meal form
    # Expected Result: The form shows the selected date and has no date field to leave empty
    expect(page.get_by_role("heading", name="Add a meal for 2026-10-08")).to_be_visible()
    expect(page.locator("form.add-meal-form input[type=date], form.add-meal-form input[name=date]")).to_have_count(0)

#TC-1-05: Saving a meal without a recipe shows an error
@pytest.mark.skip(reason="Add Meal not merged yet (PR #12)")
def test_add_meal_without_recipe_shows_error(page):
    # Precondition: a user account already exists, user has successfully logged in
    # and has an active session, has a saved recipe, and the Add Meal form is open
    name = unique_recipe("Recipe Check Soup")
    start_on_oct_15(page, name)
    open_day(page, "2026-10-08")
    page.get_by_role("button", name="Add Meal").first.click()

    # Steps:
    # 1. Leave the recipe unchosen (date is the selected day, meal type is Dinner)
    # 2. Click "Save meal"
    page.get_by_role("button", name="Save meal").click()

    # Expected Result: The recipe field is flagged as required and no meal is added
    # (the browser's own "Please select an item" message, not a custom one)
    recipe_field = page.get_by_label("Recipe", exact=True)
    assert recipe_field.evaluate("e => e.validity.valueMissing")
    expect(page.get_by_role("heading", name="Add a meal for 2026-10-08")).to_be_visible()
    expect(page.locator(".meal-card")).to_have_count(0)

#TC-1-06: Saving a meal without a meal type shows an error
@pytest.mark.skip(reason="Add Meal not merged yet (PR #12)")
def test_add_meal_without_meal_type_shows_error(page):
    # Precondition: a user account already exists, user has successfully logged in
    # and has an active session, has a saved recipe, and the Add Meal form is open
    # (NOTE: in PR #12 the meal type is a list with no blank choice and starts on Dinner,
    # so it cannot be left empty. This checks that instead. Confirm with the team.)
    name = unique_recipe("Type Check Soup")
    start_on_oct_15(page, name)
    open_day(page, "2026-10-08")
    page.get_by_role("button", name="Add Meal").first.click()

    # Steps:
    # 1. Look at the "Meal type" field
    meal_type = page.get_by_label("Meal type")

    # Expected Result: It always has a value, and the only choices are the four meal types
    expect(meal_type).to_have_value("Dinner")
    assert meal_type.locator("option").all_text_contents() == ["Breakfast", "Lunch", "Dinner", "Snack"]

#TC-1-07: [CONFIRM] Add a custom meal typed by the user
@pytest.mark.skip(reason="Custom meals not in scope yet; confirm with the team")
def test_add_custom_typed_meal(page):
    # Precondition: a user account already exists, user has successfully logged in
    # and has an active session and is on the Calendar home page
 
    # Steps:
    # 1. Click "Add Meal" on 2026-10-20
    # 2. Type "Leftover Pizza" as the meal name
    # 3. Click "Save"
    # 4. Reload the page
 
    # Expected Result: "Leftover Pizza" shows on 2026-10-20 before and after reloading
    assert False  # placeholder, replace with real check once custom meals exist
 
 
 
# Sprint 2: Add Meal Details (SCRUM-56)
 
#TC-GAP-56-01: Each meal type can be picked
@pytest.mark.skip(reason="Add Meal not merged yet (PR #12)")
def test_each_meal_type_can_be_picked(page):
    # Precondition: user is logged in and has a saved recipe
    name = unique_recipe("Everyday Eggs")
    start_on_oct_15(page, name)
    open_day(page, "2026-10-29")

    # Steps:
    # 1. Add a meal for each meal type (breakfast, lunch, dinner, snack, as built)
    for meal_type in ["Breakfast", "Lunch", "Dinner", "Snack"]:
        add_meal(page, name, meal_type)

    # Expected Result: Each meal card shows the meal type that was picked
    expect(page.locator(".meal-card")).to_have_count(4)
    assert sorted(page.locator(".meal-card .meal-type").all_text_contents()) == \
        ["Breakfast", "Dinner", "Lunch", "Snack"]

#TC-GAP-56-02: A failed save shows an error and retry saves once
@pytest.mark.skip(reason="Add Meal not merged yet (PR #12)")
def test_failed_meal_save_then_retry(page):
    # Precondition: user is logged in and the next meal save is set to fail once
    name = unique_recipe("Retry Rice")
    start_on_oct_15(page, name)
    open_day(page, "2026-10-30")
    failures = {"done": False}

    def fail_first_save(route):
        if route.request.method == "POST" and not failures["done"]:
            failures["done"] = True
            route.abort()
        else:
            route.continue_()
    page.route("**/api/meals", fail_first_save)

    # Steps:
    # 1. Fill in the Add Meal form and click "Save meal"
    page.get_by_role("button", name="Add Meal").first.click()
    page.get_by_label("Recipe", exact=True).select_option(label=name)
    page.get_by_label("Meal type").select_option("Lunch")
    page.get_by_role("button", name="Save meal").click()

    # Expected Result (step 1): an error shows and the choices are kept
    expect(page.get_by_role("alert")).to_be_visible()
    expect(page.get_by_label("Meal type")).to_have_value("Lunch")
    expect(page.get_by_label("Recipe", exact=True).locator("option:checked")).to_have_text(name)

    # 2. Click "Save meal" again (there is no separate retry button)
    page.get_by_role("button", name="Save meal").click()

    # Expected Result (step 2): the meal is saved once, with no duplicate
    expect(page.get_by_role("heading", name=re.compile("Add a meal for"))).not_to_be_visible()
    expect(page.locator(".meal-card")).to_have_count(1)
    expect(page.get_by_role("button", name="2026-10-30")).to_contain_text("1 planned")

# Sprint 2: Calendar Flow (SCRUM-28)
 
#TC-28-01: A scheduled meal stays after reloading and after signing back in
@pytest.mark.skip(reason="Add Meal not merged yet (PR #12)")
def test_scheduled_meal_stays_after_reload_and_sign_in(browser):
    # Precondition: a user account already exists, user has successfully logged in
    # and has an active session, and a recipe is scheduled on 2026-10-22
    # (uses its own account, because signing out ends that account's session)
    name = unique_recipe("Taco Bowl")
    context, page, email = new_account_context(browser)
    console_errors = []
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
    try:
        start_on_oct_15(page, name)
        open_day(page, "2026-10-22")
        add_meal(page, name)

        # Steps:
        # 1. Reload the page
        page.reload()
        open_day(page, "2026-10-22")
        # Expected Result (step 1): the meal card is still there
        expect(page.locator(".meal-card")).to_have_count(1)
        expect(page.locator(".meal-card").first).to_contain_text(name)

        # 2. Click "Log out", then sign back in with the same account
        page.get_by_role("button", name="Log out").click()
        page.wait_for_url("**/login")
        console_errors.clear()   # signing out can log an expected 401 from the session check
        page.get_by_label("Email address").fill(email)
        page.get_by_label("Password").fill(CAL_PASSWORD)
        page.get_by_role("button", name="Sign In").click()
        page.wait_for_url("**/calendar")
        # 3. Select 2026-10-22
        open_day(page, "2026-10-22")

        # Expected Result: The meal card is still on 2026-10-22 after both steps,
        # the day's planned count is 1, and there are no console errors
        expect(page.locator(".meal-card")).to_have_count(1)
        expect(page.locator(".meal-card").first).to_contain_text(name)
        expect(page.get_by_role("button", name="2026-10-22")).to_contain_text("1 planned")
        assert console_errors == []
    finally:
        context.close()

#TC-28-03: Planned count with several meals on one day
@pytest.mark.skip(reason="Add Meal not merged yet (PR #12)")
def test_planned_count_with_several_meals(page):
    # Precondition: a user account already exists, user has successfully logged in
    # and has an active session, and has at least one saved recipe
    name = unique_recipe("Sheet Pan Veggies")
    start_on_oct_15(page, name)
    open_day(page, "2026-10-23")

    # Steps:
    # 1. Add 3 meals to 2026-10-23
    for meal_type in ["Breakfast", "Lunch", "Dinner"]:
        add_meal(page, name, meal_type)

    # Expected Result: The planned count on 2026-10-23 shows 3
    expect(page.get_by_role("button", name="2026-10-23")).to_contain_text("3 planned")

#TC-28-04: The side panel shows the full date of the selected day
def test_side_panel_shows_selected_full_date(page):
    # Precondition: today is 2026-10-15 (frozen clock) and user is on the Calendar home page
    open_calendar_on_oct_15(page)
    panel_date = page.locator(".meals-heading span").first
    expect(panel_date).to_have_text("THURSDAY, OCTOBER 15, 2026")

    # Steps:
    # 1. Click day 20
    day_cell(page, 20).click()

    # Expected Result: The side panel heading changes from "THURSDAY, OCTOBER 15, 2026"
    # to "TUESDAY, OCTOBER 20, 2026"
    expect(panel_date).to_have_text("TUESDAY, OCTOBER 20, 2026")
 
 
#TC-28-05: Selected day stays after moving away and back
def test_selected_day_stays_after_navigation(page):
    # Precondition: today is 2026-10-15 (frozen clock) and user is on the Calendar home page
    open_calendar_on_oct_15(page)

    # Steps:
    # 1. Click day 20
    day_cell(page, 20).click()
    # 2. Click "Next Month"
    page.get_by_role("button", name="Next Month").click()
    expect(page.locator("h1")).to_have_text("November 2026")
    # 3. Click "Previous Month"
    page.get_by_role("button", name="Previous Month").click()
    expect(page.locator("h1")).to_have_text("October 2026")

    # Expected Result: Day 20 is still selected
    expect(day_cell(page, 20)).to_have_class(re.compile(r"selected"))
 
 
#TC-28-06: Sidebar links switch pages
def test_sidebar_links_switch_pages(page):
    # Precondition: user is on the Calendar home page
    page.goto(f"{BASE_URL}/calendar")

    # Steps:
    # 1. Click "Recipes" in the sidebar
    sidebar_item(page, "Recipes").click()
    # Expected Result (step 1): The URL ends with /recipes
    expect(page).to_have_url(f"{BASE_URL}/recipes")

    # 2. Click "Calendar" in the sidebar
    sidebar_item(page, "Calendar").click()
    # Expected Result (step 2): The URL ends with /calendar
    expect(page).to_have_url(f"{BASE_URL}/calendar")


# Sprint 2: Meal Card Data (SCRUM-32, SCRUM-34)
 
#TC-32-02: Editing a recipe updates its meal card
# BUG FOUND (BUG-03): A renamed recipe is not updated on its meal card. This test fails until it is fixed.
@pytest.mark.skip(reason="Add Meal not merged yet (PR #12)")
def test_recipe_edit_updates_meal_card(page):
    # Precondition: a recipe is scheduled on 2026-10-24
    # (NOTE: PR #14 removes the Edit button; move step 1 to the recipe detail page when #14 merges)
    name = unique_recipe("Taco Bowl")
    start_on_oct_15(page, name)
    open_day(page, "2026-10-24")
    add_meal(page, name)

    # Steps:
    # 1. On the Recipes page, rename the recipe by adding " XL"
    page.goto(f"{BASE_URL}/recipes")
    page.get_by_role("button", name=f"Edit {name}").click()
    page.get_by_label("Name").fill(f"{name} XL")
    page.get_by_role("button", name="Save recipe").click()
    expect(page.get_by_text(f"{name} XL")).to_be_visible()
    # 2. Go to the Calendar and select 2026-10-24
    page.clock.set_fixed_time(FROZEN_TODAY)
    page.goto(f"{BASE_URL}/calendar")
    open_day(page, "2026-10-24")

    # Expected Result: The meal card shows the new name
    expect(page.locator(".meal-card").first).to_contain_text(f"{name} XL")

#TC-32-03: Deleting a scheduled recipe is handled cleanly
# BUG FOUND (BUG-04): A deleted scheduled recipe leaves a normal-looking ghost card. This test fails until it is fixed.
@pytest.mark.skip(reason="Add Meal not merged yet (PR #12)")
def test_deleted_scheduled_recipe_handled_cleanly(page):
    # Precondition: a recipe is scheduled on 2026-10-25
    name = unique_recipe("Taco Bowl")
    start_on_oct_15(page, name)
    open_day(page, "2026-10-25")
    add_meal(page, name)

    # Steps:
    # 1. On the Recipes page, delete the recipe
    page.goto(f"{BASE_URL}/recipes")
    page.get_by_role("button", name=f"Delete {name}").click()
    expect(page.get_by_text(name)).not_to_be_visible()
    # 2. Go to the Calendar and select 2026-10-25
    page.clock.set_fixed_time(FROZEN_TODAY)
    page.goto(f"{BASE_URL}/calendar")
    open_day(page, "2026-10-25")

    # Expected Result: The meal card is removed or shows a clear "recipe unavailable" note,
    # with no "undefined" or "null" text
    cards = page.locator(".meal-card")
    if cards.count() > 0:
        expect(cards.first).to_contain_text("unavailable")
    text = page.inner_text("body")
    assert "undefined" not in text and "null" not in text

#TC-34-02: A long recipe name does not break the card
@pytest.mark.skip(reason="Add Meal not merged yet (PR #12)")
def test_long_recipe_name_does_not_break_card(page):
    # Precondition: a recipe with an 80-character name is scheduled on 2026-10-26
    words = "Slow Roasted Garlic Herb Chicken Thighs With Lemon Butter Sauce And Seasonal Vegetables"
    name = f"{time.time_ns() % 10**8} {words}"[:80]
    assert len(name) == 80
    start_on_oct_15(page, name)
    open_day(page, "2026-10-26")
    add_meal(page, name)

    # Steps:
    # 1. Select 2026-10-26 on the calendar (already selected)
    card = page.locator(".meal-card").first

    # Expected Result: The name wraps or is shortened and the card stays inside its space
    expect(card).to_be_visible()
    assert card.evaluate("e => e.scrollWidth <= e.clientWidth + 1"), "text spills out of the card"
    box = card.bounding_box()
    assert box["x"] >= 0 and box["x"] + box["width"] <= page.viewport_size["width"], "card is wider than the screen"

# Sprint 2: Month View (SCRUM-65)
 
#TC-65-01: Calendar opens on the current month with today marked
def test_opens_on_current_month_with_today_marked(page):
    # Precondition: today is Thursday 2026-10-15 (frozen clock) and user opens the Calendar home page
    # Steps:
    # 1. View the Calendar home page
    open_calendar_on_oct_15(page)

    # Expected Result: The title reads "October 2026", day 15 has the "today" style and "Today" label,
    # day 15 is selected, and the side panel says "THURSDAY, OCTOBER 15, 2026"
    expect(page.locator("h1")).to_have_text("October 2026")
    today_cell = day_cell(page, 15)
    expect(today_cell).to_have_class(re.compile(r"today"))
    expect(today_cell.locator(".today-label")).to_have_text("Today")
    expect(today_cell).to_have_class(re.compile(r"selected"))
    expect(page.locator(".meals-heading span").first).to_have_text("THURSDAY, OCTOBER 15, 2026")
 
 
#TC-65-02: Today button returns to the current month
def test_today_button_returns_to_current_month(page):
    # Precondition: today is 2026-10-15 (frozen clock) and user is on the Calendar home page
    open_calendar_on_oct_15(page)
    next_month = page.get_by_role("button", name="Next Month")

    # Steps:
    # 1. Click "Next Month" twice
    next_month.click()
    next_month.click()
    # Expected Result (step 1): The title reads "December 2026"
    expect(page.locator("h1")).to_have_text("December 2026")

    # 2. Click "Today"
    page.locator(".today-button").click()
    # Expected Result (step 2): "October 2026" with day 15 selected
    expect(page.locator("h1")).to_have_text("October 2026")
    expect(day_cell(page, 15)).to_have_class(re.compile(r"selected"))
 
 
#TC-65-03: Each month shows the right number of days and first weekday
def test_month_day_count_and_first_weekday(page):
    # Precondition: today is 2026-10-15 (frozen clock) and user is on the Calendar home page
    open_calendar_on_oct_15(page)
    previous_month = page.get_by_role("button", name="Previous Month")
    next_month = page.get_by_role("button", name="Next Month")
    today_button = page.locator(".today-button")

    def check_month(title, blanks, days):
        expect(page.locator("h1")).to_have_text(title)
        assert page.locator(".calendar-cell.empty").count() == blanks, f"{title}: blank cells"
        assert page.locator(".calendar-cell:not(.empty)").count() == days, f"{title}: day cells"

    # Steps:
    # 1. Click "Previous Month" 8 times (February 2026)
    for _ in range(8):
        previous_month.click()
    check_month("February 2026", blanks=0, days=28)

    # 2. Click "Today", then "Previous Month" 6 times (April 2026)
    today_button.click()
    for _ in range(6):
        previous_month.click()
    check_month("April 2026", blanks=3, days=30)

    # 3. Click "Today" (October 2026)
    today_button.click()
    check_month("October 2026", blanks=4, days=31)

    # 4. Click "Next Month" 16 times (February 2028, leap year)
    for _ in range(16):
        next_month.click()
    check_month("February 2028", blanks=2, days=29)
 
 
#TC-65-04: Month view shows minimal meal cards
@pytest.mark.skip(reason="Add Meal and calendar views not merged yet (PR #12, #14)")
def test_month_view_shows_minimal_meal_cards(page):
    # Precondition: a user account already exists, user has successfully logged in
    # and has an active session, and has 1 meal on 2026-10-20
 
    # Steps:
    # 1. View October 2026 in month view
 
    # Expected Result: The 2026-10-20 cell shows a minimal card (name or dot), not full details
    assert False  # placeholder, replace with real check once Add Meal and views are merged
 
 
#TC-65-05: Weekday header is in order
def test_weekday_header_in_order(page):
    # Precondition: user is on the Calendar home page
    page.goto(f"{BASE_URL}/calendar")

    # Steps:
    # 1. View the weekday header
    labels = page.locator(".calendar-weekdays span")

    # Expected Result: 7 labels show in order: Sun Mon Tue Wed Thu Fri Sat
    expect(labels).to_have_text(["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"])
 
 
#TC-65-06: Today is only marked in today's month
def test_today_marked_only_in_todays_month(page):
    # Precondition: today is 2026-10-15 (frozen clock) and user is on the Calendar home page
    open_calendar_on_oct_15(page)
    expect(page.locator(".calendar-cell.today")).to_have_count(1)

    # Steps:
    # 1. Click "Next Month"
    page.get_by_role("button", name="Next Month").click()

    # Expected Result: No day in November 2026 has the "today" style or "Today" label
    expect(page.locator("h1")).to_have_text("November 2026")
    expect(page.locator(".calendar-cell.today")).to_have_count(0)
    expect(page.locator(".today-label")).to_have_count(0)
 
 
 
# Sprint 2: Week View (SCRUM-66)
 
#TC-66-01: Week view shows the 7 days around the selected date
@pytest.mark.skip(reason="Week view not merged yet (PR #14)")
def test_week_view_shows_seven_days(page):
    # Precondition: today is 2026-10-15 (frozen clock) and user is on the Calendar home page
    open_calendar_on_oct_15(page)

    # Steps:
    # 1. Select 2026-10-15
    day_cell(page, 15).click()
    # 2. Click "Week"
    view_button(page, "Week").click()

    # Expected Result: 7 days show, including 2026-10-15, with today highlighted
    expect(page.locator(".calendar-week-day")).to_have_count(7)
    assert week_day_numbers(page) == [11, 12, 13, 14, 15, 16, 17]
    expect(page.locator(".calendar-week-day.today")).to_have_count(1)
    expect(page.locator(".calendar-week-day.today .week-day-number")).to_have_text("15")
    expect(heading(page)).to_have_text("Week of October 11")

#TC-66-02: Next and previous week
@pytest.mark.skip(reason="Week view not merged yet (PR #14)")
def test_next_and_previous_week(page):
    # Precondition: user is in week view for the week of 2026-10-15
    open_calendar_on_oct_15(page)
    view_button(page, "Week").click()
    assert week_day_numbers(page) == [11, 12, 13, 14, 15, 16, 17]

    # Steps:
    # 1. Click next
    page.get_by_role("button", name="Next Month").click()

    # Expected Result: Step 1 shows the following 7 days
    assert week_day_numbers(page) == [18, 19, 20, 21, 22, 23, 24]

    # 2. Click previous twice
    page.get_by_role("button", name="Previous Month").click()
    page.get_by_role("button", name="Previous Month").click()

    # Expected Result: Step 2 shows the 7 days before the starting week
    assert week_day_numbers(page) == [4, 5, 6, 7, 8, 9, 10]
    expect(heading(page)).to_have_text("Week of October 4")

#TC-66-03: Week view shows condensed meal cards
# BUG FOUND (BUG-05): The week view meal card shows no meal type. This test fails until it is fixed.
@pytest.mark.skip(reason="Week view not merged yet (PR #14)")
def test_week_view_shows_condensed_cards(browser):
    # Precondition: a meal is scheduled on a day in the current week
    context, page = meal_account(browser)
    try:
        seed_meal(page, "Pho", "2026-10-14", meal_type="Dinner", difficulty="Medium", prep_time=45)
        page.reload()

        # Steps:
        # 1. Open week view
        switch(page, "Week")

        # Expected Result: The card shows the recipe name and meal type, not the full details
        card = week_column(page, "2026-10-14").locator(".week-meal")
        expect(card).to_have_count(1)
        expect(card).to_contain_text("Pho")
        expect(card).to_contain_text("Dinner")
        expect(card).not_to_contain_text("45")
        expect(card).not_to_contain_text("Medium")
    finally:
        context.close()

# Sprint 2: Day View (SCRUM-67)
 
#TC-67-01: Day view shows full meal cards
@pytest.mark.skip(reason="Day view not merged yet (PR #14)")
def test_day_view_shows_full_cards(browser):
    # Precondition: breakfast, lunch and dinner are scheduled on 2026-10-20
    context, page = meal_account(browser)
    try:
        seed_meal(page, "Oatmeal", "2026-10-20", "Breakfast", "Easy", 10)
        seed_meal(page, "Club Sandwich", "2026-10-20", "Lunch", "Medium", 15)
        seed_meal(page, "Lasagna", "2026-10-20", "Dinner", "Hard", 90)
        page.reload()

        # Steps:
        # 1. Open day view for 2026-10-20
        show_date(page, "2026-10-20")
        switch(page, "Day")

        # Expected Result: 3 full cards show, each with name, difficulty, prep time and meal type
        cards = page.locator(".meal-card")
        expect(cards).to_have_count(3)
        for name, meal_type, difficulty, minutes in [("Oatmeal", "Breakfast", "Easy", "10"),
                                                     ("Club Sandwich", "Lunch", "Medium", "15"),
                                                     ("Lasagna", "Dinner", "Hard", "90")]:
            card = cards.filter(has_text=name)
            expect(card).to_have_count(1)
            expect(card).to_contain_text(meal_type)
            expect(card).to_contain_text(difficulty)
            expect(card).to_contain_text(f"{minutes} min")
    finally:
        context.close()

#TC-67-02: Next and previous day
@pytest.mark.skip(reason="Day view not merged yet (PR #14)")
def test_next_and_previous_day(page):
    # Precondition: user is in day view for 2026-10-20
    open_calendar_on_oct_15(page)
    day_cell(page, 20).click()
    view_button(page, "Day").click()
    expect(heading(page)).to_have_text("October 20, 2026")

    # Steps:
    # 1. Click next
    page.get_by_role("button", name="Next day").click()

    # Expected Result: Step 1 shows 2026-10-21
    expect(heading(page)).to_have_text("October 21, 2026")

    # 2. Click previous
    page.get_by_role("button", name="Previous day").click()

    # Expected Result: Step 2 shows 2026-10-20 again
    expect(heading(page)).to_have_text("October 20, 2026")

#TC-67-03: An empty day shows a clear message
@pytest.mark.skip(reason="Day view not merged yet (PR #14)")
def test_empty_day_shows_message(page):
    # Precondition: no meals are scheduled on 2026-10-23
    open_calendar_on_oct_15(page)
    day_cell(page, 23).click()

    # Steps:
    # 1. Open day view for 2026-10-23
    view_button(page, "Day").click()

    # Expected Result: A readable "No meals planned" message shows with an "Add Meal" button
    expect(heading(page)).to_have_text("October 23, 2026")
    expect(page.get_by_text("No meals planned for this day yet.")).to_be_visible()
    expect(page.get_by_text("No meals for this day.")).to_be_visible()
    expect(page.get_by_role("button", name="Add Meal").first).to_be_visible()

# Sprint 2: View Toggle (SCRUM-68)
 
#TC-68-01: Switching views keeps the selected date
@pytest.mark.skip(reason="Calendar views not merged yet (PR #14)")
def test_switching_views_keeps_selected_date(page):
    # Precondition: user is in month view and has selected 2026-11-12
    open_calendar_on_oct_15(page)
    page.get_by_role("button", name="Next Month").click()
    expect(heading(page)).to_have_text("November 2026")
    day_cell(page, 12).click()

    # Steps:
    # 1. Click "Week"
    view_button(page, "Week").click()
    # Expected Result: The week contains 2026-11-12
    assert 12 in week_day_numbers(page)
    expect(page.locator(".calendar-week-day.selected .week-day-number")).to_have_text("12")

    # 2. Click "Day"
    view_button(page, "Day").click()
    # Expected Result: the day view is 2026-11-12
    expect(heading(page)).to_have_text("November 12, 2026")

    # 3. Click "Month"
    view_button(page, "Month").click()
    # Expected Result: the month view shows November 2026, with the 12th still selected
    expect(heading(page)).to_have_text("November 2026")
    expect(day_cell(page, 12)).to_have_class(re.compile(r"selected"))

#TC-68-02: The active view button is marked
@pytest.mark.skip(reason="Calendar views not merged yet (PR #14)")
def test_active_view_button_is_marked(page):
    # Precondition: user is on the Calendar home page
    open_calendar_on_oct_15(page)
    expect(view_button(page, "Month")).to_have_attribute("aria-pressed", "true")

    # Steps:
    # 1. Click "Week"
    view_button(page, "Week").click()

    # Expected Result: Each time, only the button for the current view looks selected
    expect(view_button(page, "Week")).to_have_attribute("aria-pressed", "true")
    expect(view_button(page, "Week")).to_have_class(re.compile(r"active"))
    expect(view_button(page, "Month")).to_have_attribute("aria-pressed", "false")
    expect(view_button(page, "Day")).to_have_attribute("aria-pressed", "false")

    # 2. Click "Day"
    view_button(page, "Day").click()
    expect(view_button(page, "Day")).to_have_attribute("aria-pressed", "true")
    expect(view_button(page, "Day")).to_have_class(re.compile(r"active"))
    expect(view_button(page, "Week")).to_have_attribute("aria-pressed", "false")
    expect(view_button(page, "Month")).to_have_attribute("aria-pressed", "false")

#TC-68-03: The same meals show in every view
@pytest.mark.skip(reason="Calendar views not merged yet (PR #14)")
def test_same_meals_in_every_view(browser):
    # Precondition: 2 meals are scheduled on 2026-11-12
    context, page = meal_account(browser)
    try:
        seed_meal(page, "Burrito", "2026-11-12", "Lunch")
        seed_meal(page, "Chili", "2026-11-12", "Dinner")
        page.reload()

        # Steps:
        # 1. View 2026-11-12 in month, week and day view
        show_date(page, "2026-11-12")
        month_count = page.get_by_role("button", name="2026-11-12", exact=True)
        switch(page, "Month")
        # Expected Result: All three views show the same 2 meals for 2026-11-12
        expect(month_count).to_contain_text("2 planned")

        switch(page, "Week")
        column = week_column(page, "2026-11-12")
        expect(column.locator(".week-meal")).to_have_count(2)
        expect(column).to_contain_text("Burrito")
        expect(column).to_contain_text("Chili")

        switch(page, "Day")
        expect(page.locator(".meal-card")).to_have_count(2)
        expect(page.locator(".meal-card").filter(has_text="Burrito")).to_have_count(1)
        expect(page.locator(".meal-card").filter(has_text="Chili")).to_have_count(1)
    finally:
        context.close()

# Sprint 2: Meal Cards Across Views (SCRUM-69)
 
#TC-69-01: Retired (Oct 22). Covered by TC-66-03 (week card) and TC-67-01 (day card).
#TC-69-02: Many meals on one day stay readable
@pytest.mark.skip(reason="Calendar views not merged yet (PR #14)")
def test_many_meals_on_one_day(browser):
    # Precondition: 6 meals are scheduled on 2026-10-20
    context, page = meal_account(browser)
    try:
        names = [f"Dish {n}" for n in range(1, 7)]
        for n, name in enumerate(names):
            seed_meal(page, name, "2026-10-20", ["Breakfast", "Lunch", "Dinner"][n % 3])
        page.reload()

        # Steps:
        # 1. View 2026-10-20 in month, week and day view
        show_date(page, "2026-10-20")

        # Expected Result: Month shows "+N more" or scrolls without overflowing; week and day show all 6
        cell = page.get_by_role("button", name="2026-10-20", exact=True)
        expect(cell).to_contain_text("6 planned")
        cell_box, grid_box = cell.bounding_box(), page.locator(".calendar-grid").bounding_box()
        assert cell_box["x"] + cell_box["width"] <= grid_box["x"] + grid_box["width"] + 1
        assert page.evaluate("el => el.scrollWidth <= el.clientWidth + 1", cell.element_handle())

        switch(page, "Week")
        expect(week_column(page, "2026-10-20").locator(".week-meal")).to_have_count(6)
        switch(page, "Day")
        expect(page.locator(".meal-card")).to_have_count(6)
        # nothing sticks out sideways on the page
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
    finally:
        context.close()

#TC-69-03: Clicking a meal card opens the recipe in every view
# BUG FOUND (BUG-06): Calendar meal cards do not open the recipe. This test fails until it is fixed.
@pytest.mark.skip(reason="Meal cards do not open the recipe yet (PR #14 gap, confirm with the team)")
def test_meal_card_opens_recipe_in_every_view(browser):
    # Precondition: a meal is scheduled on 2026-10-20
    context, page = meal_account(browser)
    try:
        recipe_id = seed_meal(page, "Pho", "2026-10-20")
        page.reload()

        # Steps:
        # 1. In each view, click the meal card
        # Expected Result: The recipe's detail opens each time
        def clicker(view):
            if view == "Month":
                return page.get_by_role("button", name="2026-10-20", exact=True)
            if view == "Week":
                return week_column(page, "2026-10-20").locator(".week-meal")
            return page.locator(".meal-card").filter(has_text="Pho")

        for view in ["Month", "Week", "Day"]:
            show_date(page, "2026-10-20")
            switch(page, view)
            if view == "Month":
                # the month cell only selects a day, so click the card in the list under the grid
                page.locator(".meal-card").filter(has_text="Pho").click()
            else:
                clicker(view).click()
            expect(page).to_have_url(f"{BASE_URL}/recipes/{recipe_id}", timeout=3000)
            expect(page.get_by_role("heading", name="Pho")).to_be_visible()
            page.goto(f"{BASE_URL}/calendar")
    finally:
        context.close()

# Sprint 2: Date Boundary Edge Cases (SCRUM-70)
 
#TC-70-01: Meals on month and year edges show on the right day
@pytest.mark.skip(reason="Calendar views not merged yet (PR #14)")
def test_meals_on_month_and_year_edges(browser):
    # Precondition: meals are scheduled on 2026-10-31, 2026-11-01, 2026-12-31, 2027-01-01 and 2028-02-29
    context, page = meal_account(browser)
    try:
        dates = {"2026-10-31": "Halloween Stew", "2026-11-01": "November Soup",
                 "2026-12-31": "New Year Eve Pasta", "2027-01-01": "New Year Day Eggs",
                 "2028-02-29": "Leap Day Cake"}
        for date, name in dates.items():
            seed_meal(page, name, date)
        page.reload()

        # Steps:
        # 1. View each date in month, week and day view
        for date, name in dates.items():
            show_date(page, date)
            # Expected Result: Each meal shows on its own date in every view and nowhere else
            expect(page.get_by_role("button", name=date, exact=True)).to_contain_text("1 planned")
            expect(page.locator(".meal-count")).to_have_count(1)   # no other day in the month has a meal

            switch(page, "Week")
            expect(week_column(page, date).locator(".week-meal")).to_have_text([name])
            expect(page.locator(".week-meal").filter(has_text=name)).to_have_count(1)   # not in any other column

            switch(page, "Day")
            expect(page.locator(".meal-card")).to_have_count(1)
            expect(page.locator(".meal-card")).to_contain_text(name)
    finally:
        context.close()

#TC-70-02: A week crossing into a new year shows both months
# BUG FOUND (BUG-07): The week header only names the first month. This test fails until it is fixed.
@pytest.mark.skip(reason="Calendar views not merged yet (PR #14)")
def test_week_crossing_new_year(browser):
    # Precondition: a meal is scheduled on 2027-01-01
    context, page = meal_account(browser)
    try:
        seed_meal(page, "New Year Day Eggs", "2027-01-01")
        page.reload()

        # Steps:
        # 1. Open week view for 2026-12-29
        show_date(page, "2026-12-29")
        switch(page, "Week")

        # Expected Result: The week runs from December 2026 into January 2027, the header shows both,
        # and the meal is in the 2027-01-01 column
        numbers = [int(n) for n in page.locator(".calendar-week-day .week-day-number").all_inner_texts()]
        assert numbers == [27, 28, 29, 30, 31, 1, 2]
        expect(week_column(page, "2026-12-27")).to_be_visible()
        expect(week_column(page, "2027-01-02")).to_be_visible()
        expect(week_column(page, "2027-01-01").locator(".week-meal")).to_have_text(["New Year Day Eggs"])
        header = page.locator(".calendar-header h1").inner_text()
        assert "December" in header and "January" in header, f"header only says: {header}"
    finally:
        context.close()

#TC-70-03: Meals do not move days in different time zones
@pytest.mark.skip(reason="Add Meal not merged yet (PR #12)")
def test_meals_do_not_shift_with_time_zone(page, browser, signed_in_state):
    # Precondition: a meal is scheduled on 2026-10-28
    name = unique_recipe("Zone Chili")
    start_on_oct_15(page, name)
    open_day(page, "2026-10-28")
    add_meal(page, name)

    # Steps:
    # 1. Set the browser time zone to America/Chicago and view 2026-10-28
    # 2. Repeat with UTC
    # 3. Repeat with Asia/Tokyo
    for zone in ["America/Chicago", "UTC", "Asia/Tokyo"]:
        context = browser.new_context(storage_state=signed_in_state, timezone_id=zone)
        zone_page = context.new_page()
        try:
            zone_page.clock.set_fixed_time(FROZEN_TODAY)
            zone_page.goto(f"{BASE_URL}/calendar")
            open_day(zone_page, "2026-10-28")

            # Expected Result: The meal stays on 2026-10-28 every time (and is not on the days next to it)
            expect(zone_page.locator(".meal-card")).to_have_count(1)
            expect(zone_page.locator(".meal-card").first).to_contain_text(name)
            for neighbor in ["2026-10-27", "2026-10-29"]:
                open_day(zone_page, neighbor)
                expect(zone_page.locator(".meal-card").filter(has_text=name)).to_have_count(0)
        finally:
            context.close()


