import pytest
 
# Recipe Creation
 
#TC-16-01: User can create a new recipe with all required fields filled out
@pytest.mark.skip(reason="Recipe creation UI not yet implemented")
def test_create_recipe_with_all_fields():
    # Precondition: a user account already exists, user has successfully logged in
    # and has an active session and has navigated to the recipe creation page

    # Steps:
    # 1. Enter recipe name
    # 2. Enter recipe description
    # 3. Enter ingredients
    # 4. Enter instructions
    # 5. Click "Save Recipe"
 
    # Expected Result: The recipe is created successfully and appears in the recipe list
    assert False  # placeholder, replace with real check once recipe creation UI exists
 
 
#TC-16-02: Newly created recipe displays correctly in the recipe list
@pytest.mark.skip(reason="Recipe creation UI not yet implemented")
def test_new_recipe_appears_in_recipe_list():
    # Precondition: a user account already exists, user has successfully logged in
    # and has an active session and has just created a new recipe
 
    # Steps:
    # 1. Navigate to the recipe list
 
    # Expected Result: The newly created recipe appears in the list with the correct name and details
    assert False  # placeholder, replace with real check once recipe creation UI exists
 
 
# Recipe Editing
 
#TC-16-03: User can edit an existing recipe's fields
@pytest.mark.skip(reason="Recipe editing UI not yet implemented")
def test_edit_existing_recipe():
    # Precondition: a user account already exists, user has successfully logged in
    # and has an active session, and a recipe already exists to edit
 
    # Steps:
    # 1. Navigate to the recipe's edit page
    # 2. Change one or more fields (e.g. name, ingredients)
    # 3. Click "Save"
 
    # Expected Result: The recipe's edit page allows changes and accepts the save
    assert False  # placeholder, replace with real check once recipe editing UI exists
 
 
#TC-16-04: Edited recipe changes persist after saving
@pytest.mark.skip(reason="Recipe editing UI not yet implemented")
def test_edited_recipe_changes_persist():
    # Precondition: a user account already exists, user has successfully logged in
    # and has an active session, and has just edited and saved a recipe
 
    # Steps:
    # 1. Navigate away from the recipe, then back to it (or refresh the page)
 
    # Expected Result: The recipe displays the updated fields, not the original ones
    assert False  # placeholder, replace with real check once recipe editing UI exists
 
 
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
    assert not page.get_by_text("Keto Taco Bowl").is_visible()
 
 
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
    assert page.locator(".recipe-card").count() == count_before - 1
    assert not page.get_by_text("Keto Taco Bowl").is_visible()
 
 
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
@pytest.mark.skip(reason="Recipe creation UI not yet implemented")
def test_create_recipe_missing_required_fields_shows_error():
    # Precondition: a user account already exists, user has successfully logged in
    # and has an active session and has navigated to the recipe creation page
 
    # Steps:
    # 1. Leave one or more required fields blank (e.g. recipe name)
    # 2. Click "Save Recipe"
 
    # Expected Result: A validation error is shown and the recipe is not saved
    assert False  # placeholder, replace with real check once recipe creation UI exists
 
 
#TC-16-12: Invalid recipe data is handled gracefully without breaking the page
@pytest.mark.skip(reason="Recipe creation UI not yet implemented")
def test_invalid_recipe_data_handled_gracefully():
    # Precondition: a user account already exists, user has successfully logged in
    # and has an active session and has navigated to the recipe creation page

 
    # Steps:
    # 1. Enter invalid data into a field (e.g. non-numeric value where a number is expected, if applicable)
    # 2. Click "Save Recipe"
 
    # Expected Result: An appropriate error message is shown, and the page does not crash or lose entered data
    assert False  # placeholder, replace with real check once recipe creation UI exists
 

