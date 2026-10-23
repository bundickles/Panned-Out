import pytest
import json
import re
import time
from playwright.sync_api import expect


BASE_URL = "http://localhost:5173"

SHOP_PASSWORD = "shopping-test-password-123"

FROZEN_TUESDAY = "2026-10-20T10:00:00"

WEEK = "start=2026-10-18&end=2026-10-24"

EMPTY_TEXT = "No ingredients found for these dates. Schedule meals in the Calendar to build your list."

API_HEADERS = {"X-Panned-Out-Request": "1"}

def new_account(browser, **context_args):
    """A brand new account in its own browser. Returns (context, page, email)."""
    context = browser.new_context(**context_args)
    page = context.new_page()
    email = f"shop{time.time_ns()}@example.com"
    page.goto(f"{BASE_URL}/login")
    page.get_by_role("button", name="Create an account").click()
    page.get_by_label("Email address").fill(email)
    page.get_by_label("Password").fill(SHOP_PASSWORD)
    page.get_by_role("button", name="Create account").click()
    page.wait_for_url("**/calendar")
    return context, page, email

def api_recipe(page, name, ingredients):
    response = page.request.post(f"{BASE_URL}/api/recipes", headers=API_HEADERS, form={
        "name": name, "category": "My Recipes", "difficulty": "Easy", "mealType": "Dinner",
        "ingredients": ingredients, "instructions": "Cook it", "prepTime": "10", "calories": "100",
        "protein": "1", "fat": "1", "carbohydrates": "1", "fiber": "1"})
    assert response.ok, response.text()
    return response.json()["id"]

def api_meal(page, recipe_id, date, meal_type="Dinner"):
    response = page.request.post(f"{BASE_URL}/api/meals", headers=API_HEADERS,
                                 form={"recipeId": str(recipe_id), "date": date, "mealType": meal_type})
    assert response.ok, response.text()

def seed_shared(page):
    """The shared precondition of TC-117 and TC-118: Omelet on 2026-10-19 and Fried Rice on 2026-10-21."""
    omelet = api_recipe(page, "Omelet", "2 eggs\nCheese")
    fried_rice = api_recipe(page, "Fried Rice", "Rice\n2 eggs\nPeas")
    api_meal(page, omelet, "2026-10-19", "Breakfast")
    api_meal(page, fried_rice, "2026-10-21", "Dinner")
    return {"Omelet": omelet, "Fried Rice": fried_rice}

def item_names(page):
    return page.locator(".shopping-item > div > strong").all_inner_texts()

def item(page, name):
    return page.locator(".shopping-item", has=page.locator("strong", has_text=re.compile(rf"^{re.escape(name)}$")))

def slow_shopping_list(page, seconds, only_if_url_has=""):
    """Make shopping list requests take `seconds` longer, without freezing the test itself.
    The delay is added inside the browser (a wrapper around fetch), so the page keeps running while it waits.
    `only_if_url_has` limits it to requests whose URL contains that text (for example "end=2026-10-20")."""
    script = """(() => {
        if (window.__slowShopping) return;
        window.__slowShopping = true;
        const realFetch = window.fetch.bind(window);
        window.fetch = (input, init) => {
            const url = typeof input === 'string' ? input : input.url;
            if (url.includes('/api/shopping-list') && url.includes(%s))
                return new Promise(resolve => setTimeout(resolve, %d)).then(() => realFetch(input, init));
            return realFetch(input, init);
        };
    })();""" % (json.dumps(only_if_url_has), int(seconds * 1000))
    page.add_init_script(script)   # applies to pages opened from now on
    page.evaluate(script)          # and to the page that is open now


# Shopping List Page (SCRUM-71)
#TC-71-02: Shopping List page requires login
@pytest.mark.skip(reason="Login and Shopping List page not merged yet (PR #11, #15)")
def test_shopping_list_requires_login(browser):
    # Precondition: user is signed out
    context = browser.new_context()
    page = context.new_page()
    try:
        # Steps:
        # 1. Go directly to /shopping
        page.goto(f"{BASE_URL}/shopping")

        # Expected Result: User is sent to the Login page and no shopping list shows
        expect(page).to_have_url(f"{BASE_URL}/login")
        expect(page.get_by_role("heading", name="Weekly Groceries")).to_have_count(0)
    finally:
        context.close()


#TC-71-03: Retired (Oct 22). The Shopping page now builds the list from the calendar (PR #15), so the manual list does not exist. See TC-117 and TC-118.

# Item Display (SCRUM-72)
#TC-72-02: Retired (Oct 22). The Shopping page now builds the list from the calendar (PR #15), so the manual list does not exist. See TC-117 and TC-118.

#TC-72-03: [CONFIRM] Quantity and unit show next to the name
@pytest.mark.skip(reason="Quantity and unit may not exist (SCRUM-57 says text only); confirm with the team")
def test_quantity_and_unit_show(page):
    # Precondition: a meal in the range uses an ingredient with a quantity and unit

    # Steps:
    # 1. Open the Shopping List page for that range

    # Expected Result: The quantity and unit show next to the item name
    assert False  # placeholder, replace with real check once quantity and unit are confirmed


# Check/Complete Item (SCRUM-73)
#TC-73-01: Retired (Oct 22). The Shopping page now builds the list from the calendar (PR #15), so the manual list does not exist. See TC-117 and TC-118.

#TC-73-02: Checked items stay checked after reload and re-login
@pytest.mark.skip(reason="Purchased status UI not merged yet (PR #13, #14)")
def test_checked_item_survives_reload_and_relogin(page):
    # Precondition: user is logged in and a saved shopping list with "eggs" is open

    # Steps:
    # 1. Check "eggs"
    # 2. Reload the page
    # 3. Log out and log back in, then open the same list

    # Expected Result: "eggs" is still purchased after steps 2 and 3
    assert False  # placeholder, replace with real check once purchased status is merged

#TC-73-03: Retired (Oct 22). The Shopping page now builds the list from the calendar (PR #15), so the manual list does not exist. See TC-117 and TC-118.

#TC-73-04: A failed save does not leave a wrong checkbox
@pytest.mark.skip(reason="Purchased status UI not merged yet (PR #13, #14)")
def test_failed_check_save_shows_error(page):
    # Precondition: a saved shopping list is open and the server is set to fail the update

    # Steps:
    # 1. Check an item

    # Expected Result: The checkbox goes back or an error shows; it never silently looks saved
    assert False  # placeholder, replace with real check once purchased status is merged


# Remove Item (SCRUM-74)
#TC-74-01: Retired (Oct 22). The Shopping page now builds the list from the calendar (PR #15), so the manual list does not exist. See TC-117 and TC-118.

#TC-74-02: [CONFIRM] Removed item after reloading
@pytest.mark.skip(reason="Removal may not be saved (SCRUM-59 out of scope); confirm with the team")
def test_removed_item_after_reload(page):
    # Precondition: user just removed "milk" from the list

    # Steps:
    # 1. Reload the page

    # Expected Result: Matches what the team decides (stays removed or comes back)
    assert False  # placeholder, replace with real check once the team decides

#TC-74-03: Retired (Oct 22). The Shopping page now builds the list from the calendar (PR #15), so the manual list does not exist. See TC-117 and TC-118.

# Empty, Loading and Error States (SCRUM-75)
#TC-75-02: Retired (Oct 22). Folded into TC-118-06 (error is not the empty or loading message).

# Generate from Meal Plan: Happy Path (SCRUM-117)
# "Generate Meal Plan" (SCRUM-92) is the "Generate from Meal Plan" button on this page.
# Shared precondition for TC-117-xx and TC-118-xx: a user account already exists, user has successfully
# logged in and has an active session; recipe "Omelet" (ingredients "2 eggs", "Cheese") is scheduled on
# 2026-10-19 and recipe "Fried Rice" (ingredients "Rice", "2 eggs", "Peas") is scheduled on 2026-10-21
#TC-117-01: Shopping List page opens with this week's list
@pytest.mark.skip(reason="Shopping list generation not merged yet (PR #15)")
def test_page_opens_with_this_weeks_list(browser):
    # Precondition: shared precondition, and today is Tuesday 2026-10-20 (frozen clock)
    context, page, _ = new_account(browser)
    try:
        seed_shared(page)
        page.clock.set_fixed_time(FROZEN_TUESDAY)
        slow_shopping_list(page, 1.0)

        # Steps:
        # 1. Open /shopping
        page.goto(f"{BASE_URL}/shopping")

        # Expected Result: "Weekly Groceries" shows, Start date is 2026-10-18 and End date is 2026-10-24,
        # and "Loading shopping list..." shows before the "Ingredients" list appears
        expect(page.get_by_role("heading", level=1, name="Weekly Groceries")).to_be_visible()
        expect(page.get_by_label("Start date")).to_have_value("2026-10-18")
        expect(page.get_by_label("End date")).to_have_value("2026-10-24")
        expect(page.get_by_text("Loading shopping list...")).to_be_visible()
        expect(page.get_by_role("heading", name="Ingredients")).to_be_visible()
        expect(page.get_by_text("Loading shopping list...")).to_have_count(0)
    finally:
        context.close()


#TC-117-02: Items come from the meals in the range
@pytest.mark.skip(reason="Shopping list generation not merged yet (PR #15)")
def test_items_come_from_meals_in_range(browser):
    # Precondition: shared precondition
    context, page, _ = new_account(browser)
    try:
        seed_shared(page)

        # Steps:
        # 1. Open /shopping?start=2026-10-18&end=2026-10-24
        page.goto(f"{BASE_URL}/shopping?{WEEK}")

        # Expected Result: Items are "2 eggs", "Cheese", "Rice" and "Peas"; "2 eggs" shows "2 occurrences"
        # with "Omelet — 2026-10-19" and "Fried Rice — 2026-10-21"; "Cheese" shows "1 occurrence"
        expect(page.locator(".shopping-item")).to_have_count(4)
        assert sorted(item_names(page)) == ["2 eggs", "Cheese", "Peas", "Rice"]
        eggs = item(page, "2 eggs")
        expect(eggs).to_contain_text("2 occurrences")
        expect(eggs).to_contain_text("Omelet — 2026-10-19")
        expect(eggs).to_contain_text("Fried Rice — 2026-10-21")
        expect(item(page, "Cheese")).to_contain_text("1 occurrence")
        expect(item(page, "Cheese")).not_to_contain_text("1 occurrences")
    finally:
        context.close()


#TC-117-03: Generate from Meal Plan refreshes the list
@pytest.mark.skip(reason="Shopping list generation not merged yet (PR #15)")
def test_generate_button_refreshes_list(browser):
    # Precondition: shared precondition, and /shopping?start=2026-10-18&end=2026-10-24 is open
    context, page, _ = new_account(browser)
    try:
        ids = seed_shared(page)
        page.goto(f"{BASE_URL}/shopping?{WEEK}")
        expect(item(page, "2 eggs")).to_contain_text("2 occurrences")

        # Steps:
        # 1. In another tab, schedule "Omelet" on 2026-10-22
        other_tab = context.new_page()
        api_meal(other_tab, ids["Omelet"], "2026-10-22", "Dinner")
        other_tab.close()

        # 2. Click "Generate from Meal Plan"
        page.get_by_role("button", name="Generate from Meal Plan").click()

        # Expected Result: "2 eggs" now shows "3 occurrences" without reloading the page
        expect(item(page, "2 eggs")).to_contain_text("3 occurrences")
    finally:
        context.close()


#TC-117-04: Changing a date updates the list
@pytest.mark.skip(reason="Shopping list generation not merged yet (PR #15)")
def test_changing_date_updates_list(browser):
    # Precondition: shared precondition, and /shopping?start=2026-10-18&end=2026-10-24 is open
    context, page, _ = new_account(browser)
    try:
        seed_shared(page)
        page.goto(f"{BASE_URL}/shopping?{WEEK}")
        expect(page.locator(".shopping-item")).to_have_count(4)

        # Steps:
        # 1. Change End date to 2026-10-20
        page.get_by_label("End date").fill("2026-10-20")

        # Expected Result: Only Omelet's items ("2 eggs", "Cheese") show and the URL has end=2026-10-20
        expect(page.locator(".shopping-item")).to_have_count(2)
        assert sorted(item_names(page)) == ["2 eggs", "Cheese"]
        expect(page).to_have_url(re.compile(r"end=2026-10-20"))
    finally:
        context.close()


#TC-117-05: The chosen range stays after reloading
@pytest.mark.skip(reason="Shopping list generation not merged yet (PR #15)")
def test_chosen_range_stays_after_reload(browser):
    # Precondition: shared precondition, and user is on /shopping
    context, page, _ = new_account(browser)
    try:
        seed_shared(page)
        page.goto(f"{BASE_URL}/shopping?{WEEK}")

        # Steps:
        # 1. Set Start date and End date to 2026-10-19
        page.get_by_label("End date").fill("2026-10-19")
        page.get_by_label("Start date").fill("2026-10-19")
        expect(page.locator(".shopping-item")).to_have_count(2)
        # 2. Reload the page
        page.reload()

        # Expected Result: The same dates are in the boxes and the same items show
        expect(page.get_by_label("Start date")).to_have_value("2026-10-19")
        expect(page.get_by_label("End date")).to_have_value("2026-10-19")
        expect(page.locator(".shopping-item")).to_have_count(2)
        assert sorted(item_names(page)) == ["2 eggs", "Cheese"]
    finally:
        context.close()


#TC-117-06: View Calendar link opens the calendar
@pytest.mark.skip(reason="Shopping list generation not merged yet (PR #15)")
def test_view_calendar_link(browser):
    # Precondition: shared precondition, and user is on /shopping
    context, page, _ = new_account(browser)
    try:
        page.goto(f"{BASE_URL}/shopping?{WEEK}")

        # Steps:
        # 1. Click "View Calendar →"
        page.get_by_role("link", name="View Calendar").click()

        # Expected Result: The URL ends with /calendar
        expect(page).to_have_url(re.compile(r"/calendar$"))
    finally:
        context.close()


# Generate from Meal Plan: Edge Cases (SCRUM-118)
#TC-118-01: No meals in the range shows the empty message
@pytest.mark.skip(reason="Shopping list generation not merged yet (PR #15)")
def test_no_meals_in_range_shows_empty_message(browser):
    # Precondition: shared precondition
    context, page, _ = new_account(browser)
    try:
        seed_shared(page)

        # Steps:
        # 1. Open /shopping?start=2026-12-01&end=2026-12-07
        page.goto(f"{BASE_URL}/shopping?start=2026-12-01&end=2026-12-07")

        # Expected Result: "No ingredients found for these dates. Schedule meals in the Calendar to build
        # your list." shows
        expect(page.get_by_text(EMPTY_TEXT)).to_be_visible()
        expect(page.locator(".shopping-item")).to_have_count(0)
    finally:
        context.close()


#TC-118-02: Start date after end date is blocked
@pytest.mark.skip(reason="Shopping list generation not merged yet (PR #15)")
def test_start_after_end_is_blocked(browser):
    # Precondition: shared precondition, and user is on /shopping
    context, page, _ = new_account(browser)
    try:
        seed_shared(page)
        page.goto(f"{BASE_URL}/shopping?{WEEK}")
        expect(page.locator(".shopping-item")).to_have_count(4)
        list_requests = []
        page.on("request", lambda request: list_requests.append(request.url) if "/api/shopping-list" in request.url else None)

        # Steps:
        # 1. Set Start date to 2026-10-25
        page.get_by_label("Start date").fill("2026-10-25")
        # 2. Set End date to 2026-10-19
        page.get_by_label("End date").fill("2026-10-19")

        # Expected Result: "Start date must be on or before end date." shows, "Generate from Meal Plan"
        # is disabled, and no list request is sent
        expect(page.get_by_role("alert")).to_have_text("Start date must be on or before end date.")
        expect(page.get_by_role("button", name="Generate from Meal Plan")).to_be_disabled()
        page.wait_for_timeout(500)
        assert list_requests == [], f"list requests were sent: {list_requests}"
    finally:
        context.close()


#TC-118-03: An impossible date in the URL is blocked
@pytest.mark.skip(reason="Shopping list generation not merged yet (PR #15)")
def test_impossible_date_in_url_is_blocked(browser):
    # Precondition: shared precondition
    context, page, _ = new_account(browser)
    try:
        list_requests = []
        page.on("request", lambda request: list_requests.append(request.url) if "/api/shopping-list" in request.url else None)

        # Steps:
        # 1. Open /shopping?start=2026-02-30&end=2026-03-05
        page.goto(f"{BASE_URL}/shopping?start=2026-02-30&end=2026-03-05")

        # Expected Result: "Choose valid start and end dates." shows and the button is disabled
        expect(page.get_by_role("alert")).to_have_text("Choose valid start and end dates.")
        expect(page.get_by_role("button", name="Generate from Meal Plan")).to_be_disabled()
        assert list_requests == []
    finally:
        context.close()


#TC-118-04: A single-day range uses only that day
@pytest.mark.skip(reason="Shopping list generation not merged yet (PR #15)")
def test_single_day_range(browser):
    # Precondition: shared precondition
    context, page, _ = new_account(browser)
    try:
        seed_shared(page)

        # Steps:
        # 1. Open /shopping?start=2026-10-21&end=2026-10-21
        page.goto(f"{BASE_URL}/shopping?start=2026-10-21&end=2026-10-21")

        # Expected Result: Only Fried Rice's items show
        expect(page.locator(".shopping-item")).to_have_count(3)
        assert sorted(item_names(page)) == ["2 eggs", "Peas", "Rice"]
        expect(item(page, "2 eggs")).to_contain_text("1 occurrence")
        expect(page.locator(".shopping-item", has_text="Omelet")).to_have_count(0)
    finally:
        context.close()


#TC-118-05: A deleted recipe shows a warning
@pytest.mark.skip(reason="Shopping list generation not merged yet (PR #15)")
def test_deleted_recipe_shows_warning(browser):
    # Precondition: shared precondition, then the recipe "Fried Rice" is deleted (its meal stays scheduled)
    context, page, _ = new_account(browser)
    try:
        ids = seed_shared(page)
        response = page.request.delete(f"{BASE_URL}/api/recipes/{ids['Fried Rice']}", headers=API_HEADERS)
        assert response.ok, response.text()

        # Steps:
        # 1. Open /shopping?start=2026-10-18&end=2026-10-24
        page.goto(f"{BASE_URL}/shopping?{WEEK}")

        # Expected Result: "Some ingredients are unavailable" lists Fried Rice and its date, and
        # Omelet's items are still listed
        warning = page.get_by_label("Missing recipes")
        expect(warning.get_by_role("heading", name="Some ingredients are unavailable")).to_be_visible()
        expect(warning).to_contain_text("Fried Rice")
        expect(warning).to_contain_text("2026-10-21")
        assert sorted(item_names(page)) == ["2 eggs", "Cheese"]
    finally:
        context.close()


#TC-118-06: Server error shows Retry and keeps the dates
@pytest.mark.skip(reason="Shopping list generation not merged yet (PR #15)")
def test_server_error_shows_retry(browser):
    # Precondition: shared precondition, and the shopping list request is set to fail
    context, page, _ = new_account(browser)
    try:
        seed_shared(page)
        page.route("**/api/shopping-list*", lambda route: route.fulfill(
            status=500, content_type="application/json", body=json.dumps({"error": "Something went wrong"})))

        # Steps:
        # 1. Open /shopping
        page.goto(f"{BASE_URL}/shopping?start=2026-10-19&end=2026-10-23")

        # Expected Result: Step 1 shows an error with "Retry" and keeps the chosen dates
        expect(page.get_by_role("alert")).to_contain_text("Something went wrong")
        expect(page.get_by_role("button", name="Retry")).to_be_visible()
        expect(page.get_by_label("Start date")).to_have_value("2026-10-19")
        expect(page.get_by_label("End date")).to_have_value("2026-10-23")
        # The error is its own message: not the empty-list text and not the loading text (TC-75-02)
        expect(page.get_by_text(EMPTY_TEXT)).to_have_count(0)
        expect(page.get_by_text("Loading shopping list...")).to_have_count(0)

        # 2. Fix the server and click "Retry"
        page.unroute("**/api/shopping-list*")
        page.get_by_role("button", name="Retry").click()

        # Expected Result: step 2 loads the list
        expect(page.locator(".shopping-item")).to_have_count(4)
        expect(page.get_by_role("button", name="Retry")).to_have_count(0)
    finally:
        context.close()


#TC-118-07: Quantities are not combined
@pytest.mark.skip(reason="Shopping list generation not merged yet (PR #15)")
def test_quantities_not_combined(browser):
    # Precondition: shared precondition, plus a recipe with "3 eggs" scheduled on 2026-10-22
    context, page, _ = new_account(browser)
    try:
        seed_shared(page)
        scramble = api_recipe(page, "Scramble", "3 eggs")
        api_meal(page, scramble, "2026-10-22", "Dinner")

        # Steps:
        # 1. Open /shopping?start=2026-10-18&end=2026-10-24
        page.goto(f"{BASE_URL}/shopping?{WEEK}")

        # Expected Result: "2 eggs" and "3 eggs" show as separate items
        names = item_names(page)
        assert "2 eggs" in names and "3 eggs" in names, names
        expect(item(page, "3 eggs")).to_contain_text("1 occurrence")
        expect(item(page, "2 eggs")).to_contain_text("2 occurrences")
    finally:
        context.close()


#TC-118-08: Another account never sees my list
@pytest.mark.skip(reason="Login and generation not merged yet (PR #11, #15)")
def test_other_account_never_sees_my_list(browser):
    # Precondition: shared precondition, and a second account B exists with no meals
    context_b, page_b, email_b = new_account(browser)
    context_b.close()
    context, page, _ = new_account(browser)
    try:
        seed_shared(page)
        page.goto(f"{BASE_URL}/shopping?{WEEK}")
        expect(page.locator(".shopping-item")).to_have_count(4)
        bodies = []
        page.on("response", lambda response: bodies.append(response.text())
                if "/api/shopping-list" in response.url else None)

        # Steps:
        # 1. Log out
        page.get_by_role("button", name="Log out").click()
        page.wait_for_url("**/login")
        # 2. Log in as account B and open /shopping?start=2026-10-18&end=2026-10-24
        page.get_by_label("Email address").fill(email_b)
        page.get_by_label("Password").fill(SHOP_PASSWORD)
        page.get_by_role("button", name="Sign In").click()
        page.wait_for_url("**/calendar")
        page.goto(f"{BASE_URL}/shopping?{WEEK}")

        # Expected Result: The empty-list message shows and none of the first account's items appear, even briefly
        expect(page.get_by_text(EMPTY_TEXT)).to_be_visible()
        text = page.locator("body").inner_text()
        for mine in ("Omelet", "Fried Rice", "Cheese", "Peas", "Rice"):
            assert mine not in text, f"'{mine}' showed for account B"
        assert bodies, "no list response was captured"
        for body in bodies:
            assert "Omelet" not in body and "Fried Rice" not in body, "account B's response held account A's meals"
    finally:
        context.close()


#TC-118-09: Fast date changes end on the last range picked
@pytest.mark.skip(reason="Shopping list generation not merged yet (PR #15)")
def test_fast_date_changes_show_last_range(browser):
    # Precondition: shared precondition, the server responds slowly, and user is on /shopping
    context, page, _ = new_account(browser)
    try:
        seed_shared(page)
        page.goto(f"{BASE_URL}/shopping?{WEEK}")
        expect(page.locator(".shopping-item")).to_have_count(4)

        # the first answer (end 2026-10-20) is slower than the second one, so it would arrive last
        slow_shopping_list(page, 1.5, only_if_url_has="end=2026-10-20")

        # Steps:
        # 1. Change End date to 2026-10-20
        page.get_by_label("End date").fill("2026-10-20")
        # 2. Quickly change End date to 2026-10-24
        page.get_by_label("End date").fill("2026-10-24")

        # Expected Result: The final list matches 2026-10-18 to 2026-10-24 (the older answer does not win)
        expect(page.locator(".shopping-item")).to_have_count(4)
        page.wait_for_timeout(2500)
        expect(page.locator(".shopping-item")).to_have_count(4)
        expect(page.get_by_label("End date")).to_have_value("2026-10-24")
    finally:
        context.close()


# Add Item and Grocery Sections (SCRUM-81, SCRUM-49)
#TC-GAP-81-01: [CONFIRM] Add an item by hand
@pytest.mark.skip(reason="Shopping List UI not merged yet (PR #14); confirm if added items are saved")
def test_add_item_by_hand(page):
    # Precondition: user is on the Shopping List page

    # Steps:
    # 1. Click "Add item"
    # 2. Type "paper towels"
    # 3. Click "Save"

    # Expected Result: "paper towels" shows in the list (and after reloading, if added items are saved)
    assert False  # placeholder, replace with real check once the Shopping List UI is merged

#TC-GAP-81-02: Retired (Oct 22). The Shopping page now builds the list from the calendar (PR #15), so the manual list does not exist. See TC-117 and TC-118.

#TC-GAP-81-03: Retired (Oct 22). The Shopping page now builds the list from the calendar (PR #15), so the manual list does not exist. See TC-117 and TC-118.

# Save and Reopen a List (SCRUM-59)
#TC-GAP-59-01: Save a shopping list
@pytest.mark.skip(reason="Save list button not built yet")
def test_save_shopping_list(page):
    # Precondition: user is logged in and a shopping list is showing for a range

    # Steps:
    # 1. Click "Save list"

    # Expected Result: A success message shows and the list appears in saved lists
    assert False  # placeholder, replace with real check once the Save list button exists

#TC-GAP-59-02: A saved list reopens unchanged
@pytest.mark.skip(reason="Save list button not built yet")
def test_saved_list_reopens_unchanged(page):
    # Precondition: user has saved a shopping list

    # Steps:
    # 1. Log out and log back in
    # 2. Open the saved list

    # Expected Result: The same items, counts, range and warnings show as when it was saved
    assert False  # placeholder, replace with real check once the Save list button exists


# Expired Session (SCRUM-57)
#TC-GAP-57-01: Expired session sends the user to login
@pytest.mark.skip(reason="Login and Shopping List integration not merged yet (PR #11, #15)")
def test_expired_session_goes_to_login(browser):
    # Precondition: user is on the Shopping List page and the session cookie expires
    context, page, email = new_account(browser)
    try:
        seed_shared(page)
        page.goto(f"{BASE_URL}/shopping?{WEEK}")
        expect(page.locator(".shopping-item")).to_have_count(4)
        context.clear_cookies()

        # Steps:
        # 1. Change a date
        page.get_by_label("End date").fill("2026-10-23")

        # Expected Result: User is sent to the Login page, and after logging in no old or broken list shows
        expect(page).to_have_url(f"{BASE_URL}/login")
        page.get_by_label("Email address").fill(email)
        page.get_by_label("Password").fill(SHOP_PASSWORD)
        page.get_by_role("button", name="Sign In").click()
        page.wait_for_url("**/calendar")
        page.goto(f"{BASE_URL}/shopping?{WEEK}")
        expect(page.locator(".shopping-item")).to_have_count(4)
        expect(page.get_by_role("alert")).to_have_count(0)
    finally:
        context.close()


