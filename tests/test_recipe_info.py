import pytest
import json
import re
import time
from playwright.sync_api import expect
 
# Recipe Detail Display
 
BASE_URL = "http://localhost:5173"

DETAIL_FILLER = "A favorite to make, share, and come back to."

def create_recipe(page, name, difficulty="Medium", ingredients="2 eggs\n1 cup milk",
                  instructions="Whisk the eggs\nBake for 20 minutes", prep_time=20,
                  calories=300, protein=12, fat=8, carbohydrates=40, fiber=3,
                  meal_type="Dinner", category="My Recipes"):
    """Create a recipe straight through the backend and return its id (faster than the form)."""
    response = page.request.post(f"{BASE_URL}/api/recipes", headers={"X-Panned-Out-Request": "1"}, form={
        "name": name, "category": category, "difficulty": difficulty, "mealType": meal_type,
        "ingredients": ingredients, "instructions": instructions, "prepTime": str(prep_time),
        "calories": str(calories), "protein": str(protein), "fat": str(fat),
        "carbohydrates": str(carbohydrates), "fiber": str(fiber),
    })
    assert response.ok, response.text()
    return response.json()["id"]

def unique_name(prefix):
    return f"{prefix} {time.time_ns()}"

def mock_recipe_list(page, recipes):
    """Make the Recipes API return `recipes`, so a recipe with missing fields can be shown.
    The form and the backend both refuse to save a recipe with no ingredients or steps."""
    page.route("**/api/recipes", lambda route: route.fulfill(
        status=200, content_type="application/json", body=json.dumps(recipes)))

def open_detail(page, name):
    page.goto(f"{BASE_URL}/recipes")
    page.get_by_role("button", name=f"Open recipe: {name}").click()
    expect(page.get_by_role("heading", level=1, name=name)).to_be_visible()

def page_text(page):
    return page.locator("body").inner_text()

def assert_no_placeholder_text(page):
    text = page_text(page)
    for bad in ("undefined", "null", "NaN"):
        assert bad not in text, f"found '{bad}' on the page"


#TC-50-01: Recipe name, description, ingredients, and instructions all display correctly for a complete recipe
def test_recipe_details_display_correctly(page):
    # Precondition: a user account already exists, user has successfully logged in
    # and has an active session and is viewing a recipe's detail page,
    # and the recipe has complete data in all fields
    name = unique_name("Complete Omelette")
    create_recipe(page, name, ingredients="2 eggs\n1 cup milk\n1 pinch salt",
                  instructions="Whisk the eggs\nPour into the pan\nFold and serve")

    # Steps:
    # 1. View the recipe detail page
    open_detail(page, name)

    # Expected Result: Recipe name, description, ingredients, and instructions all display correctly
    expect(page.get_by_role("heading", level=1)).to_have_text(name)
    expect(page.get_by_text(DETAIL_FILLER)).to_be_visible()   # the page shows a fixed sentence, recipes have no description field
    expect(page.get_by_role("heading", name="Ingredients")).to_be_visible()
    expect(page.locator(".journal-ingredients li")).to_have_text(["2 eggs", "1 cup milk", "1 pinch salt"])
    expect(page.get_by_role("heading", name="Instructions")).to_be_visible()
    expect(page.locator(".journal-instructions li p")).to_have_text(
        ["Whisk the eggs", "Pour into the pan", "Fold and serve"])
    assert_no_placeholder_text(page)


#TC-50-02: Cooking/preparation info displays when available
def test_cooking_prep_info_displays_when_available(page):
    # Precondition: a user account already exists, user has successfully logged in
    # and has an active session and is viewing a recipe's detail page,
    # and the recipe includes cooking/preparation info
    name = unique_name("Prep Info Pasta")
    create_recipe(page, name, prep_time=25, calories=450)

    # Steps:
    # 1. View the recipe detail page
    open_detail(page, name)

    # Expected Result: Cooking/preparation info displays correctly on the recipe detail page
    stats = page.locator(".journal-stats")
    expect(stats).to_contain_text("PREP TIME")
    expect(stats).to_contain_text("25 min")
    expect(stats).to_contain_text("CALORIES")
    expect(stats).to_contain_text("450")


# Missing/Incomplete Recipe Data
 
#TC-50-03: Recipe missing cooking/prep info still displays correctly without breaking
def test_recipe_missing_cooking_prep_info_still_displays(page):
    # Precondition: a user account already exists, user has successfully logged in
    # and has an active session and is viewing a recipe's detail page,
    # and the recipe does not include cooking/preparation info
    name = unique_name("No Prep Soup")
    mock_recipe_list(page, [{
        "id": "mock-1", "name": name, "difficulty": "Easy", "mealType": "Lunch",
        "category": "My Recipes", "ingredients": "water\nsalt", "instructions": "Boil\nServe",
    }])

    # Steps:
    # 1. View the recipe detail page
    page.goto(f"{BASE_URL}/recipes/mock-1")

    # Expected Result: Recipe detail page displays all other available info correctly,
    # without breaking or showing an error for the missing cooking/prep field
    expect(page.get_by_role("heading", level=1)).to_have_text(name)
    expect(page.locator(".journal-ingredients li")).to_have_count(2)
    expect(page.locator(".journal-instructions li")).to_have_count(2)
    expect(page.locator(".journal-stats")).to_contain_text("— min")
    assert_no_placeholder_text(page)


#TC-50-04: Recipe missing other fields (e.g., no description or no ingredients) handles gracefully
def test_recipe_missing_other_fields_handles_gracefully(page):
    # Precondition: a user account already exists, user has successfully logged in
    # and has an active session and is viewing a recipe's detail page,
    # and the recipe is missing one or more fields (e.g., no description or no ingredients listed)
    name = unique_name("Bare Recipe")
    mock_recipe_list(page, [{"id": "mock-2", "name": name}])

    # Steps:
    # 1. View the recipe detail page
    page.goto(f"{BASE_URL}/recipes/mock-2")

    # Expected Result: Recipe detail page still renders without breaking or crashing,
    # showing whatever fields are available and handling missing fields gracefully
    # (e.g., hidden or shown as empty rather than causing an error)
    expect(page.get_by_role("heading", level=1)).to_have_text(name)
    expect(page.get_by_text("No ingredients have been added yet.")).to_be_visible()
    expect(page.get_by_text("No instructions have been added yet.")).to_be_visible()
    assert_no_placeholder_text(page)


# Recipe Navigation & Interactions
 
#TC-50-05: Navigating back to the recipe/meal list from the detail view works correctly
def test_navigate_back_to_recipe_list(page):
    # Precondition: a user account already exists, user has successfully logged in
    # and has an active session and is viewing a recipe's detail page
    name = unique_name("Back Button Stew")
    create_recipe(page, name)
    open_detail(page, name)

    # Steps:
    # 1. Click the "Back" navigation element on the recipe detail page
    page.get_by_role("button", name="Back to Recipes").first.click()

    # Expected Result: User is returned to the recipe/meal list view
    expect(page).to_have_url(f"{BASE_URL}/recipes")
    expect(page.get_by_role("heading", level=1, name="Recipes")).to_be_visible()


# Sprint 2: Recipe Detail Display (SCRUM-51)
 
#TC-51-02: Difficulty label matches the recipe
def test_difficulty_label_matches_recipe(page):
    # Precondition: recipes exist with difficulty Easy, Medium and Hard
    names = {level: unique_name(f"{level} Dish") for level in ("Easy", "Medium", "Hard")}
    for level, name in names.items():
        create_recipe(page, name, difficulty=level)

    # Steps:
    # 1. Open each recipe's detail page
    for level, name in names.items():
        open_detail(page, name)

        # Expected Result: Each page shows its own difficulty (and its color, see TC-GAP-82-02)
        expect(page.locator(".journal-difficulty")).to_contain_text(f"{level} difficulty")


#TC-51-03: Special characters show exactly as saved
def test_special_characters_show_as_saved(page):
    # Precondition: a recipe named "Crème Brûlée 🍮" with the ingredient "½ cup jalapeño" exists
    name = "Crème Brûlée 🍮"
    create_recipe(page, name, ingredients="½ cup jalapeño")
    page.goto(f"{BASE_URL}/recipes")
    card = page.get_by_role("button", name=f"Open recipe: {name}").first

    # Steps:
    # 1. Open the recipe's detail page
    card.click()

    # Expected Result: The name and ingredient show exactly as saved
    expect(page.get_by_role("heading", level=1)).to_have_text(name)
    expect(page.locator(".journal-ingredients li").first).to_have_text("½ cup jalapeño")


# Sprint 2: Missing/Incomplete Recipe Data (SCRUM-52)
 
#TC-52-01: Recipe with no image shows a placeholder
def test_recipe_without_image_shows_placeholder(page):
    # Precondition: a recipe exists with no image
    name = unique_name("No Photo Chili")
    create_recipe(page, name)

    # Steps:
    # 1. Open the recipe's detail page
    open_detail(page, name)

    # Expected Result: A placeholder shows instead of a broken image icon
    expect(page.locator(".journal-photo-placeholder")).to_be_visible()
    expect(page.locator("img.journal-photo")).to_have_count(0)


#TC-52-05: Retired (Oct 22). Covered by TC-50-04 (missing fields).

#TC-52-06: Very long content does not break the layout
def test_long_content_does_not_break_layout(page):
    # Precondition: a recipe exists with a 200-character name, 50 ingredients and a 2,000-character step
    long_name = " ".join(["Marvelous"] * 20)[:200]
    ingredients = "\n".join(f"{n} cup of ingredient number {n}" for n in range(1, 51))
    long_step = " ".join(["stir"] * 400)[:2000]
    mock_recipe_list(page, [{
        "id": "mock-4", "name": long_name, "difficulty": "Hard", "mealType": "Dinner",
        "ingredients": ingredients, "instructions": long_step, "prepTime": 90,
    }])

    # Steps:
    # 1. Open the recipe's detail page
    page.goto(f"{BASE_URL}/recipes/mock-4")

    # Expected Result: Text wraps, there is no sideways scrolling, and the page is still usable
    expect(page.get_by_role("heading", level=1)).to_be_visible()
    expect(page.locator(".journal-ingredients li")).to_have_count(50)
    widths = page.evaluate("() => ({scroll: document.documentElement.scrollWidth, view: document.documentElement.clientWidth})")
    assert widths["scroll"] <= widths["view"], f"page scrolls sideways: {widths}"
    expect(page.get_by_role("button", name="Back to Recipes").first).to_be_visible()


# Sprint 2: Recipe Navigation & Interactions (SCRUM-53)
 
#TC-53-01: Going back from a recipe keeps the list's scroll position and filters
# BUG FOUND (BUG-01): Back from the recipe detail page clears the Recipes search. This test fails until it is fixed.
def test_back_from_detail_keeps_list_position(page):
    # Precondition: 20 recipes exist and user has scrolled to recipe #15 on the Recipes page
    tag = f"Keep{time.time_ns()}"
    for n in range(1, 21):
        create_recipe(page, f"{tag} Dish {n:02d}")
    page.goto(f"{BASE_URL}/recipes")
    page.get_by_label("Search recipes").fill(tag)
    card = page.get_by_role("button", name=f"Open recipe: {tag} Dish 15")
    card.scroll_into_view_if_needed()
    scroll_before = page.evaluate("() => document.querySelector('.recipes-content').scrollTop")

    # Steps:
    # 1. Click recipe card #15
    card.click()
    expect(page.get_by_role("heading", level=1, name=f"{tag} Dish 15")).to_be_visible()
    # 2. Click "Back"
    page.get_by_role("button", name="Back to Recipes").first.click()

    # Expected Result: The same list shows at the same scroll spot with the same search and filter
    expect(page.get_by_label("Search recipes")).to_have_value(tag)
    expect(page.get_by_role("button", name=f"Open recipe: {tag} Dish 15")).to_be_visible()
    scroll_after = page.evaluate("() => document.querySelector('.recipes-content').scrollTop")
    assert abs(scroll_after - scroll_before) < 50, f"scroll moved from {scroll_before} to {scroll_after}"


#TC-53-03: Editing from the detail page updates the recipe
@pytest.mark.skip(reason="Still fails on main 03114e1 (checked Nov 19): PR #14 removed Edit from the recipe pages; confirm with the team whether Edit is coming back")
def test_edit_from_detail_updates_recipe(page):
    # Precondition: a recipe with a 20-minute prep time is open on its detail page

    # Steps:
    # 1. Click "Edit"
    # 2. Change the prep time to 35
    # 3. Click "Save recipe"

    # Expected Result: The detail page and the list card both show 35, and there is still one recipe
    assert False  # placeholder, replace with real check once Edit exists again


#TC-53-04: Deleting from the detail page removes the recipe
@pytest.mark.skip(reason="Still fails on main 03114e1 (checked Nov 19): Recipe detail page has no Delete button (PR #14, Delete is on the list cards only); confirm with the team")
def test_delete_from_detail_removes_recipe(page):
    # Precondition: a recipe is open on its detail page

    # Steps:
    # 1. Click "Delete" and confirm

    # Expected Result: User is back on the Recipes page and the recipe is gone
    assert False  # placeholder, replace with real check once Delete exists on the detail page


#TC-53-05: Another account's recipe link shows not found
def test_other_accounts_recipe_link_not_found(page, browser):
    # Precondition: account A owns a recipe and user is logged in as account B
    name = unique_name("Private Stew")
    recipe_id = create_recipe(page, name)               # the shared test account is account A

    context = browser.new_context()
    page_b = context.new_page()
    try:
        page_b.goto(f"{BASE_URL}/login")
        page_b.get_by_role("button", name="Create an account").click()
        page_b.get_by_label("Email address").fill(f"other{time.time_ns()}@example.com")
        page_b.get_by_label("Password").fill("calendar-test-password-123")
        page_b.get_by_role("button", name="Create account").click()
        page_b.wait_for_url("**/calendar")
        try:   # new accounts see the app tour (SCRUM-165); close it so it does not cover the page
            page_b.get_by_role("button", name="Skip tour").click(timeout=4000)
        except Exception:
            pass

        # Steps:
        # 1. Go directly to account A's recipe detail URL
        page_b.goto(f"{BASE_URL}/recipes/{recipe_id}")

        # Expected Result: A "not found" page shows and none of account A's recipe data appears
        expect(page_b.get_by_role("heading", name="Recipe not found")).to_be_visible()
        expect(page_b.get_by_text(name)).to_have_count(0)
        expect(page_b.get_by_text("Cook it")).to_have_count(0)
    finally:
        context.close()


# Sprint 2: Recipe Detail Extras (SCRUM-82, SCRUM-47)
 
#TC-GAP-82-01: Nutrition info shows with units
def test_nutrition_info_shows_units(page):
    # Precondition: a recipe with nutrition values and a recipe with none exist
    with_values = unique_name("Nutrition Bowl")
    create_recipe(page, with_values, calories=520, protein=31, fat=14, carbohydrates=60, fiber=9)

    # Steps:
    # 1. Open each recipe's detail page
    open_detail(page, with_values)

    # Expected Result: Nutrition shows with units, and missing nutrition shows cleanly
    nutrition = page.locator(".nutrition-values")
    # (calories are already checked in TC-50-02, so this test checks only the gram units)
    for grams, label in (("31", "Protein"), ("14", "Fat"), ("60", "Carbs"), ("9", "Fiber")):
        expect(nutrition).to_contain_text(re.compile(rf"{grams}\s*g\s*{label}"))

    mock_recipe_list(page, [{"id": "mock-5", "name": unique_name("No Nutrition"), "ingredients": "a", "instructions": "b"}])
    page.goto(f"{BASE_URL}/recipes/mock-5")
    expect(page.locator(".nutrition-values")).to_be_visible()
    assert_no_placeholder_text(page)


#TC-GAP-82-02: Difficulty colors match
def test_difficulty_colors(page):
    # Precondition: recipes exist with difficulty Easy, Medium and Hard
    names = {level: unique_name(f"{level} Color") for level in ("Easy", "Medium", "Hard")}
    for level, name in names.items():
        create_recipe(page, name, difficulty=level)

    # Steps:
    # 1. Open each recipe's detail page
    detail_colors = {}
    list_colors = {}
    page.goto(f"{BASE_URL}/recipes")
    for level, name in names.items():
        card = page.locator(".recipe-card", has=page.get_by_role("button", name=f"Open recipe: {name}"))
        list_colors[level] = card.locator(".recipe-difficulty-dot").evaluate("el => getComputedStyle(el).backgroundColor")
    for level, name in names.items():
        open_detail(page, name)
        detail_colors[level] = page.locator(".difficulty-dot").evaluate("el => getComputedStyle(el).backgroundColor")
        page.goto(f"{BASE_URL}/recipes")

    # Expected Result: Each difficulty has its own color, the same as on the meal cards
    assert len(set(detail_colors.values())) == 3, f"colors are not all different: {detail_colors}"
    assert detail_colors == list_colors, f"detail {detail_colors} vs list cards {list_colors}"


#TC-GAP-82-03: Add to calendar from the recipe detail
@pytest.mark.skip(reason="Still fails on main 03114e1 (checked Nov 19): '+ Add to Calendar' only opens the Calendar in PR #14 (no date or meal type step yet); needs Add Meal (PR #12) wired in")
def test_add_to_calendar_from_detail(page):
    # Precondition: user is logged in and a recipe detail page is open

    # Steps:
    # 1. Click "Add to calendar"
    # 2. Choose 2026-10-21 and "Dinner", then click "Save"
    # 3. Open the Calendar and select 2026-10-21

    # Expected Result: The meal shows on 2026-10-21
    assert False  # placeholder, replace with real check once the button saves a meal


#TC-GAP-82-05: Recipe detail page works at phone, tablet and desktop widths
@pytest.mark.parametrize("width,height", [(375, 812), (768, 1024), (1440, 900)])
def test_detail_page_responsive(page, width, height):
    # Precondition: a recipe detail page is open
    name = unique_name("Responsive Risotto")
    create_recipe(page, name)

    # Steps:
    # 1. View the page at 375, 768 and 1440 pixels wide
    page.set_viewport_size({"width": width, "height": height})
    open_detail(page, name)

    # Expected Result: Content is readable with no sideways scrolling at every width
    expect(page.get_by_role("heading", level=1)).to_be_visible()
    expect(page.get_by_role("heading", name="Ingredients")).to_be_visible()
    expect(page.get_by_role("heading", name="Instructions")).to_be_visible()
    widths = page.evaluate("() => ({scroll: document.documentElement.scrollWidth, view: document.documentElement.clientWidth})")
    # Allow 2px: at 375px the photo frame (.journal-photo-frame) ends half a pixel past the edge, which makes
    # the page 1px wider on some loads. Anything more than that is a real sideways scroll.
    assert widths["scroll"] <= widths["view"] + 2, f"page scrolls sideways at {width}px: {widths}"




# Sprint 3: Cooking Mode (SCRUM-47, built as the "cooking focus view")
# The merged view shows one step at a time with Previous step and Next step, and has one
# manual timer (a minutes box plus Start, Pause and Reset). It has no per-step timers and no
# checkboxes, so TC-47-05, 06, 07, 08 and 11 from the plan do not apply to this build.

STEPS_3 = "Boil water.\nSimmer for 10 minutes.\nDrain."


def open_cooking_view(page, name):
    open_detail(page, name)
    page.get_by_role("button", name="Open cooking focus view").click()
    dialog = page.locator("dialog.cooking-dialog")
    expect(dialog).to_be_visible()
    return dialog


#TC-47-01: Cooking Mode turns on from the recipe detail page
def test_cooking_mode_turns_on_from_detail(page):
    # Precondition: the recipe with the steps "Boil water.", "Simmer for 10 minutes." and "Drain." is open on its detail page
    name = unique_name("Cook Pasta")
    create_recipe(page, name, instructions=STEPS_3)

    # Steps:
    # 1. Click "Open cooking focus view"
    dialog = open_cooking_view(page, name)

    # Expected Result: The cooking view shows with the recipe name and step 1, "Boil water."
    expect(dialog.get_by_role("heading", name=name)).to_be_visible()
    expect(dialog.get_by_text("Step 1 of 3")).to_be_visible()
    expect(dialog.get_by_text("Boil water.")).to_be_visible()


#TC-47-03: Next and Back move between steps
def test_cooking_mode_next_and_back(page):
    # Precondition: the cooking view is on for a recipe with 3 steps and step 1 is showing
    name = unique_name("Cook Steps")
    create_recipe(page, name, instructions=STEPS_3)
    dialog = open_cooking_view(page, name)

    # Steps:
    # 1. Click "Next step"
    dialog.get_by_role("button", name="Next step").click()
    # Expected Result (step 1): step 2 shows with the recipe's own text
    expect(dialog.get_by_text("Step 2 of 3")).to_be_visible()
    expect(dialog.get_by_text("Simmer for 10 minutes.")).to_be_visible()
    # 2. Click "Next step"
    dialog.get_by_role("button", name="Next step").click()
    expect(dialog.get_by_text("Step 3 of 3")).to_be_visible()
    expect(dialog.get_by_text("Drain.")).to_be_visible()
    # 3. Click "Previous step"
    dialog.get_by_role("button", name="Previous step").click()

    # Expected Result: step 2 shows again
    expect(dialog.get_by_text("Step 2 of 3")).to_be_visible()
    expect(dialog.get_by_text("Simmer for 10 minutes.")).to_be_visible()


#TC-47-04: Previous stops at the first step and Next stops at the last step
def test_cooking_mode_first_and_last_step(page):
    # Precondition: the cooking view is on for a recipe with 3 steps
    name = unique_name("Cook Ends")
    create_recipe(page, name, instructions=STEPS_3)
    dialog = open_cooking_view(page, name)

    # Steps:
    # 1. Look at "Previous step" on step 1
    expect(dialog.get_by_role("button", name="Previous step")).to_be_disabled()
    # 2. Click "Next step" until step 3 shows
    dialog.get_by_role("button", name="Next step").click()
    dialog.get_by_role("button", name="Next step").click()
    expect(dialog.get_by_text("Step 3 of 3")).to_be_visible()

    # Expected Result: "Previous step" is disabled on step 1, and "Next step" is disabled on step 3
    expect(dialog.get_by_role("button", name="Next step")).to_be_disabled()


#TC-47-09: The timer counts down, pauses and resets
def test_timer_counts_down_pauses_and_resets(page):
    # Precondition: the cooking view is on, a 10 minute timer is set, and the browser clock is controlled by the test
    name = unique_name("Cook Timer")
    create_recipe(page, name, instructions=STEPS_3)
    page.clock.install()
    dialog = open_cooking_view(page, name)
    dialog.get_by_label("Duration (minutes)").fill("10")
    clock_text = dialog.get_by_role("timer", name="Time remaining")

    # Steps:
    # 1. Click "Start timer" and move the clock forward 60 seconds
    dialog.get_by_role("button", name="Start timer").click()
    page.clock.run_for(60_000)
    expect(clock_text).to_have_text("09:00")
    # 2. Click "Pause timer" and move the clock forward 60 seconds
    dialog.get_by_role("button", name="Pause timer").click()
    page.clock.run_for(60_000)
    expect(clock_text).to_have_text("09:00")
    # 3. Click "Reset timer"
    dialog.get_by_role("button", name="Reset timer").click()

    # Expected Result: the timer reads 09:00 after step 1, still 09:00 after step 2, and is cleared after step 3
    expect(clock_text).to_have_text("00:00")


#TC-47-10: The timer shows when it finishes
def test_timer_shows_when_finished(page):
    # Precondition: the cooking view is on and the browser clock is controlled by the test
    name = unique_name("Cook Done")
    create_recipe(page, name, instructions=STEPS_3)
    page.clock.install()
    dialog = open_cooking_view(page, name)
    dialog.get_by_label("Duration (minutes)").fill("1")

    # Steps:
    # 1. Click "Start timer"
    dialog.get_by_role("button", name="Start timer").click()
    # 2. Move the clock forward 60 seconds
    page.clock.run_for(61_000)

    # Expected Result: the timer reads 00:00 and a finished message shows
    expect(dialog.get_by_role("timer", name="Time remaining")).to_have_text("00:00")
    expect(dialog.get_by_text("Time’s up! Check your food.")).to_be_visible()


#TC-47-10b: A duration of 0, a negative number or more than 1440 minutes is refused
@pytest.mark.parametrize("minutes", ["0", "-5", "1441"])
def test_timer_rejects_invalid_duration(page, minutes):
    # Precondition: the cooking view is on
    name = unique_name("Cook Bad Timer")
    create_recipe(page, name, instructions=STEPS_3)
    dialog = open_cooking_view(page, name)

    # Steps:
    # 1. Type the duration and click "Start timer"
    dialog.get_by_label("Duration (minutes)").fill(minutes)
    dialog.get_by_role("button", name="Start timer").click()

    # Expected Result: an error shows and the timer does not start
    expect(dialog.get_by_role("alert")).to_contain_text("greater than 0")
    expect(dialog.get_by_role("timer", name="Time remaining")).to_have_text("00:00")


#TC-47-12: Closing the cooking view returns to the normal detail page
def test_leaving_cooking_mode_returns_to_detail(page):
    # Precondition: the cooking view is on for a recipe with 3 steps
    name = unique_name("Cook Exit")
    create_recipe(page, name, instructions=STEPS_3)
    dialog = open_cooking_view(page, name)
    url_before = page.url

    # Steps:
    # 1. Click "Close focus view"
    dialog.get_by_role("button", name="Close focus view").click()

    # Expected Result: the normal detail page shows for the same recipe and the address is unchanged
    expect(dialog).not_to_be_visible()
    expect(page.get_by_role("heading", level=1, name=name)).to_be_visible()
    assert page.url == url_before
    assert re.search(r"/recipes/\d+$", page.url)


#TC-47-13: A 1 step recipe and a 35 step recipe both work
@pytest.mark.parametrize("step_count", [1, 35])
def test_one_step_and_many_step_recipes(page, step_count):
    # Precondition: a recipe with 1 step, and then a recipe with 35 steps, is open on its detail page
    name = unique_name(f"Cook {step_count} Steps")
    create_recipe(page, name, instructions="\n".join(f"Do thing number {i}." for i in range(1, step_count + 1)))

    # Steps:
    # 1. Turn on the cooking view
    dialog = open_cooking_view(page, name)
    # 2. Click "Next step" until the last step
    for _ in range(step_count - 1):
        dialog.get_by_role("button", name="Next step").click()

    # Expected Result: the last step is reached, the label counts up to it, and nothing overflows the page
    expect(dialog.get_by_text(f"Step {step_count} of {step_count}")).to_be_visible()
    expect(dialog.get_by_text(f"Do thing number {step_count}.")).to_be_visible()
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
