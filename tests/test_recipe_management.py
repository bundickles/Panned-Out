import pytest
import time
from playwright.sync_api import expect
import base64

BASE_URL = "http://localhost:5173"

def add_test_recipe(page, name, ingredients, instructions, category="My Recipes"):
    page.goto("http://localhost:5173/recipes")
    page.get_by_role("button", name="Add Recipe").first.click()
    page.get_by_label("Name").fill(name)
    page.get_by_label("Category").select_option(category)
    page.get_by_label("Ingredients").fill(ingredients)
    page.get_by_label("Instructions").fill(instructions)
    page.get_by_role("button", name="Save recipe").click()
    expect(page.get_by_text(name)).to_be_visible()

 
# Recipe Creation
 
TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")

def open_add_form(page):
    page.goto(f"{BASE_URL}/recipes")
    page.get_by_role("button", name="Add Recipe").first.click()
    expect(page.get_by_role("button", name="Save recipe")).to_be_visible()

def fill_required(page, name):
    page.get_by_label("Recipe name").fill(name)
    page.get_by_label("Ingredients").fill("rice\nbeans")
    page.get_by_label("Instructions").fill("Cook together")


#TC-16-01: User can create a new recipe with all required fields filled out
def test_create_recipe_with_all_fields(page):
    # Precondition: a user account already exists, user has successfully logged in
    # and has an active session and has navigated to the recipe creation page
    name = f"Lemon Garlic Shrimp {int(time.time_ns())}"
    page.goto("http://localhost:5173/recipes")

    # Steps:
    # 1. Click "+ Add Recipe"
    page.get_by_role("button", name="Add Recipe").first.click()
    # 2. Enter recipe name
    page.get_by_label("Name").fill(name)
    # 3. Enter ingredients
    page.get_by_label("Ingredients").fill("shrimp, lemon, garlic, olive oil")
    # 4. Enter instructions
    page.get_by_label("Instructions").fill("Saute shrimp with garlic, finish with lemon juice")
    # 5. Click "Save"
    page.get_by_role("button", name="Save").click()

    # Expected Result: the recipe is created successfully and appears in the recipe list
    expect(page.get_by_text(name)).to_be_visible()

#TC-16-02: Newly created recipe displays correctly in the recipe list
def test_new_recipe_appears_in_recipe_list(page):
    # Precondition: a user account already exists, user has successfully logged in
    # and has an active session and has just created a new recipe
    name = f"Lemon Garlic Shrimp {int(time.time_ns())}"
    ingredients = ["shrimp", "lemon", "garlic", "olive oil"]
    instructions = "Saute shrimp with garlic, finish with lemon juice"
    add_test_recipe(page, name, ", ".join(ingredients), instructions)

    # Steps:
    # 1. Navigate to the recipe list
    page.goto("http://localhost:5173/recipes")
    # The recipe shows on its card in the list
    card = page.locator(".recipe-card", has_text=name)
    expect(card).to_have_count(1)
    # 2. Open that recipe's details (the card opens the detail page)
    page.get_by_role("button", name=f"Open recipe: {name}").click()

    # Expected Result: the newly created recipe appears in the list with the correct name and details
    expect(page.get_by_role("heading", level=1, name=name)).to_be_visible()
    for item in ingredients:
        expect(page.locator(".journal-ingredients li").filter(has_text=item)).to_have_count(1)
    expect(page.get_by_text(instructions)).to_be_visible()


# Recipe Editing
 
#TC-16-03: User can edit an existing recipe's fields
def test_edit_existing_recipe(page):
    # Precondition: a recipe already exists to edit
    name, ingredients, instructions = f"Pasta Bake {int(time.time_ns())}", "pasta, sauce, cheese", "Mix and bake 20 min"
    add_test_recipe(page, name, ingredients, instructions)

    # Steps:

    # 1. Navigate to Recipes page
    page.goto("http://localhost:5173/recipes")
    expect(page.get_by_text(name)).to_be_visible()
    count_before = page.locator(".recipe-card").count()

    # 2. Click the recipe's "Edit" button
    page.get_by_role("button", name=f"Edit {name}").click()

    # 3. Form opens titled "Edit Recipe" and is pre-filled with the existing values
    expect(page.get_by_text("Edit Recipe")).to_be_visible()
    assert page.get_by_label("Name").input_value() == name
    assert page.get_by_label("Ingredients").input_value() == ingredients
    assert page.get_by_label("Instructions").input_value() == instructions

    # 4. Change one or more fields
    page.get_by_label("Name").fill(f"{name} v2")   
    
     # 5. Click "Save recipe"
    page.get_by_role("button", name="Save").click()

    # Expected Result: The edit form closes, the recipe card shows the updated name, and no new card is added (the recipe count stays the same).
    expect(page.get_by_text("Edit Recipe")).not_to_be_visible()
    expect(page.get_by_text(f"{name} v2")).to_be_visible()    
    expect(page.locator(".recipe-card")).to_have_count(count_before)

#TC-16-04: Edited recipe changes persist after saving
def test_edited_recipe_changes_persist(page):
    # Precondition: a recipe already exists, and has just been edited and saved
    name = f"Pasta Bake {int(time.time_ns())}"
    add_test_recipe(page, name, "pasta, sauce, cheese", "Mix and bake 20 min")
    page.get_by_role("button", name=f"Edit {name}").click()
    page.get_by_label("Name").fill(f"{name} v2")   
    page.get_by_role("button", name="Save").click()
    expect(page.get_by_text("Edit Recipe")).not_to_be_visible()

    # Steps:
    # 1. Navigate away from the recipe, then back to it (refresh the page)
    page.reload()

    # Expected Result: the recipe displays the updated fields, not the original ones
    expect(page.get_by_text(f"{name} v2")).to_be_visible()    

#TC-16-04c: Cancelling an edit does not save the changes
def test_cancel_edit_does_not_save_changes(page):
    # Precondition: a recipe already exists to edit
    name = f"Pasta Bake {int(time.time_ns())}"
    original_ingredients = "pasta, sauce, cheese"
    add_test_recipe(page, name, original_ingredients, "Mix and bake 20 min")

    # Steps:
    # 1. Click "Edit"
    page.get_by_role("button", name=f"Edit {name}").click()

    # 2. Change a field without saving
    page.get_by_label("Name").fill("this change should be discarded")

    # 3. Click "Cancel" instead of "Save"
    page.get_by_role("button", name="Cancel").click()

    # Expected Result: the recipe card still shows the original value,
    # the unsaved edit never made it onto the card
    expect(page.get_by_text(name)).to_be_visible()
    expect(page.get_by_text("this change should be discarded")).not_to_be_visible()

    # Note: TC-16-04b (image preservation on edit) isn't covered here, the
    # Add/Edit form has no image field at all right now

# Recipe Deletion
 
#TC-16-05: User can delete an existing recipe
def test_delete_existing_recipe(page):
    # Precondition: a user account already exists, user has successfully logged in
    # and has an active session, and a recipe already exists to delete
    name = f"Keto Taco Bowl {int(time.time_ns())}"
    add_test_recipe(page, name, "corn, cheese, ground beef, tomato", "Bake for 20 mins")
    page.goto("http://localhost:5173/recipes")


    # Steps:
    # 1. Select the recipe to delete
    # 2. Click "Delete"
    page.get_by_role("button", name=f"Delete {name}").click()

    # Expected Result: The recipe is removed successfully
    expect(page.get_by_text(name)).not_to_be_visible()
 
 
#TC-16-06: Deleted recipe no longer appears in the recipe list
def test_deleted_recipe_not_in_list(page):
    # Precondition: a user account already exists, user has successfully logged in
    # and has an active session, and has just deleted a recipe
    name = f"Keto Taco Bowl {int(time.time_ns())}"
    add_test_recipe(page, name, "corn, cheese, ground beef, tomato", "Bake for 20 mins")
    page.goto("http://localhost:5173/recipes")
    expect(page.get_by_text(name)).to_be_visible()
    count_before = page.locator(".recipe-card").count()

    # Steps:
    # 1. Navigate to the recipe list
    page.get_by_role("button", name=f"Delete {name}").click()

    # Expected Result: The deleted recipe does not appear in the list
    expect(page.locator(".recipe-card")).to_have_count(count_before - 1)
    expect(page.get_by_text(name)).not_to_be_visible()
 
 
# Recipe Search/Filter
 
#TC-16-07: Searching by recipe name filters the list to matching recipes
def test_search_by_recipe_name_filters_list(page):
    # Precondition: a user account already exists, user has successfully logged in
    # and has an active session and is on the Recipes page with multiple recipes available

    keto_name = f"Keto Taco Bowl {time.time_ns()}"
    add_test_recipe(page, keto_name, "corn, cheese, ground beef, tomato", "Bake for 20 mins")

    chicken_name = f"Creamy Tuscan Chicken {time.time_ns()}"
    add_test_recipe(page, chicken_name, "chicken, cheese, heavy whipping cream, tomato", "Bake for 20 mins")

 
    # Steps:
    # 1. Type a recipe name (or partial name) into the search field
    page.goto("http://localhost:5173/recipes")
    page.get_by_label("Search recipes").fill("Keto")
 
    # Expected Result: Only recipes whose name matches the search text are displayed
    expect(page.get_by_text(keto_name)).to_be_visible()
    expect(page.get_by_text(chicken_name)).not_to_be_visible()
 
 
#TC-16-08: Filtering by category shows only recipes in that category
def test_filter_by_category_shows_matching_recipes(page):
    # Precondition: a user account already exists, user has successfully logged in
    # and has an active session and is on the Recipes page with recipes in multiple categories
    keto_name = f"Keto Taco Bowl {time.time_ns()}"
    add_test_recipe(page, keto_name, "corn, cheese, ground beef, tomato", "Bake for 20 mins", category="Keto")

    chicken_name = f"Creamy Tuscan Chicken {time.time_ns()}"
    add_test_recipe(page, chicken_name, "chicken, cheese, heavy whipping cream, tomato", "Bake for 20 mins", category="High Protein")

    page.goto("http://localhost:5173/recipes")

    # Steps:
    # 1. Click a category filter button (e.g. "Keto")
    page.get_by_role("button", name="Keto", exact=True).click()

    # Expected Result: Only recipes belonging to that category are displayed
    expect(page.get_by_text(keto_name)).to_be_visible()
    expect(page.get_by_text(chicken_name)).not_to_be_visible()

#TC-16-09: Search text and category filter combine correctly
def test_search_and_category_filter_combine(page):
    # Precondition: a user account already exists, user has successfully logged in
    # and has an active session and is on the Recipes page
    # Three recipes: one matches both the search and the category, one matches
    # only the search, one matches only the category
    both_name = f"Keto Taco Bowl {time.time_ns()}"
    add_test_recipe(page, both_name, "corn, cheese, ground beef, tomato", "Bake for 20 mins", category="Keto")

    search_only_name = f"Keto Chicken Salad {time.time_ns()}"
    add_test_recipe(page, search_only_name, "chicken, lettuce, olive oil", "Toss together", category="High Protein")

    category_only_name = f"Creamy Tuscan Chicken {time.time_ns()}"
    add_test_recipe(page, category_only_name, "chicken, cheese, heavy whipping cream, tomato", "Bake for 20 mins", category="Keto")

    page.goto("http://localhost:5173/recipes")

    # Steps:
    # 1. Type a search term into the search field
    page.get_by_label("Search recipes").fill("Keto")

    # 2. Click a category filter button
    page.get_by_role("button", name="Keto", exact=True).click()

    # Expected Result: Only recipes matching both the search text and the selected category are displayed
    expect(page.get_by_text(both_name)).to_be_visible()
    expect(page.get_by_text(search_only_name)).not_to_be_visible()
    expect(page.get_by_text(category_only_name)).not_to_be_visible()

#TC-16-10: No matching recipes shows an empty state rather than breaking
def test_no_matching_recipes_shows_empty_state(page):
    # Precondition: a user account already exists, user has successfully logged in
    # and has an active session and is on the Recipes page
    page.goto("http://localhost:5173/recipes")

    # Steps:
    # 1. Type a search term that matches no recipes
    page.get_by_label("Search recipes").fill("zzzznotarecipe")

    # Expected Result: An empty/no-results state is shown, and the page does not break
    assert page.get_by_text("No recipes found.").is_visible()
    assert page.locator(".recipe-card").count() == 0
 
 
# Validation & Error Handling
 
#TC-16-11: Creating a recipe with missing required fields shows a validation error
def test_create_recipe_missing_required_fields_shows_error(page):
    # Precondition: a user account already exists, user has successfully logged in
    # and has an active session and has navigated to the recipe creation page
    page.goto("http://localhost:5173/recipes")
    page.get_by_role("button", name="Add Recipe").first.click()

    # Steps:
    # 1. Leave the recipe name blank
    name_input = page.get_by_label("Name")
    # 2. Fill in the other fields
    page.get_by_label("Ingredients").fill("flour, sugar, eggs")
    page.get_by_label("Instructions").fill("Mix and bake")
    # 3. Click "Save"
    page.get_by_role("button", name="Save").click()

    # Expected Result: a validation error is shown and the recipe is not saved
    # (the Name field is a required HTML input, so the browser blocks the submit)
    is_valid = name_input.evaluate("el => el.validity.valid")
    assert is_valid is False

#TC-16-12: Invalid recipe data is handled gracefully without breaking the page
def test_invalid_recipe_data_handled_gracefully(page):
    # Precondition: a user account already exists, user has successfully logged in
    # and has an active session and has navigated to the recipe creation page
    # Note: every field on this form is a plain required text field, there's no
    # numeric or type-specific validation to violate here, so "invalid data" means
    # unusual input (symbols, no real content) rather than a wrong data type
    page.goto("http://localhost:5173/recipes")
    page.get_by_role("button", name="Add Recipe").first.click()

    # Steps:
    # 1. Enter unusual data into the fields
    name = f"@@@###??? {time.time_ns()}"
    page.get_by_label("Name").fill(name)
    page.get_by_label("Ingredients").fill("!!!")
    page.get_by_label("Instructions").fill("???")
    # 2. Click "Save"
    page.get_by_role("button", name="Save").click()

    # Expected Result: the page does not crash, and the recipe saves with the
    # entered data intact rather than silently dropping or corrupting it
    expect(page.get_by_text(name)).to_be_visible()
# Sprint 2: Recipe Flow (SCRUM-29)
 
#TC-29-05: Empty recipe collection shows a starter message
def test_empty_collection_shows_starter_message(page):
    # Precondition: the recipe collection is empty and user opens the Recipes page
    # (the recipe list request is answered with an empty list so the real data is untouched)
    page.route("**/api/recipes", lambda route: route.fulfill(
        status=200, content_type="application/json", body="[]"))

    # Steps:
    # 1. View the Recipes page
    page.goto(f"{BASE_URL}/recipes")

    # Expected Result: "No recipes found." and "Start by adding your favorite recipes to your
    # collection." show, with a "+ Add Recipe" button
    empty = page.locator(".empty-recipes")
    expect(empty.get_by_text("No recipes found.")).to_be_visible()
    expect(empty.get_by_text("Start by adding your favorite recipes to your collection.")).to_be_visible()
    expect(empty.get_by_role("button", name="Add Recipe")).to_be_visible()
 
 
#TC-29-07: A new recipe is still there after reloading
def test_new_recipe_survives_reload(page):
    # Precondition: user just created a new recipe on the Recipes page
    name = f"Prof Check Soup {time.time_ns()}"
    add_test_recipe(page, name, "broth, carrots", "Simmer for 20 minutes")

    # Steps:
    # 1. Reload the page
    page.reload()

    # Expected Result: The recipe card is still listed
    expect(page.get_by_text(name)).to_be_visible()
 
 
#TC-29-09: Ingredients and instructions are required
def test_ingredients_and_instructions_are_required(page):
    # Precondition: user is on the Recipes page with the "Add Recipe" form open
    name = f"Missing Fields {time.time_ns()}"
    page.goto(f"{BASE_URL}/recipes")
    page.get_by_role("button", name="Add Recipe").first.click()
    form_title = page.get_by_role("heading", name="Add Recipe")
    cards_with_name = page.locator(".recipe-card").filter(has_text=name)

    # Steps:
    # 1. Fill in everything except "Ingredients" and click "Save recipe"
    page.get_by_label("Name").fill(name)
    page.get_by_label("Instructions").fill("Mix and bake")
    page.get_by_role("button", name="Save recipe").click()

    # Expected Result (first try): the form stays open and no recipe card is added
    expect(form_title).to_be_visible()
    expect(cards_with_name).to_have_count(0)

    # 2. Fill in "Ingredients", clear "Instructions" and click "Save recipe"
    page.get_by_label("Ingredients").fill("flour, eggs")
    page.get_by_label("Instructions").fill("")
    page.get_by_role("button", name="Save recipe").click()

    # Expected Result (second try): the form stays open and still nothing was saved
    expect(form_title).to_be_visible()
    page.reload()
    expect(cards_with_name).to_have_count(0)
 
 
#TC-29-10: Cancel closes the form without saving
def test_cancel_closes_form_without_saving(page):
    # Precondition: user is on the Recipes page with the "Add Recipe" form open
    name = f"Cancelled Recipe {time.time_ns()}"
    page.goto(f"{BASE_URL}/recipes")
    page.get_by_role("button", name="Add Recipe").first.click()

    # Steps:
    # 1. Type a recipe name
    page.get_by_label("Name").fill(name)
    # 2. Click "Cancel"
    page.get_by_role("button", name="Cancel").click()

    # Expected Result: The form closes and no recipe card is added
    expect(page.get_by_role("heading", name="Add Recipe")).not_to_be_visible()
    expect(page.locator(".recipe-card").filter(has_text=name)).to_have_count(0)
 
 
#TC-29-11: Recipe server down while loading, then retry
def test_server_down_while_loading_then_retry(page):
    # Precondition: at least one recipe exists, and the recipe backend is "stopped"
    # (the recipe list request is blocked, then allowed again, so the real backend is untouched)
    name = f"Retry Soup {time.time_ns()}"
    add_test_recipe(page, name, "broth", "Simmer")

    def block(route):
        route.abort()
    page.route("**/api/recipes", block)

    # Steps:
    # 1. Open the Recipes page
    page.goto(f"{BASE_URL}/recipes")
    alert = page.get_by_role("alert")

    # Expected Result (step 1): the alert "Cannot reach the recipe server..." with a retry button
    expect(alert).to_contain_text("Cannot reach the recipe server")

    # 2. Start the backend again
    page.unroute("**/api/recipes", block)
    # 3. Click "Retry loading recipes"
    page.get_by_role("button", name="Retry loading recipes").click()

    # Expected Result (step 3): the alert is gone and recipes are listed
    expect(alert).not_to_be_visible()
    expect(page.get_by_text(name)).to_be_visible()
 
 
#TC-29-12: Recipe server down while saving keeps the typed values
def test_server_down_while_saving_keeps_values(page):
    # Precondition: user has filled in the "Add Recipe" form, then the backend is "stopped"
    name = f"Offline Attempt {time.time_ns()}"
    page.goto(f"{BASE_URL}/recipes")
    page.get_by_role("button", name="Add Recipe").first.click()
    page.get_by_label("Name").fill(name)
    page.get_by_label("Ingredients").fill("rice, beans")
    page.get_by_label("Instructions").fill("Cook together")

    def block_saves(route):
        if route.request.method == "POST":
            route.abort()
        else:
            route.continue_()
    page.route("**/api/recipes", block_saves)

    # Steps:
    # 1. Click "Save recipe"
    page.get_by_role("button", name="Save recipe").click()

    # Expected Result (step 1): an error shows and the typed values are kept
    expect(page.get_by_role("alert")).to_be_visible()
    expect(page.get_by_label("Name")).to_have_value(name)
    expect(page.get_by_label("Ingredients")).to_have_value("rice, beans")
    expect(page.get_by_label("Instructions")).to_have_value("Cook together")

    # 2. Start the backend again
    page.unroute("**/api/recipes", block_saves)
    # 3. Click "Save recipe" again
    page.get_by_role("button", name="Save recipe").click()

    # Expected Result (step 3): the recipe is saved once (one card, not two)
    expect(page.get_by_role("heading", name="Add Recipe")).not_to_be_visible()
    expect(page.locator(".recipe-card").filter(has_text=name)).to_have_count(1)
 
 
#TC-29-13: Recipes page works on a narrow screen
def test_recipes_page_on_narrow_screen(page):
    # Precondition: browser window is 375 x 800 and at least one recipe exists
    add_test_recipe(page, f"Narrow Screen Stew {time.time_ns()}", "beef, potatoes", "Slow cook")
    page.set_viewport_size({"width": 375, "height": 800})
    no_sideways_scroll = "document.documentElement.scrollWidth <= document.documentElement.clientWidth"

    # Steps:
    # 1. Open the Recipes page
    page.goto(f"{BASE_URL}/recipes")
    expect(page.locator(".recipe-card").first).to_be_visible()

    # Expected Result (step 1): the cards fit the screen with no sideways scrolling
    assert page.evaluate(no_sideways_scroll)

    # 2. Open the "Add Recipe" form
    page.get_by_role("button", name="Add Recipe").first.click()
    expect(page.get_by_role("heading", name="Add Recipe")).to_be_visible()

    # Expected Result (step 2): the form fits the screen with no sideways scrolling
    assert page.evaluate(no_sideways_scroll)
 
 
 


#TC-29-14: A recipe image shows a preview, then shows on the card and the detail page
# BUG FOUND (BUG-02): The recipe form never saves the image, so the card shows the placeholder. This test fails until it is fixed.
@pytest.mark.skip(reason="Recipe image upload not merged yet (PR #14)")
def test_recipe_image_upload_shows_preview_card_and_detail(page):
    # Precondition: user is on the Recipes page with the Add Recipe form open
    name = f"Photo Pasta {time.time_ns()}"
    open_add_form(page)
    fill_required(page, name)

    # Steps:
    # 1. Choose a small PNG as the recipe image
    page.get_by_label("Recipe image (optional)").set_input_files(
        {"name": "dish.png", "mimeType": "image/png", "buffer": TINY_PNG})

    # Expected Result: a preview shows in the form
    expect(page.get_by_alt_text("Recipe preview")).to_be_visible()

    # 2. Click "Save recipe"
    page.get_by_role("button", name="Save recipe").click()

    # Expected Result: the card shows the picture, and so does the detail page
    card = page.get_by_role("button", name=f"Open recipe: {name}")
    expect(card.locator("img")).to_be_visible()
    card.click()
    expect(page.locator("img.journal-photo")).to_be_visible()


#TC-29-15: A file that is not a picture is refused
@pytest.mark.skip(reason="Recipe image upload not merged yet (PR #14)")
def test_non_image_file_is_refused(page):
    # Precondition: the Add Recipe form is open
    open_add_form(page)

    # Steps:
    # 1. Choose a text file as the recipe image
    page.get_by_label("Recipe image (optional)").set_input_files(
        {"name": "notes.txt", "mimeType": "text/plain", "buffer": b"not a picture"})

    # Expected Result: "Please select an image file." shows and no preview appears
    expect(page.get_by_text("Please select an image file.")).to_be_visible()
    expect(page.get_by_alt_text("Recipe preview")).to_have_count(0)


#TC-29-16: A picture over 5 MB is refused
@pytest.mark.skip(reason="Recipe image upload not merged yet (PR #14)")
def test_image_over_5mb_is_refused(page):
    # Precondition: the Add Recipe form is open
    open_add_form(page)

    # Steps:
    # 1. Choose a picture that is just over 5 MB
    page.get_by_label("Recipe image (optional)").set_input_files(
        {"name": "huge.png", "mimeType": "image/png", "buffer": TINY_PNG + b"\0" * (5 * 1024 * 1024)})

    # Expected Result: "Image must be 5 MB or smaller." shows and no preview appears
    expect(page.get_by_text("Image must be 5 MB or smaller.")).to_be_visible()
    expect(page.get_by_alt_text("Recipe preview")).to_have_count(0)


#TC-29-17: Remove image clears the preview and the recipe saves without a picture
@pytest.mark.skip(reason="Recipe image upload not merged yet (PR #14)")
def test_remove_image_saves_recipe_without_picture(page):
    # Precondition: the Add Recipe form is open with a picture chosen
    name = f"No Photo After All {time.time_ns()}"
    open_add_form(page)
    fill_required(page, name)
    page.get_by_label("Recipe image (optional)").set_input_files(
        {"name": "dish.png", "mimeType": "image/png", "buffer": TINY_PNG})
    expect(page.get_by_alt_text("Recipe preview")).to_be_visible()

    # Steps:
    # 1. Click "Remove image"
    page.get_by_role("button", name="Remove image").click()
    # Expected Result: the preview goes away
    expect(page.get_by_alt_text("Recipe preview")).to_have_count(0)

    # 2. Click "Save recipe"
    page.get_by_role("button", name="Save recipe").click()

    # Expected Result: the card shows the plate placeholder, not a picture
    card = page.get_by_role("button", name=f"Open recipe: {name}")
    expect(card).to_be_visible()
    expect(card.locator("img")).to_have_count(0)


#TC-29-18: Negative or too large numbers are blocked
@pytest.mark.skip(reason="Recipe form number limits not merged yet (PR #14)")
@pytest.mark.parametrize("field,value", [
    ("Prep time (minutes)", "-5"),
    ("Calories", "-1"),
    ("Protein (g)", "100001"),
])
def test_out_of_range_numbers_are_blocked(page, field, value):
    # Precondition: the Add Recipe form is open with the required fields filled in
    name = f"Bad Number {time.time_ns()}"
    open_add_form(page)
    fill_required(page, name)

    # Steps:
    # 1. Type an out of range number in one of the number boxes
    page.get_by_label(field).fill(value)
    # 2. Click "Save recipe"
    page.get_by_role("button", name="Save recipe").click()

    # Expected Result: the form stays open and the recipe is not saved
    expect(page.get_by_role("button", name="Save recipe")).to_be_visible()
    page.get_by_role("button", name="Cancel").click()
    expect(page.get_by_role("button", name=f"Open recipe: {name}")).to_have_count(0)


# Sprint 2: Recipe Search/Filter (SCRUM-31)
# Shared precondition for TC-31-xx: recipes "Taco Bowl" (Keto), "Tomato Soup" (Low Calorie),
# "Pancakes" (My Recipes) and "Protein Oats" (High Protein) exist, and the page says "4 recipes found"
 
#TC-31-04: Clear filters brings back every recipe
def test_clear_filters_shows_all_recipes(page):
    # Precondition: recipes exist, "zzzz" is typed in the search and "Keto" is selected
    token = time.time_ns()
    add_test_recipe(page, f"Taco Bowl {token}", "beef, rice", "Assemble", category="Keto")
    add_test_recipe(page, f"Pancakes {token}", "flour, eggs", "Fry", category="My Recipes")
    page.goto(f"{BASE_URL}/recipes")
    expect(page.get_by_text(f"Pancakes {token}")).to_be_visible()
    total = page.locator(".recipe-card").count()
    search = page.get_by_label("Search recipes")
    search.fill("zzzz")
    page.get_by_role("button", name="Keto", exact=True).click()
    expect(page.get_by_text("No recipes found.")).to_be_visible()

    # Steps:
    # 1. Click "Clear filters"
    page.get_by_role("button", name="Clear filters").click()

    # Expected Result: The search box is empty, "All" is pressed, and every recipe is back
    expect(search).to_have_value("")
    expect(page.get_by_role("button", name="All", exact=True)).to_have_attribute("aria-pressed", "true")
    expect(page.get_by_text(f"{total} recipes found", exact=True)).to_be_visible()
 
 
#TC-31-07: Saving a new recipe resets the filters
def test_saving_recipe_resets_filters(page):
    # Precondition: recipes exist and "taco" is typed in "Search recipes"
    token = time.time_ns()
    add_test_recipe(page, f"Taco Bowl {token}", "beef, rice", "Assemble", category="Keto")
    page.goto(f"{BASE_URL}/recipes")
    expect(page.get_by_text(f"Taco Bowl {token}")).to_be_visible()
    total_before = page.locator(".recipe-card").count()
    search = page.get_by_label("Search recipes")
    search.fill("taco")

    # Steps:
    # 1. Click "+ Add Recipe"
    page.get_by_role("button", name="Add Recipe").first.click()
    # 2. Fill in the form for "Waffles" and click "Save recipe"
    page.get_by_label("Name").fill(f"Waffles {token}")
    page.get_by_label("Ingredients").fill("flour, milk")
    page.get_by_label("Instructions").fill("Cook in the waffle iron")
    page.get_by_role("button", name="Save recipe").click()

    # Expected Result: The search box is empty, "All" is pressed, Waffles shows,
    # and the recipe count went up by one
    expect(search).to_have_value("")
    expect(page.get_by_role("button", name="All", exact=True)).to_have_attribute("aria-pressed", "true")
    expect(page.get_by_text(f"Waffles {token}")).to_be_visible()
    expect(page.get_by_text(f"{total_before + 1} recipes found", exact=True)).to_be_visible()
 
 
#TC-31-08: An edited recipe moves to its new category
def test_edited_recipe_moves_category(page):
    # Precondition: a Keto recipe exists and user is on the Recipes page
    # (NOTE: PR #14 removes the Edit button; move this to the detail page when #14 merges)
    name = f"Taco Bowl {time.time_ns()}"
    add_test_recipe(page, name, "beef, rice", "Assemble", category="Keto")

    # Steps:
    # 1. Click "Edit Taco Bowl", change "Category" to "My Recipes", and click "Save recipe"
    page.get_by_role("button", name=f"Edit {name}").click()
    page.get_by_label("Category").select_option("My Recipes")
    page.get_by_role("button", name="Save recipe").click()
    expect(page.get_by_role("heading", name="Edit Recipe")).not_to_be_visible()
    # 2. Click the "Keto" category button
    page.get_by_role("button", name="Keto", exact=True).click()
    # Expected Result (step 2): the recipe is not under "Keto"
    expect(page.get_by_text(name)).not_to_be_visible()
    # 3. Click the "My Recipes" category button
    page.get_by_role("button", name="My Recipes", exact=True).click()
    # Expected Result (step 3): the recipe shows under "My Recipes"
    expect(page.get_by_text(name)).to_be_visible()
 
 
 
# Sprint 2: Recipe Edit Form (SCRUM-54)
 
#TC-GAP-54-03: An invalid edit keeps the old data
def test_invalid_edit_keeps_old_data(page):
    # Precondition: a recipe exists and user is on the Recipes page
    # (NOTE: PR #14 removes the Edit button; move this to the detail page when #14 merges)
    name = f"Taco Bowl {time.time_ns()}"
    add_test_recipe(page, name, "beef, rice", "Assemble", category="Keto")

    # Steps:
    # 1. Click "Edit Taco Bowl"
    page.get_by_role("button", name=f"Edit {name}").click()
    # 2. Clear "Recipe name" and click "Save recipe"
    page.get_by_label("Name").fill("")
    page.get_by_role("button", name="Save recipe").click()

    # Expected Result: The form stays open
    expect(page.get_by_role("heading", name="Edit Recipe")).to_be_visible()

    # 3. Reload the page
    page.reload()

    # Expected Result: after reloading the name is still the old one
    expect(page.get_by_text(name)).to_be_visible()
 
 
 
# Sprint 2: Likely Bug to Confirm
 
#TC-BUG-A4: [CONFIRM] Deleting a recipe asks for confirmation
@pytest.mark.skip(reason="Confirm with Vanny/Pratap whether a confirm step is wanted")
def test_delete_recipe_asks_for_confirmation(page):
    # Precondition: the recipe "Taco Bowl" exists and user is on the Recipes page
 
    # Steps:
    # 1. Click "Delete Taco Bowl" (trash icon)
 
    # Expected Result: A confirm step shows before the recipe is deleted
    assert False  # placeholder, replace with real check once the team decides
 
