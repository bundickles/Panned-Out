import pytest
from playwright.sync_api import expect
import time


BASE_URL = "http://localhost:5173"

def open_plans(page):
    page.goto(f"{BASE_URL}/meal-plans")
    expect(page.get_by_role("heading", level=1, name="Find Your Perfect Plate")).to_be_visible()

def create_plan(page, name, description=""):
    page.get_by_role("button", name="+ Create New Plan").click()
    page.get_by_label("Plan Name").fill(name)
    if description:
        page.get_by_label("Description").fill(description)
    page.get_by_role("button", name="Create Plan").click()

def plan_card(page, name):
    return page.locator(".meal-plan-card", has=page.get_by_role("heading", name=name))


# Meal Plans Pages (SCRUM-85)
#TC-GAP-85-01: Each meal plan page opens with its sections
@pytest.mark.skip(reason="Meal Plans pages not merged yet (PR #14)")
def test_each_meal_plan_page_opens(page):
    # Precondition: a user account already exists, user has successfully logged in
    # and has an active session
    page.goto(f"{BASE_URL}/meal-plans")
    expect(page.get_by_role("heading", level=1, name="Find Your Perfect Plate")).to_be_visible()

    # Steps:
    # 1. Click the Keto plan card
    # 2. Repeat for the Low Calorie and High Protein plan cards
    for name in ("Keto", "Low Calorie", "High Protein"):
        page.locator(".meal-plan-card", has=page.get_by_role("heading", name=name)).click()

        # Expected Result: Each plan page shows its title and description (the page has no weekly macros
        # or recipes section yet), with no "undefined" or "null" text
        dialog = page.get_by_role("dialog")
        expect(dialog.get_by_role("heading", name=name)).to_be_visible()
        expect(dialog.locator("p").first).not_to_be_empty()
        text = dialog.inner_text()
        assert "undefined" not in text and "null" not in text
        dialog.get_by_role("button", name="Close").click()
        expect(dialog).to_have_count(0)


#TC-GAP-85-02: Weekly macros show units and sensible numbers
@pytest.mark.skip(reason="Meal Plans pages not merged yet (PR #14)")
def test_weekly_macros_sensible(page):
    # Precondition: user is logged in

    # Steps:
    # 1. Open the Keto plan page and note the carbs
    # 2. Open the High Protein plan page and note the carbs

    # Expected Result: Protein, carbs and fat show in grams with no negative numbers, and Keto
    # carbs are lower than High Protein carbs
    assert False  # placeholder, replace with real check once Meal Plans is merged

#TC-GAP-85-03: A recipe in a plan opens its detail
@pytest.mark.skip(reason="Meal Plans pages not merged yet (PR #14)")
def test_plan_recipe_opens_detail(page):
    # Precondition: user is on a meal plan page

    # Steps:
    # 1. Click a recipe in the plan's recipes section
    # 2. Click "Back"

    # Expected Result: The recipe detail opens, and Back returns to the plan page
    assert False  # placeholder, replace with real check once Meal Plans is merged

#TC-GAP-85-04: [CONFIRM] Customizing a plan
@pytest.mark.skip(reason="Meal Plans pages not merged yet (PR #14); confirm if changes are saved")
def test_customize_plan(page):
    # Precondition: user is on a meal plan page

    # Steps:
    # 1. Change one customization option
    # 2. Reload the page

    # Expected Result: The change shows, and stays after reloading if it is meant to be saved
    assert False  # placeholder, replace with real check once Meal Plans is merged

#TC-GAP-85-05: Meal plan pages work at phone, tablet and desktop widths
@pytest.mark.skip(reason="Meal Plans pages not merged yet (PR #14)")
@pytest.mark.parametrize("width,height", [(375, 812), (768, 1024), (1440, 900)])
def test_meal_plan_pages_responsive(page, width, height):
    # Precondition: user is on a meal plan page
    page.set_viewport_size({"width": width, "height": height})
    page.goto(f"{BASE_URL}/meal-plans")

    # Steps:
    # 1. View the page at 375, 768 and 1440 pixels wide
    # Expected Result: Content is readable with no sideways scrolling at every width
    expect(page.get_by_role("heading", level=1, name="Find Your Perfect Plate")).to_be_visible()
    expect(page.locator(".meal-plan-card")).to_have_count(4)
    widths = page.evaluate("() => ({scroll: document.documentElement.scrollWidth, view: document.documentElement.clientWidth})")
    assert widths["scroll"] <= widths["view"], f"page scrolls sideways at {width}px: {widths}"

    # The plan pop-up also fits the screen
    page.locator(".meal-plan-card").first.click()
    dialog = page.get_by_role("dialog")
    expect(dialog).to_be_visible()
    box = dialog.bounding_box()
    assert box["x"] >= 0 and box["x"] + box["width"] <= width + 1, f"pop-up is outside the screen: {box}"


#TC-GAP-85-06: A new plan shows under My Meal Plans with its name and description
@pytest.mark.skip(reason="Meal Plans pages not merged yet (PR #14)")
def test_new_plan_appears_under_my_meal_plans(page):
    # Precondition: user is on the Meal Plans page and has no plans of their own
    open_plans(page)
    expect(page.get_by_role("heading", name="Your collection starts here.")).to_be_visible()
    name = f"Weeknight Dinners {time.time_ns()}"

    # Steps:
    # 1. Click "+ Create New Plan"
    # 2. Type a name and a description, then click "Create Plan"
    create_plan(page, name, "Fast meals for busy nights")

    # Expected Result: the plan shows with its name and description, the empty message is gone,
    # and the 4 built-in plans are unchanged
    expect(plan_card(page, name)).to_contain_text("Fast meals for busy nights")
    expect(plan_card(page, name)).to_contain_text("CUSTOM COLLECTION")
    expect(page.get_by_role("heading", name="Your collection starts here.")).to_have_count(0)
    expect(page.locator(".meal-plan-card")).to_have_count(5)


#TC-GAP-85-07: A plan with no description gets the default one
@pytest.mark.skip(reason="Meal Plans pages not merged yet (PR #14)")
def test_plan_without_description_gets_default_text(page):
    # Precondition: user is on the Meal Plans page
    open_plans(page)
    name = f"Plain Plan {time.time_ns()}"

    # Steps:
    # 1. Create a plan with a name and no description
    create_plan(page, name)

    # Expected Result: the plan shows "A personalized meal plan made just for you."
    expect(plan_card(page, name)).to_contain_text("A personalized meal plan made just for you.")


#TC-GAP-85-08: A plan is still there after reloading, and is gone after it is deleted
@pytest.mark.skip(reason="Meal Plans pages not merged yet (PR #14)")
def test_plan_survives_reload_and_delete_sticks(page):
    # Precondition: user has created a plan
    open_plans(page)
    name = f"Keeper {time.time_ns()}"
    create_plan(page, name)
    expect(plan_card(page, name)).to_be_visible()

    # Steps:
    # 1. Reload the page
    page.reload()
    # Expected Result: the plan is still there
    expect(plan_card(page, name)).to_be_visible()

    # 2. Open the plan and click "Delete This Plan"
    plan_card(page, name).click()
    page.get_by_role("button", name="Delete This Plan").click()
    # Expected Result: the plan is removed, and it stays removed after another reload
    expect(plan_card(page, name)).to_have_count(0)
    page.reload()
    expect(plan_card(page, name)).to_have_count(0)
    expect(page.get_by_role("heading", name="Your collection starts here.")).to_be_visible()


#TC-GAP-85-09: Cancel, the X button and clicking outside close the form without creating a plan
@pytest.mark.skip(reason="Meal Plans pages not merged yet (PR #14)")
def test_closing_create_form_creates_nothing(page):
    # Precondition: user is on the Meal Plans page
    open_plans(page)
    name = f"Never Saved {time.time_ns()}"
    dialog = page.get_by_role("dialog")

    for how in ("Cancel", "Close", "outside"):
        # Steps:
        # 1. Click "+ Create New Plan" and type a name
        page.get_by_role("button", name="+ Create New Plan").click()
        page.get_by_label("Plan Name").fill(name)
        # 2. Close the form without creating
        if how == "outside":
            page.mouse.click(5, 5)
        else:
            dialog.get_by_role("button", name=how).click()

        # Expected Result: the form closes and no plan is created
        expect(dialog).to_have_count(0)
        expect(plan_card(page, name)).to_have_count(0)
        expect(page.locator(".meal-plan-card")).to_have_count(4)


#TC-GAP-85-10: A name of only spaces does not create a plan
@pytest.mark.skip(reason="Meal Plans pages not merged yet (PR #14)")
def test_blank_plan_name_creates_nothing(page):
    # Precondition: the Create Your Meal Plan form is open
    open_plans(page)
    page.get_by_role("button", name="+ Create New Plan").click()

    # Steps:
    # 1. Click "Create Plan" with the name empty
    page.get_by_role("button", name="Create Plan").click()
    # Expected Result: the form stays open and no plan is created (the name box is required)
    expect(page.get_by_role("dialog")).to_be_visible()

    # 2. Type only spaces and click "Create Plan"
    page.get_by_label("Plan Name").fill("     ")
    page.get_by_role("button", name="Create Plan").click()
    # Expected Result: still no plan, only the 4 built-in ones
    page.get_by_role("button", name="Cancel").click()
    expect(page.locator(".meal-plan-card")).to_have_count(4)


# Meal Plan Dashboard (SCRUM-48)
#TC-GAP-48-01: Dashboard lists today's and upcoming meals
@pytest.mark.skip(reason="Meal Plan Dashboard not built yet")
def test_dashboard_lists_upcoming_meals(page):
    # Precondition: user has meals today, tomorrow and last week

    # Steps:
    # 1. Open the dashboard

    # Expected Result: Today's and tomorrow's meals show; last week's do not
    assert False  # placeholder, replace with real check once the dashboard exists

#TC-GAP-48-02: Dashboard links open the right pages
@pytest.mark.skip(reason="Meal Plan Dashboard not built yet")
def test_dashboard_links(page):
    # Precondition: user is on the dashboard

    # Steps:
    # 1. Click Recipes, then go back
    # 2. Click Calendar, then go back
    # 3. Click Shopping List

    # Expected Result: Each link opens its own page
    assert False  # placeholder, replace with real check once the dashboard exists

#TC-GAP-48-03: Dashboard with no meals shows a friendly message
@pytest.mark.skip(reason="Meal Plan Dashboard not built yet")
def test_dashboard_no_meals(page):
    # Precondition: user has a new account with no meals

    # Steps:
    # 1. Open the dashboard

    # Expected Result: A friendly empty message shows with an "Add Meal" link
    assert False  # placeholder, replace with real check once the dashboard exists

#TC-GAP-48-04: Dashboard works at phone, tablet and desktop widths
@pytest.mark.skip(reason="Meal Plan Dashboard not built yet")
def test_dashboard_responsive(page):
    # Precondition: user is on the dashboard

    # Steps:
    # 1. View the page at 375, 768 and 1440 pixels wide

    # Expected Result: Content is readable with no sideways scrolling at every width
    assert False  # placeholder, replace with real check once the dashboard exists


# Suggested Recipes on the Dashboard (SCRUM-64)
#TC-76-01: Suggested recipes load with a loading indicator
@pytest.mark.skip(reason="Suggested recipes not merged yet (PR #14)")
def test_suggested_recipes_load_with_indicator(page):
    # Precondition: a user account already exists, user has successfully logged in
    # and has an active session, and at least 10 suggested recipes exist

    # Steps:
    # 1. Open the suggested recipes page

    # Expected Result: A loading indicator shows, then the recipe cards appear and the indicator goes away
    assert False  # placeholder, replace with real check once suggested recipes are merged

#TC-76-02: Slow network keeps the loading indicator until data arrives
@pytest.mark.skip(reason="Suggested recipes not merged yet (PR #14)")
def test_slow_network_keeps_indicator(page):
    # Precondition: user is logged in and the network is slowed down

    # Steps:
    # 1. Open the suggested recipes page

    # Expected Result: The loading indicator stays until the cards appear, with no blank flash
    assert False  # placeholder, replace with real check once suggested recipes are merged

#TC-76-03: A failed request shows an error and Retry works
@pytest.mark.skip(reason="Suggested recipes not merged yet (PR #14)")
def test_failed_request_shows_error_and_retry(page):
    # Precondition: user is logged in and the suggestions request is set to fail

    # Steps:
    # 1. Open the suggested recipes page
    # 2. Fix the server and click "Retry"

    # Expected Result: Step 1 shows a readable error with "Retry"; step 2 loads the cards
    assert False  # placeholder, replace with real check once suggested recipes are merged

#TC-77-01: Each card shows name, image and cook time
@pytest.mark.skip(reason="Suggested recipes not merged yet (PR #14)")
def test_card_shows_name_image_cook_time(page):
    # Precondition: user is logged in and suggested recipes exist

    # Steps:
    # 1. Open the suggested recipes page

    # Expected Result: Every card shows a name, image and cook time, with no "undefined" or "null" text
    assert False  # placeholder, replace with real check once suggested recipes are merged

#TC-77-02: A missing or broken image shows a placeholder
@pytest.mark.skip(reason="Suggested recipes not merged yet (PR #14)")
def test_missing_or_broken_image_shows_placeholder(page):
    # Precondition: one suggested recipe has a bad image link and one has no image

    # Steps:
    # 1. Open the suggested recipes page

    # Expected Result: Both cards show a placeholder image, not a broken image icon
    assert False  # placeholder, replace with real check once suggested recipes are merged

#TC-77-03: A long recipe name does not break the card
@pytest.mark.skip(reason="Meal Plans pages not merged yet (PR #14)")
def test_long_name_does_not_break_card(page):
    # Precondition: a plan has a long name (a custom plan, the longest the box allows is 60 characters)
    page.goto(f"{BASE_URL}/meal-plans")
    long_name = ("Extraordinarily " * 4)[:60].strip()
    page.get_by_role("button", name="+ Create New Plan").click()
    page.get_by_label("Plan Name").fill(long_name)
    page.get_by_role("button", name="Create Plan").click()

    # Steps:
    # 1. View the Meal Plans page
    card = page.locator(".meal-plan-card", has=page.get_by_role("heading", name=long_name))

    # Expected Result: The card shows the whole name and stays inside the page
    expect(card).to_be_visible()
    box = card.bounding_box()
    viewport = page.viewport_size["width"]
    assert box["x"] >= 0 and box["x"] + box["width"] <= viewport, f"card sticks out of the page: {box}"
    widths = page.evaluate("() => ({scroll: document.documentElement.scrollWidth, view: document.documentElement.clientWidth})")
    assert widths["scroll"] <= widths["view"]


#TC-78-01: Retired (Oct 22). Covered by TC-GAP-85-01.

#TC-78-02: Going back keeps the list position
@pytest.mark.skip(reason="Suggested recipes not merged yet (PR #14)")
def test_back_keeps_list_position(page):
    # Precondition: user has scrolled to card #25 on the suggested recipes page

    # Steps:
    # 1. Open card #25
    # 2. Click "Back"

    # Expected Result: The list is at the same spot with card #25 visible
    assert False  # placeholder, replace with real check once suggested recipes are merged

#TC-78-03: A suggested recipe cannot be deleted by the user
@pytest.mark.skip(reason="Meal Plans pages not merged yet (PR #14)")
def test_suggested_recipe_cannot_be_deleted(page):
    # Precondition: a suggested plan's detail is open
    page.goto(f"{BASE_URL}/meal-plans")
    page.locator(".meal-plan-card", has=page.get_by_role("heading", name="Balanced")).click()

    # Steps:
    # 1. Look for a delete option
    # Expected Result: There is no delete option on a built-in plan
    expect(page.get_by_role("dialog").get_by_role("heading", name="Balanced")).to_be_visible()
    expect(page.get_by_role("button", name="Delete This Plan")).to_have_count(0)

    # (a plan the user created does have one)
    page.get_by_role("button", name="Close").click()
    page.get_by_role("button", name="+ Create New Plan").click()
    page.get_by_label("Plan Name").fill("Mine to delete")
    page.get_by_role("button", name="Create Plan").click()
    page.locator(".meal-plan-card", has=page.get_by_role("heading", name="Mine to delete")).click()
    expect(page.get_by_role("button", name="Delete This Plan")).to_be_visible()


#TC-79-01: No suggested recipes shows a clear message
@pytest.mark.skip(reason="Meal Plans pages not merged yet (PR #14)")
def test_no_suggested_recipes_shows_message(page):
    # Precondition: user has not created any plans of their own (the built-in collections cannot be removed,
    # so the empty message is for "My Meal Plans")
    page.goto(f"{BASE_URL}/meal-plans")

    # Steps:
    # 1. Look at "My Meal Plans"
    # Expected Result: A clear message shows with a button to create the first plan
    expect(page.get_by_role("heading", name="Your collection starts here.")).to_be_visible()
    expect(page.get_by_role("button", name="Create Your First Plan")).to_be_visible()


#TC-80-01: Every recipe in a long list can be reached
@pytest.mark.skip(reason="Suggested recipes not merged yet (PR #14)")
def test_long_list_all_reachable(page):
    # Precondition: 60 suggested recipes exist

    # Steps:
    # 1. Scroll to the bottom (or click through every page)

    # Expected Result: All 60 recipes are reachable, none repeated and none skipped
    assert False  # placeholder, replace with real check once suggested recipes are merged

#TC-80-02: The end of the list is clear
@pytest.mark.skip(reason="Suggested recipes not merged yet (PR #14)")
def test_end_of_list_is_clear(page):
    # Precondition: 60 suggested recipes exist

    # Steps:
    # 1. Scroll to the very end of the list

    # Expected Result: The list clearly ends, with no endless loading indicator
    assert False  # placeholder, replace with real check once suggested recipes are merged

#TC-80-03: Cards stack in one column on a phone
@pytest.mark.skip(reason="Meal Plans pages not merged yet (PR #14)")
def test_cards_stack_on_phone(page):
    # Precondition: browser window is 375 pixels wide and the 4 built-in collections exist
    page.set_viewport_size({"width": 375, "height": 812})
    page.goto(f"{BASE_URL}/meal-plans")

    # Steps:
    # 1. Look at the cards
    cards = page.locator(".meal-plan-card")
    expect(cards).to_have_count(4)

    # Expected Result: One column: every card starts at the same left edge, each below the one before
    boxes = [cards.nth(n).bounding_box() for n in range(4)]
    assert len({round(box["x"]) for box in boxes}) == 1, f"cards are not in one column: {boxes}"
    for upper, lower in zip(boxes, boxes[1:]):
        assert lower["y"] >= upper["y"] + upper["height"] - 1


