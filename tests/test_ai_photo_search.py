import json
import re
import time

import pytest
from playwright.sync_api import expect

BASE_URL = "http://localhost:5173"

# The AI reply is faked by the tests so they give the same result every run.
# TC-151-03 (the real AI) is run by hand and is not in this file.

PNG = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360000002000001e221bc330000000049454e44ae426082")
JPG = bytes.fromhex("ffd8ffe000104a46494600010100000100010000ffdb004300080606070605080707070909080a0c140d0c0b0b0c1912130f141d1a1f1e1d1a1c1c20242e2720222c231c1c2837292c30313434341f27393d38323c2e333432ffc0000b080001000101011100ffc4001f0000010501010101010100000000000000000102030405060708090a0bffda0008010100003f00d2cf20ffd9")

RECIPE = {
    "status": "success",
    "requiresConfirmation": True,
    "warnings": ["AI may miss allergens. Check every ingredient."],
    "recipe": {
        "name": "Veggie Stir Fry",
        "ingredients": ["2 cups broccoli", "1 tbsp soy sauce", "1 cup rice"],
        "steps": ["Cook the rice.", "Stir fry the broccoli.", "Add the soy sauce and serve."],
    },
}


def photo_file(name="food.jpg", mime="image/jpeg", data=JPG):
    return {"name": name, "mimeType": mime, "buffer": data}


def fake_photo_api(page, body=None, status=200, available=True, delay_ms=0, hold=None):
    """Fake GET (is it set up) and POST (analyze) on /api/ai/photo-recipe. Returns the list of POSTs seen."""
    posts = []

    def handle(route):
        request = route.request
        if request.method == "GET":
            return route.fulfill(status=200, content_type="application/json", body=json.dumps({"available": available}))
        posts.append(request.headers.get("content-type", ""))
        if hold is not None:
            hold.append(route)
            return
        if delay_ms:
            time.sleep(delay_ms / 1000)
        route.fulfill(status=status, content_type="application/json", body=json.dumps(body if body is not None else RECIPE))
    page.route("**/api/ai/photo-recipe", handle)
    return posts


def open_photo_page(page):
    page.goto(f"{BASE_URL}/ai-photo")
    expect(page.get_by_role("heading", name="What could we cook?")).to_be_visible()


def choose(page, **kwargs):
    page.locator("#ai-photo-upload").set_input_files(photo_file(**kwargs))


def analyze(page):
    page.get_by_role("button", name="Analyze photo").click()


def recipe_names(page):
    names = page.request.get(f"{BASE_URL}/api/recipes").json()
    return [item["name"] for item in names]


# Sprint 3: Photo Upload and File Validation (SCRUM-121)

#TC-121-01: A JPG and a PNG are accepted and previewed
@pytest.mark.parametrize("file_name,mime,data", [("food.jpg", "image/jpeg", JPG), ("food.png", "image/png", PNG)])
def test_jpg_and_png_accepted(page, file_name, mime, data):
    # Precondition: user is signed in and is on the AI photo page
    fake_photo_api(page)
    open_photo_page(page)

    # Steps:
    # 1. Choose the file in the file picker
    choose(page, name=file_name, mime=mime, data=data)

    # Expected Result: A preview of the photo shows and Analyze photo can be clicked
    expect(page.get_by_text(f"Photo selected: {file_name}")).to_be_visible()
    expect(page.get_by_role("button", name="Analyze photo")).to_be_enabled()


#TC-121-02: Unsupported file types are rejected with a message
@pytest.mark.parametrize("file_name,mime", [("menu.pdf", "application/pdf"), ("clip.gif", "image/gif"), ("notes.jpg", "text/plain")])
def test_unsupported_files_rejected(page, file_name, mime):
    # Precondition: user is signed in and is on the AI photo page
    fake_photo_api(page)
    open_photo_page(page)

    # Steps:
    # 1. Choose the file in the file picker
    choose(page, name=file_name, mime=mime, data=b"not an image")

    # Expected Result: A message gives the reason, nothing is previewed and Analyze photo is not offered
    expect(page.get_by_role("alert").filter(has_text="Choose a JPEG or PNG image.")).to_be_visible()
    expect(page.get_by_text("Photo selected")).to_have_count(0)
    expect(page.get_by_role("button", name="Analyze photo")).to_have_count(0)


#TC-121-03: A file at the 5 MB limit is accepted and one byte over is rejected
def test_file_size_limit(page):
    # Precondition: user is signed in and is on the AI photo page (the limit is 5 MB, set in the app)
    fake_photo_api(page)
    open_photo_page(page)
    limit = 5 * 1024 * 1024

    # Steps:
    # 1. Choose a photo exactly at the size limit
    choose(page, name="exact.jpg", data=JPG + b"\0" * (limit - len(JPG)))
    expect(page.get_by_text("Photo selected: exact.jpg")).to_be_visible()
    # 2. Choose a photo one byte over the limit
    choose(page, name="toobig.jpg", data=JPG + b"\0" * (limit + 1 - len(JPG)))

    # Expected Result: The first photo is accepted, and the second is rejected with a message
    expect(page.get_by_role("alert").filter(has_text="no larger than 5 MB")).to_be_visible()


#TC-121-04: A zero-byte image is rejected
def test_empty_image_rejected(page):
    # Precondition: user is signed in and is on the AI photo page
    fake_photo_api(page)
    open_photo_page(page)

    # Steps:
    # 1. Choose an empty file named empty.jpg
    choose(page, name="empty.jpg", data=b"")

    # Expected Result: The file is rejected with a clear reason
    expect(page.get_by_role("alert").filter(has_text="The photo is empty")).to_be_visible()
    expect(page.get_by_role("button", name="Analyze photo")).to_have_count(0)


#TC-121-05: I can replace the photo before submitting
def test_replace_photo_before_submitting(page):
    # Precondition: user is signed in and is on the AI photo page
    fake_photo_api(page)
    open_photo_page(page)

    # Steps:
    # 1. Choose "food.jpg"
    choose(page, name="food.jpg")
    expect(page.get_by_text("Photo selected: food.jpg")).to_be_visible()
    # 2. Choose "food.png"
    choose(page, name="food.png", mime="image/png", data=PNG)

    # Expected Result: Only "food.png" is selected
    expect(page.get_by_text("Photo selected: food.png")).to_be_visible()
    expect(page.get_by_text("Photo selected: food.jpg")).to_have_count(0)


#TC-121-05b: Remove photo clears the selection
def test_remove_photo_clears_selection(page):
    # Precondition: user is signed in and has chosen "food.jpg"
    fake_photo_api(page)
    open_photo_page(page)
    choose(page)

    # Steps:
    # 1. Click "Remove photo"
    page.get_by_role("button", name="Remove photo").click()

    # Expected Result: The selection and the Analyze photo button are gone
    expect(page.get_by_text("Photo selected")).to_have_count(0)
    expect(page.get_by_role("button", name="Analyze photo")).to_have_count(0)


#TC-121-06: Cancelling the file picker leaves the page unchanged
def test_cancel_file_picker(page):
    # Precondition: user is signed in and is on the AI photo page
    fake_photo_api(page)
    open_photo_page(page)
    before = page.locator("main, body").first.inner_text()

    # Steps:
    # 1. Open the file picker
    with page.expect_file_chooser() as chooser:
        page.get_by_role("button", name="Upload photo").click()
    # 2. Cancel it (choose nothing)
    chooser.value.set_files([])

    # Expected Result: The page looks the same as before step 1
    assert page.locator("main, body").first.inner_text() == before


#TC-121-07: The camera shows a clear message when it cannot be opened
def test_camera_unavailable_message(page):
    # Precondition: user is signed in, is on the AI photo page, and the browser has no camera (the test browser has none)
    fake_photo_api(page)
    open_photo_page(page)

    # Steps:
    # 1. Click "Use camera"
    page.get_by_role("button", name="Use camera").click()

    # Expected Result: A message says the camera could not be used and uploading still works
    expect(page.get_by_role("alert")).to_contain_text("camera")
    expect(page.get_by_role("button", name="Upload photo")).to_be_enabled()


# Sprint 3: Search Results and Save Generated Recipe (SCRUM-122)

#TC-122-01: A clear food photo returns a recipe draft with name, ingredients and steps
def test_food_photo_returns_result(page):
    # Precondition: user is signed in and is on the AI photo page and the AI reply is faked by the test
    fake_photo_api(page)
    open_photo_page(page)

    # Steps:
    # 1. Choose "food.jpg"
    choose(page)
    # 2. Click Analyze photo
    analyze(page)

    # Expected Result: The review shows "Veggie Stir Fry" with its ingredients and steps, and a warning
    review = page.get_by_role("region", name="Review generated recipe")
    expect(review).to_be_visible()
    expect(review.locator("input, textarea").first).to_be_visible()
    values = " ".join(review.locator("input, textarea").evaluate_all("els => els.map(e => e.value)"))
    assert "Veggie Stir Fry" in values and "2 cups broccoli" in values and "Stir fry the broccoli." in values
    expect(review.get_by_text("AI may miss allergens")).to_be_visible()


#TC-122-02: Save adds the recipe to the recipe list and it opens normally
def test_save_adds_generated_recipe(page):
    # Precondition: a photo search has returned the recipe (the reply is faked by the test)
    name = f"Veggie Stir Fry {time.time_ns()}"
    body = json.loads(json.dumps(RECIPE))
    body["recipe"]["name"] = name
    fake_photo_api(page, body=body)
    open_photo_page(page)
    choose(page)
    analyze(page)
    review = page.get_by_role("region", name="Review generated recipe")

    # Steps:
    # 1. Check "I reviewed the ingredients and instructions." and click "Save recipe"
    review.get_by_label("I reviewed the ingredients and instructions.").check()
    review.get_by_role("button", name="Save recipe").click()

    # Expected Result: The new recipe's detail page opens and the recipe is in the list
    expect(page.get_by_role("heading", level=1, name=name)).to_be_visible()
    assert name in recipe_names(page)


#TC-122-03: Discard (Cancel) saves nothing
def test_discard_saves_nothing(page):
    # Precondition: a photo search has returned the recipe (the reply is faked by the test)
    name = f"Veggie Discard {time.time_ns()}"
    body = json.loads(json.dumps(RECIPE))
    body["recipe"]["name"] = name
    fake_photo_api(page, body=body)
    open_photo_page(page)
    choose(page)
    analyze(page)
    review = page.get_by_role("region", name="Review generated recipe")

    # Steps:
    # 1. Click "Cancel"
    review.get_by_role("button", name="Cancel").click()

    # Expected Result: The review closes and the recipe is not in the list
    expect(review).to_have_count(0)
    assert name not in recipe_names(page)


#TC-122-04: Nothing is saved until I confirm
def test_nothing_saved_until_confirm(page):
    # Precondition: a photo search has returned the recipe (the reply is faked by the test)
    name = f"Veggie Unsaved {time.time_ns()}"
    body = json.loads(json.dumps(RECIPE))
    body["recipe"]["name"] = name
    fake_photo_api(page, body=body)
    open_photo_page(page)
    choose(page)
    analyze(page)
    expect(page.get_by_role("region", name="Review generated recipe")).to_be_visible()

    # Steps:
    # 1. Look at the recipe list without clicking Save

    # Expected Result: The recipe is not in the list
    assert name not in recipe_names(page)


#TC-122-04b: Save is refused until the review box is checked
def test_save_needs_review_checkbox(page):
    # Precondition: a photo search has returned the recipe (the reply is faked by the test)
    name = f"Veggie Needs Check {time.time_ns()}"
    body = json.loads(json.dumps(RECIPE))
    body["recipe"]["name"] = name
    fake_photo_api(page, body=body)
    open_photo_page(page)
    choose(page)
    analyze(page)
    review = page.get_by_role("region", name="Review generated recipe")

    # Steps:
    # 1. Click "Save recipe" without checking the review box
    review.get_by_role("button", name="Save recipe").click()

    # Expected Result: A message asks for the review and nothing is saved
    expect(review).to_contain_text("check the confirmation before saving")
    assert name not in recipe_names(page)


#TC-122-06: No match shows a friendly message
def test_no_match_shows_empty_state(page):
    # Precondition: user is signed in and is on the AI photo page and the AI reply is faked to return no recipe
    fake_photo_api(page, body={"status": "no_result", "message": "No recognizable food was found. Try a clearer food photo."})
    open_photo_page(page)

    # Steps:
    # 1. Choose "food.jpg"
    choose(page)
    # 2. Click Analyze photo
    analyze(page)

    # Expected Result: A friendly message shows and another photo can be chosen
    expect(page.get_by_role("status").filter(has_text="No recognizable food was found")).to_be_visible()
    expect(page.get_by_role("button", name="Upload photo")).to_be_enabled()


#TC-122-07: Fields can be edited before saving
def test_fields_can_be_edited_before_saving(page):
    # Precondition: a photo search has returned a recipe (the reply is faked by the test)
    name = f"Veggie Edit {time.time_ns()}"
    body = json.loads(json.dumps(RECIPE))
    body["recipe"]["name"] = name
    fake_photo_api(page, body=body)
    open_photo_page(page)
    choose(page)
    analyze(page)
    review = page.get_by_role("region", name="Review generated recipe")

    # Steps:
    # 1. Add a prep time of 25 and a line to the steps
    review.get_by_label("Prep time (minutes)").fill("25")
    steps = review.locator("textarea[name='instructions']")
    steps.fill(steps.input_value() + "\nLet it rest for 2 minutes.")
    # 2. Check the box and click "Save recipe"
    review.get_by_label("I reviewed the ingredients and instructions.").check()
    review.get_by_role("button", name="Save recipe").click()

    # Expected Result: The saved recipe has the added step
    expect(page.get_by_role("heading", level=1, name=name)).to_be_visible()
    expect(page.get_by_text("Let it rest for 2 minutes.")).to_be_visible()


# Sprint 3: AI Request Failure and Loading States (SCRUM-123)

#TC-123-01: A loading indicator shows and Analyze photo is disabled while the request runs
def test_photo_loading_state(page):
    # Precondition: the AI reply waits until the test releases it
    held = []
    fake_photo_api(page, hold=held)
    open_photo_page(page)
    choose(page)

    # Steps:
    # 1. Click Analyze photo
    analyze(page)

    # Expected Result: A loading message shows and the button cannot be clicked until the result arrives
    expect(page.get_by_text("Looking at your food photo")).to_be_visible()
    expect(page.get_by_role("button", name="Analyzing photo…")).to_be_disabled()
    page.wait_for_timeout(300)
    held[0].fulfill(status=200, content_type="application/json", body=json.dumps(RECIPE))
    expect(page.get_by_role("region", name="Review generated recipe")).to_be_visible()


#TC-123-02: A slow response can be cancelled and tried again
def test_slow_response_cancel_and_retry(page):
    # Precondition: the AI reply never arrives on the first request
    held = []
    posts = fake_photo_api(page, hold=held)
    open_photo_page(page)
    choose(page)

    # Steps:
    # 1. Click Analyze photo
    analyze(page)
    expect(page.get_by_role("button", name="Cancel analysis")).to_be_visible()
    # 2. Click "Cancel analysis"
    page.get_by_role("button", name="Cancel analysis").click()
    expect(page.get_by_role("button", name="Analyze photo")).to_be_enabled()
    # 3. Click Analyze photo again
    analyze(page)

    # Expected Result: The request stops after step 2 and a new request starts after step 3
    expect(page.get_by_text("Looking at your food photo")).to_be_visible()
    assert len(posts) == 2


#TC-123-03: A server error shows an error and keeps the photo
def test_server_error_keeps_photo(page):
    # Precondition: the server is set to fail the request
    fake_photo_api(page, body={"error": "Unable to analyze this photo. Please try again."}, status=502)
    open_photo_page(page)
    choose(page)

    # Steps:
    # 1. Click Analyze photo
    analyze(page)

    # Expected Result: An error shows, the photo is still selected, and Analyze photo can be clicked to retry
    expect(page.get_by_role("alert").filter(has_text="Unable to analyze this photo")).to_be_visible()
    expect(page.get_by_text("Photo selected: food.jpg")).to_be_visible()
    expect(page.get_by_role("button", name="Analyze photo")).to_be_enabled()


#TC-123-04: Being offline shows an error, not a blank page
def test_offline_shows_error(page):
    # Precondition: the photo page is open and the browser goes offline
    fake_photo_api(page)
    open_photo_page(page)
    choose(page)
    page.unroute("**/api/ai/photo-recipe")
    page.route("**/api/ai/photo-recipe", lambda route: route.abort("internetdisconnected") if route.request.method == "POST"
               else route.fulfill(status=200, content_type="application/json", body='{"available": true}'))

    # Steps:
    # 1. Click Analyze photo
    analyze(page)

    # Expected Result: An error message shows and the page is not blank
    expect(page.get_by_role("alert").filter(has_text="Cannot reach photo recognition")).to_be_visible()
    expect(page.get_by_role("heading", name="What could we cook?")).to_be_visible()


#TC-123-06: A reply with no meal found gives a clear message and saves nothing
def test_not_food_photo_message(page):
    # Precondition: the AI reply is faked to return no meal found
    fake_photo_api(page, body={"status": "no_result", "message": "No meal was found in this photo."})
    open_photo_page(page)
    before = len(recipe_names(page))

    # Steps:
    # 1. Choose "desk.jpg" and click Analyze photo
    choose(page, name="desk.jpg")
    analyze(page)

    # Expected Result: A message says no meal was found and nothing is saved
    expect(page.get_by_role("status").filter(has_text="No meal was found")).to_be_visible()
    assert len(recipe_names(page)) == before


#TC-123-06b: An incomplete reply is shown as an error, not a broken recipe
def test_incomplete_reply_shows_error(page):
    # Precondition: the AI reply is faked to hold a recipe with no steps
    bad = {"status": "success", "requiresConfirmation": True, "recipe": {"name": "Half Recipe", "ingredients": ["1 egg"], "steps": []}}
    fake_photo_api(page, body=bad)
    open_photo_page(page)
    choose(page)

    # Steps:
    # 1. Click Analyze photo
    analyze(page)

    # Expected Result: An incomplete recipe error shows and no review form opens
    expect(page.get_by_role("alert").filter(has_text="incomplete recipe")).to_be_visible()
    expect(page.get_by_role("region", name="Review generated recipe")).to_have_count(0)


#TC-123-07: A signed-out user is sent to login and no request is made
def test_signed_out_photo_page_redirects(browser, browser_context_args):
    # Precondition: user is signed out
    context = browser.new_context(**browser_context_args)
    page = context.new_page()
    requests = []
    page.on("request", lambda r: requests.append(r.url) if "/api/ai/photo-recipe" in r.url else None)
    try:
        # Steps:
        # 1. Go to the AI photo page address
        page.goto(f"{BASE_URL}/ai-photo")

        # Expected Result: The Login page shows and no AI request is made
        page.wait_for_url("**/login")
        assert requests == []
    finally:
        context.close()


#TC-123-08: Every failure ends on a usable page
@pytest.mark.parametrize("failure", ["server error", "offline"])
def test_failures_end_on_usable_page(page, failure):
    # Precondition: the request is set to fail in the given way
    def handle(route):
        if route.request.method == "GET":
            return route.fulfill(status=200, content_type="application/json", body='{"available": true}')
        if failure == "offline":
            return route.abort("internetdisconnected")
        route.fulfill(status=500, content_type="application/json", body='{"error": "Unable to analyze this photo. Please try again."}')
    page.route("**/api/ai/photo-recipe", handle)
    open_photo_page(page)

    # Steps:
    # 1. Choose "food.jpg" and click Analyze photo
    choose(page)
    analyze(page)
    expect(page.get_by_role("alert").first).to_be_visible()
    # 2. Click a sidebar link, then come back and choose a new photo
    page.locator("aside.app-sidebar").get_by_role("link", name="Recipes").click()
    expect(page).to_have_url(re.compile(r"/recipes$"))
    page.locator("aside.app-sidebar").get_by_role("link", name="AI Photo Search").click()
    choose(page, name="food2.png", mime="image/png", data=PNG)

    # Expected Result: The sidebar works and a new photo can be chosen
    expect(page.get_by_text("Photo selected: food2.png")).to_be_visible()


# Sprint 3: AI Recipe Generation Flow (SCRUM-151)

#TC-151-01: Upload a photo and end with a saved recipe
def test_photo_upload_to_saved_recipe(page):
    # Precondition: user is signed in and is on the AI photo page and the AI reply is faked by the test
    name = f"Veggie Flow {time.time_ns()}"
    body = json.loads(json.dumps(RECIPE))
    body["recipe"]["name"] = name
    fake_photo_api(page, body=body)
    open_photo_page(page)

    # Steps:
    # 1. Choose "food.jpg"
    choose(page)
    # 2. Click Analyze photo, then look over the result
    analyze(page)
    review = page.get_by_role("region", name="Review generated recipe")
    expect(review).to_be_visible()
    # 3. Confirm and click "Save recipe"
    review.get_by_label("I reviewed the ingredients and instructions.").check()
    review.get_by_role("button", name="Save recipe").click()
    expect(page.get_by_role("heading", level=1, name=name)).to_be_visible()
    # 4. Reload the Recipes page
    page.goto(f"{BASE_URL}/recipes")

    # Expected Result: The recipe is in the recipe list with its ingredients and steps on its detail page
    page.get_by_role("button", name=f"Open recipe: {name}").click()
    expect(page.get_by_text("2 cups broccoli")).to_be_visible()
    expect(page.get_by_text("Stir fry the broccoli.")).to_be_visible()


#TC-151-02: A failed generation saves nothing
def test_failed_generation_saves_nothing(page):
    # Precondition: the Recipes list has been counted, and the server is set to fail the request
    fake_photo_api(page, body={"error": "Unable to analyze this photo. Please try again."}, status=502)
    open_photo_page(page)
    before = len(recipe_names(page))

    # Steps:
    # 1. Choose "food.jpg" and click Analyze photo
    choose(page)
    analyze(page)
    expect(page.get_by_role("alert").filter(has_text="Unable to analyze")).to_be_visible()

    # Expected Result: An error shows and the number of recipes is the same as before
    assert len(recipe_names(page)) == before


#TC-151-04: Not configured: Analyze photo is disabled and a setup message shows
def test_photo_not_configured(page):
    # Precondition: the server reports that photo recognition is not set up
    fake_photo_api(page, available=False)

    # Steps:
    # 1. Open the AI photo page and choose "food.jpg"
    open_photo_page(page)
    choose(page)

    # Expected Result: A message says photo recognition is not configured and Analyze photo is disabled
    expect(page.get_by_text("Photo recognition is not configured yet")).to_be_visible()
    expect(page.get_by_role("button", name="Analyze photo")).to_be_disabled()


# Ingredient search on the AI Photo Search page (not in the Sprint 3 plan, added because it is on the page)

#TC-151-05: Searching by ingredients lists matching recipes
def test_ingredient_search_lists_matches(page):
    # Precondition: the recipe "Egg Spinach Scramble" with the ingredients eggs and spinach exists
    name = f"Egg Spinach Scramble {time.time_ns()}"
    page.request.post(f"{BASE_URL}/api/recipes", headers={"X-Panned-Out-Request": "1"}, form={
        "name": name, "category": "My Recipes", "difficulty": "Easy", "mealType": "Breakfast",
        "ingredients": "3 eggs\n1 cup spinach", "instructions": "Whisk\nCook", "prepTime": "10",
        "calories": "250", "protein": "18", "fat": "15", "carbohydrates": "4", "fiber": "1"})
    open_photo_page(page)

    # Steps:
    # 1. Type "eggs, spinach" in the ingredients box and click search
    page.locator("#ai-ingredient-input").fill("eggs, spinach")
    page.locator(".ai-photo-side").get_by_role("button").first.click()

    # Expected Result: The recipe shows in the results
    expect(page.get_by_text(name)).to_be_visible()
