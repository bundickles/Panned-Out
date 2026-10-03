import pytest
from playwright.sync_api import expect

def add_test_recipe(page, name, ingredients, instructions):
    page.goto("http://localhost:5173/recipes")
    page.get_by_role("button", name="Add Recipe").first.click()
    page.get_by_label("Name").fill(name)
    page.get_by_label("Ingredients").fill(ingredients)
    page.get_by_label("Instructions").fill(instructions)
    page.get_by_role("button", name="Save").click()
    expect(page.get_by_text(name)).to_be_visible()

 
# Recipe Creation
 
#TC-16-01: User can create a new recipe with all required fields filled out
def test_create_recipe_with_all_fields(page):
    # Precondition: a user account already exists, user has successfully logged in
    # and has an active session and has navigated to the recipe creation page
    page.goto("http://localhost:5173/recipes")

    # Steps:
    # 1. Click "+ Add Recipe"
    page.get_by_role("button", name="Add Recipe").first.click()
    # 2. Enter recipe name
    page.get_by_label("Name").fill("Lemon Garlic Shrimp")
    # 3. Enter ingredients
    page.get_by_label("Ingredients").fill("shrimp, lemon, garlic, olive oil")
    # 4. Enter instructions
    page.get_by_label("Instructions").fill("Saute shrimp with garlic, finish with lemon juice")
    # 5. Click "Save"
    page.get_by_role("button", name="Save").click()

    # Expected Result: the recipe is created successfully and appears in the recipe list
    expect(page.get_by_text("Lemon Garlic Shrimp")).to_be_visible()


#TC-16-02: Newly created recipe displays correctly in the recipe list
def test_new_recipe_appears_in_recipe_list(page):
    # Precondition: a user account already exists, user has successfully logged in
    # and has an active session and has just created a new recipe
    name = "Lemon Garlic Shrimp"
    ingredients = "shrimp, lemon, garlic, olive oil"
    instructions = "Saute shrimp with garlic, finish with lemon juice"
    add_test_recipe(page, name, ingredients, instructions)

    # Steps:
    # 1. Navigate to the recipe list
    page.goto("http://localhost:5173/recipes")
    # 2. Expand that recipe's details
    card = page.locator(".recipe-card", has_text=name)
    card.get_by_text("Recipe details").click()

    # Expected Result: the newly created recipe appears in the list with the correct name and details
    assert card.get_by_text(name).is_visible()
    assert card.get_by_text(ingredients).is_visible()
    assert card.get_by_text(instructions).is_visible()


# Recipe Editing
 
#TC-16-03: User can edit an existing recipe's fields
def test_edit_existing_recipe(page):
    # Precondition: a recipe already exists to edit
    name, ingredients, instructions = "Pasta Bake", "pasta, sauce, cheese", "Mix and bake 20 min"
    add_test_recipe(page, name, ingredients, instructions)

    # Steps:
    # 1. Click the recipe's "Edit" button
    page.get_by_role("button", name=f"Edit {name}").click()

    # 2. Form opens titled "Edit Recipe" and is pre-filled with the existing values
    assert page.get_by_text("Edit Recipe").is_visible()
    assert page.get_by_label("Name").input_value() == name
    assert page.get_by_label("Ingredients").input_value() == ingredients
    assert page.get_by_label("Instructions").input_value() == instructions

    # 3. Change one or more fields
    page.get_by_label("Ingredients").fill("pasta, sauce, cheese, extra garlic")
    # 4. Click "Save"
    page.get_by_role("button", name="Save").click()

    # Expected Result: the recipe's edit page allowed changes and accepted the save
    assert page.get_by_text("extra garlic").is_visible()


#TC-16-04: Edited recipe changes persist after saving
def test_edited_recipe_changes_persist(page):
    # Precondition: a recipe already exists, and has just been edited and saved
    name = "Pasta Bake"
    add_test_recipe(page, name, "pasta, sauce, cheese", "Mix and bake 20 min")
    page.get_by_role("button", name=f"Edit {name}").click()
    page.get_by_label("Ingredients").fill("pasta, sauce, cheese, extra garlic")
    page.get_by_role("button", name="Save").click()

    # Steps:
    # 1. Navigate away from the recipe, then back to it (refresh the page)
    page.reload()

    # Expected Result: the recipe displays the updated fields, not the original ones
    assert page.get_by_text("extra garlic").is_visible()


#TC-16-04c: Cancelling an edit does not save the changes
def test_cancel_edit_does_not_save_changes(page):
    # Precondition: a recipe already exists to edit
    name = "Pasta Bake"
    original_ingredients = "pasta, sauce, cheese"
    add_test_recipe(page, name, original_ingredients, "Mix and bake 20 min")

    # Steps:
    # 1. Click "Edit"
    page.get_by_role("button", name=f"Edit {name}").click()
    # 2. Change a field without saving
    page.get_by_label("Ingredients").fill("this change should be discarded")
    # 3. Click "Cancel" instead of "Save"
    page.get_by_role("button", name="Cancel").click()

    # Expected Result: the recipe card still shows the original value,
    # the unsaved edit never made it onto the card
    assert page.get_by_text(original_ingredients).is_visible()
    assert not page.get_by_text("this change should be discarded").is_visible()

    # Note: TC-16-04b (image preservation on edit) isn't covered here, the
    # Add/Edit form has no image field at all right now


# Recipe Deletion
 
#TC-16-05: User can delete an existing recipe
def test_delete_existing_recipe(page):
    # Precondition: a user account already exists, user has successfully logged in
    # and has an active session, and a recipe already exists to delete
    page.goto("http://localhost:5173/recipes")

    # Steps:
    # 1. Select the recipe to delete
    # 2. Click "Delete"
    page.get_by_role("button", name="Delete Keto Taco Bowl").click()

    # Expected Result: The recipe is removed successfully
    expect(page.get_by_text("Keto Taco Bowl")).not_to_be_visible()
 
 
#TC-16-06: Deleted recipe no longer appears in the recipe list
def test_deleted_recipe_not_in_list(page):
    # Precondition: a user account already exists, user has successfully logged in
    # and has an active session, and has just deleted a recipe
    page.goto("http://localhost:5173/recipes")
    count_before = page.locator(".recipe-card").count()

    # Steps:
    # 1. Navigate to the recipe list
    page.get_by_role("button", name="Delete Keto Taco Bowl").click()

    # Expected Result: The deleted recipe does not appear in the list
    expect(page.locator(".recipe-card")).to_have_count(count_before - 1)
    expect(page.get_by_text("Keto Taco Bowl")).not_to_be_visible()
 
 
# Recipe Search/Filter
 
#TC-16-07: Searching by recipe name filters the list to matching recipes
def test_search_by_recipe_name_filters_list(page):
    # Precondition: a user account already exists, user has successfully logged in
    # and has an active session and is on the Recipes page with multiple recipes available
    
 
    # Steps:
    # 1. Type a recipe name (or partial name) into the search field
    page.goto("http://localhost:5173/recipes")
    page.get_by_label("Search recipes").fill("Keto")
 
    # Expected Result: Only recipes whose name matches the search text are displayed
    assert page.get_by_text("Keto Taco Bowl").is_visible()
    assert not page.get_by_text("Creamy Tuscan Chicken").is_visible()
 
 
#TC-16-08: Filtering by category shows only recipes in that category
def test_filter_by_category_shows_matching_recipes(page):
    # Precondition: a user account already exists, user has successfully logged in
    # and has an active session and is on the Recipes page with recipes in multiple categories
    page.goto("http://localhost:5173/recipes")

    # Steps:
    # 1. Click a category filter button (e.g. "Keto")
    page.get_by_role("button", name="Keto", exact=True).click()

    # Expected Result: Only recipes belonging to that category are displayed
    assert page.get_by_text("Keto Taco Bowl").is_visible()
    assert not page.get_by_text("Creamy Tuscan Chicken").is_visible()
 
 
#TC-16-09: Search text and category filter combine correctly
def test_search_and_category_filter_combine(page):
    # Precondition: a user account already exists, user has successfully logged in
    # and has an active session and is on the Recipes page
    page.goto("http://localhost:5173/recipes")
 
    # Steps:
    # 1. Type a search term into the search field
    page.get_by_label("Search recipes").fill("Keto")

    # 2. Click a category filter button
    page.get_by_role("button", name="Keto", exact=True).click()

    # Expected Result: Only recipes matching both the search text and the selected category are displayed
    assert page.get_by_text("Keto Taco Bowl").is_visible()
    assert not page.get_by_text("Creamy Tuscan Chicken").is_visible()

 
 
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
    page.get_by_label("Name").fill("@@@###???")
    page.get_by_label("Ingredients").fill("!!!")
    page.get_by_label("Instructions").fill("???")
    # 2. Click "Save"
    page.get_by_role("button", name="Save").click()

    # Expected Result: the page does not crash, and the recipe saves with the
    # entered data intact rather than silently dropping or corrupting it
    expect(page.get_by_text("@@@###???")).to_be_visible()
