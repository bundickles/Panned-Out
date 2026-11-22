import json
import re
import pytest
from playwright.sync_api import expect

BASE_URL = "http://localhost:5173"


# App Navigation (SCRUM-143)

#TC-162-01: The sidebar stays in place while the page content scrolls (SCRUM-162)
@pytest.mark.parametrize("path", ["calendar", "recipes"])
def test_sidebar_stays_in_place_while_content_scrolls(page, path):
    # Precondition: user is signed in and the window is short enough that the page content must scroll
    page.set_viewport_size({"width": 1200, "height": 500})
    page.goto(f"{BASE_URL}/{path}")
    sidebar = page.locator("aside.app-sidebar")
    content = page.locator(".calendar-content, .recipes-content")
    expect(sidebar).to_be_visible()
    top_before = sidebar.bounding_box()["y"]

    # Steps:
    # 1. Scroll the page content all the way down
    content.evaluate("e => e.scrollTo(0, e.scrollHeight)")

    # Expected Result: The content scrolled, the sidebar did not move, and the
    # logo and Settings link are still on screen
    assert content.evaluate("e => e.scrollTop") > 0, "content did not scroll"
    assert page.evaluate("window.scrollY") == 0, "the whole page scrolled instead of just the content"
    assert sidebar.bounding_box()["y"] == top_before
    expect(sidebar.locator(".sidebar-logo, .app-sidebar-logo")).to_be_in_viewport()
    expect(sidebar.locator("a, button").filter(has_text="Settings")).to_be_in_viewport()


# Sprint 3: Onboarding Tutorial (SCRUM-174, built as the "App tour")
# The merged tour has 5 steps (Welcome, Recipes, Calendar, Shopping List, Meal Plans), Back and
# Next buttons, "Skip tour" and "Finish tour". It opens by itself for an account that has not
# dismissed it, and the "App tour" button in the top bar opens it again. It remembers the
# dismissal in the browser (local storage) for each account.
import time

TOUR_PASSWORD = "tour-test-password-12345"


def new_account_page(browser, browser_context_args, width=1280, height=800):
    """A fresh browser context with a brand-new account that has just signed up. Returns (context, page, email)."""
    context = browser.new_context(**{**browser_context_args, "viewport": {"width": width, "height": height}})
    page = context.new_page()
    email = f"tour{time.time_ns()}@example.com"
    page.goto(f"{BASE_URL}/login")
    page.get_by_role("button", name="Create an account").click()
    page.get_by_label("Email address").fill(email)
    page.get_by_label("Password").fill(TOUR_PASSWORD)
    page.get_by_role("button", name="Create account").click()
    page.wait_for_url("**/calendar")
    return context, page, email


def sign_in_again(page, email):
    page.goto(f"{BASE_URL}/login")
    page.get_by_label("Email address").fill(email)
    page.get_by_label("Password").fill(TOUR_PASSWORD)
    page.get_by_role("button", name="Sign In").click()
    page.wait_for_url("**/calendar")


#TC-174-01: A new account sees the tour after signing up
def test_new_account_sees_tutorial(browser, browser_context_args):
    # Precondition: user is on the Login page
    # Steps:
    # 1. Create a new account
    context, page, _ = new_account_page(browser, browser_context_args)
    try:
        # Expected Result: The tour shows on the first page after signing up
        tour = page.locator("dialog.app-walkthrough")
        expect(tour).to_be_visible()
        expect(tour.get_by_role("heading", name="Welcome to Panned Out")).to_be_visible()
        expect(tour.get_by_text("Step 1 of 5")).to_be_visible()
    finally:
        context.close()


#TC-174-02: It points out Recipes, Calendar, Shopping List and Meal Plans
def test_tutorial_covers_main_pages(browser, browser_context_args):
    # Precondition: a brand-new account has just been created and the tour is on step 1
    context, page, _ = new_account_page(browser, browser_context_args)
    try:
        tour = page.locator("dialog.app-walkthrough")
        text = []
        # Steps:
        # 1. Click "Next" through every step and read each one
        for step in range(5):
            text.append(tour.inner_text())
            if step < 4:
                tour.get_by_role("button", name=re.compile("Show me around|Next")).click()

        # Expected Result: The steps name Recipes, Calendar, Shopping List and Meal Plans
        everything = " ".join(text)
        for page_name in ["Recipes", "Calendar", "Shopping List", "Meal Plans"]:
            assert page_name in everything, f"the tour never names {page_name}"
    finally:
        context.close()


#TC-174-04: Next and Back move between steps
def test_tutorial_next_and_back(browser, browser_context_args):
    # Precondition: a brand-new account has just been created and the tour is on step 1
    context, page, _ = new_account_page(browser, browser_context_args)
    try:
        tour = page.locator("dialog.app-walkthrough")
        back = tour.get_by_role("button", name="Back")
        expect(back).to_be_disabled()

        # Steps:
        # 1. Click "Show me around"
        tour.get_by_role("button", name="Show me around").click()
        expect(tour.get_by_text("Step 2 of 5")).to_be_visible()
        # 2. Click "Next"
        tour.get_by_role("button", name="Next").click()
        expect(tour.get_by_text("Step 3 of 5")).to_be_visible()
        # 3. Click "Back"
        back.click()

        # Expected Result: Step 2 shows, then step 3, then step 2, and "Back" is disabled on step 1
        expect(tour.get_by_text("Step 2 of 5")).to_be_visible()
        back.click()
        expect(tour.get_by_text("Step 1 of 5")).to_be_visible()
        expect(back).to_be_disabled()
    finally:
        context.close()


#TC-174-05: Skip ends the tour at any step
@pytest.mark.parametrize("step", ["first", "middle"])
def test_skip_ends_tutorial(browser, browser_context_args, step):
    # Precondition: a brand-new account has just been created and the tour is showing
    context, page, _ = new_account_page(browser, browser_context_args)
    try:
        tour = page.locator("dialog.app-walkthrough")
        # Steps:
        # 1. Go to the given step
        if step == "middle":
            tour.get_by_role("button", name="Show me around").click()
            tour.get_by_role("button", name="Next").click()
        # 2. Click "Skip tour"
        tour.get_by_role("button", name="Skip tour").click()

        # Expected Result: The tour closes and the app can be used
        expect(tour).not_to_be_visible()
        page.locator("aside.app-sidebar").get_by_role("link", name="Recipes").click()
        expect(page).to_have_url(re.compile(r"/recipes$"))
    finally:
        context.close()


#TC-174-06: Finish ends the tour after the last step
def test_finish_ends_tutorial(browser, browser_context_args):
    # Precondition: a brand-new account has just been created and the tour is on step 1
    context, page, _ = new_account_page(browser, browser_context_args)
    try:
        tour = page.locator("dialog.app-walkthrough")
        # Steps:
        # 1. Click "Next" until the last step
        tour.get_by_role("button", name="Show me around").click()
        for _ in range(3):
            tour.get_by_role("button", name="Next").click()
        expect(tour.get_by_text("Step 5 of 5")).to_be_visible()
        # 2. Click "Finish tour"
        tour.get_by_role("button", name="Finish tour").click()

        # Expected Result: The tour closes
        expect(tour).not_to_be_visible()
    finally:
        context.close()


#TC-174-07: It does not show again on the next sign in
def test_tutorial_not_shown_on_next_sign_in(browser, browser_context_args):
    # Precondition: a new account has finished the tour
    context, page, email = new_account_page(browser, browser_context_args)
    try:
        page.locator("dialog.app-walkthrough").get_by_role("button", name="Skip tour").click()
        # Steps:
        # 1. Log out
        page.get_by_role("button", name="Log out").click()
        page.wait_for_url("**/login")
        # 2. Sign back in
        sign_in_again(page, email)

        # Expected Result: The tour does not show
        expect(page.locator("dialog.app-walkthrough")).not_to_be_visible()
    finally:
        context.close()


#TC-174-08: It does not show again after a reload
def test_tutorial_not_shown_after_reload(browser, browser_context_args):
    # Precondition: a new account has finished the tour
    context, page, _ = new_account_page(browser, browser_context_args)
    try:
        page.locator("dialog.app-walkthrough").get_by_role("button", name="Skip tour").click()
        # Steps:
        # 1. Reload the page
        page.reload()
        page.wait_for_load_state("networkidle")

        # Expected Result: The tour does not show
        expect(page.get_by_role("button", name="App tour")).to_be_visible()
        expect(page.locator("dialog.app-walkthrough")).not_to_be_visible()
    finally:
        context.close()


#TC-174-09: The "App tour" button opens the tour again from step 1
def test_app_tour_button_reopens_tour(browser, browser_context_args):
    # Precondition: a new account has skipped the tour
    context, page, _ = new_account_page(browser, browser_context_args)
    try:
        tour = page.locator("dialog.app-walkthrough")
        tour.get_by_role("button", name="Show me around").click()
        tour.get_by_role("button", name="Skip tour").click()
        # Steps:
        # 1. Click "App tour" in the top bar
        page.get_by_role("button", name="App tour").click()

        # Expected Result: The tour shows again on step 1
        expect(tour).to_be_visible()
        expect(tour.get_by_text("Step 1 of 5")).to_be_visible()
    finally:
        context.close()


#TC-174-09b: The Escape key closes the tour
def test_escape_closes_tutorial(browser, browser_context_args):
    # Precondition: a brand-new account has just been created and the tour is showing
    context, page, _ = new_account_page(browser, browser_context_args)
    try:
        tour = page.locator("dialog.app-walkthrough")
        # Steps:
        # 1. Press Escape
        page.keyboard.press("Escape")

        # Expected Result: The tour closes
        expect(tour).not_to_be_visible()
    finally:
        context.close()


#TC-174-10: The tour works at phone width
def test_tutorial_at_phone_width(browser, browser_context_args):
    # Precondition: a brand-new account has just been created and the window is 375 pixels wide
    context, page, _ = new_account_page(browser, browser_context_args, width=375, height=700)
    try:
        tour = page.locator("dialog.app-walkthrough")
        # Steps:
        # 1. Click "Next" through every step
        for step in range(5):
            # Expected Result: Every step's text and buttons fit on screen with no sideways scrolling
            box = tour.bounding_box()
            assert box["x"] >= 0 and box["x"] + box["width"] <= 375, f"step {step + 1} is wider than the screen"
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
            primary = tour.locator(".walkthrough-primary")
            expect(primary).to_be_in_viewport()
            if step < 4:
                primary.click()
    finally:
        context.close()


# Sprint 3: AI Chatbot (SCRUM-176, built as the "Kitchen assistant")
# The chat requests are faked by the tests, so answers are the same every run.
# TC-176-12 (the real AI) is run by hand and stays out of this file.

def fake_chat(page, reply="Boil it for 8 to 10 minutes.", available=True, status=200, delay_ms=0):
    """Fake GET and POST /api/chat. Returns the list of requests the page sent."""
    sent = []

    def handle(route):
        request = route.request
        if request.method == "GET":
            return route.fulfill(status=200, content_type="application/json", body=json.dumps({"available": available}))
        sent.append(request.post_data or "")
        if delay_ms:
            time.sleep(delay_ms / 1000)
        if status != 200:
            return route.fulfill(status=status, content_type="application/json", body=json.dumps({"error": "The assistant could not answer. Please try again."}))
        return route.fulfill(status=200, content_type="application/json", body=json.dumps({"reply": reply}))
    page.route("**/api/chat", handle)
    return sent


def open_chat(page, path="calendar"):
    page.goto(f"{BASE_URL}/{path}")
    page.get_by_role("button", name="Kitchen assistant").click()
    panel = page.locator("#kitchen-chat")
    expect(panel).to_be_visible()
    return panel


#TC-176-01: The chatbot opens and closes from any page
@pytest.mark.parametrize("path", ["recipes", "calendar", "meal-plans", "shopping"])
def test_chatbot_opens_and_closes(page, path):
    # Precondition: user is signed in and is on the given page
    fake_chat(page)
    page.goto(f"{BASE_URL}/{path}")
    url_before = page.url

    # Steps:
    # 1. Click the Kitchen assistant button
    page.get_by_role("button", name="Kitchen assistant").click()
    panel = page.locator("#kitchen-chat")
    expect(panel).to_be_visible()
    # 2. Click close
    panel.get_by_role("button", name="Close kitchen assistant").click()

    # Expected Result: The chatbot opens, then closes, and the page behind it has not changed
    expect(panel).not_to_be_visible()
    assert page.url == url_before


#TC-176-02: A cooking question gets an answer
def test_cooking_question_gets_answer(page):
    # Precondition: user is signed in, the chatbot is open, and the chatbot request is faked by the test
    fake_chat(page, reply="Boil it for 8 to 10 minutes.")
    panel = open_chat(page)

    # Steps:
    # 1. Type "How long do I boil an egg?"
    panel.get_by_label("Your message").fill("How long do I boil an egg?")
    # 2. Click send
    panel.get_by_role("button", name="Send").click()

    # Expected Result: The question shows in the chat with the reply under it
    log = panel.get_by_role("log", name="Conversation")
    expect(log).to_contain_text("How long do I boil an egg?")
    expect(log).to_contain_text("Boil it for 8 to 10 minutes.")


#TC-176-04: The question is sent to the server in the request
def test_meal_planning_question_is_sent(page):
    # Precondition: user is signed in, the chatbot is open, and the chatbot request is faked by the test
    sent = fake_chat(page, reply="Try pasta, tacos and soup.")
    panel = open_chat(page)

    # Steps:
    # 1. Send "Plan 3 dinners for this week"
    panel.get_by_label("Your message").fill("Plan 3 dinners for this week")
    panel.get_by_role("button", name="Send").click()

    # Expected Result: The reply shows, and the request that was sent held the question
    expect(panel.get_by_role("log", name="Conversation")).to_contain_text("Try pasta, tacos and soup.")
    assert len(sent) == 1 and "Plan+3+dinners+for+this+week" in sent[0].replace("%20", "+")


#TC-176-05: A reply that redirects an off-topic question shows as a normal message
def test_off_topic_question_redirects(page):
    # Precondition: user is signed in, the chatbot is open, and the chatbot request is faked to return the redirect message
    redirect = "I can only help with cooking and using Panned Out."
    fake_chat(page, reply=redirect)
    panel = open_chat(page)

    # Steps:
    # 1. Send "Who won the game last night?"
    panel.get_by_label("Your message").fill("Who won the game last night?")
    panel.get_by_role("button", name="Send").click()

    # Expected Result: The redirect shows as a normal message, not as an error
    expect(panel.get_by_role("log", name="Conversation")).to_contain_text(redirect)
    expect(panel.get_by_role("alert")).to_have_count(0)


#TC-176-06: An empty message cannot be sent
@pytest.mark.parametrize("message", ["", "    "])
def test_empty_message_cannot_be_sent(page, message):
    # Precondition: user is signed in, the chatbot is open, and the chatbot request is faked by the test
    sent = fake_chat(page)
    panel = open_chat(page)

    # Steps:
    # 1. Leave the message box empty, or type only spaces
    panel.get_by_label("Your message").fill(message)

    # Expected Result: Send cannot be clicked, so nothing is sent and no request is made
    expect(panel.get_by_role("button", name="Send")).to_be_disabled()
    assert sent == []


#TC-176-07: A very long message is limited and does not break the chat
def test_very_long_message(page):
    # Precondition: user is signed in, the chatbot is open, and the chatbot request is faked by the test
    fake_chat(page)
    panel = open_chat(page)

    # Steps:
    # 1. Type a message of 5,000 characters
    box = panel.get_by_label("Your message")
    box.fill("x" * 5000)

    # Expected Result: The box stops at its 2,000 character limit, and nothing overflows
    assert len(box.input_value()) == 2000
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")


#TC-176-08: A loading state shows while it answers
def test_chatbot_loading_state(page):
    # Precondition: user is signed in, the chatbot is open, and the chatbot request waits before replying
    state = {"release": None}

    def handle(route):
        if route.request.method == "GET":
            return route.fulfill(status=200, content_type="application/json", body='{"available": true}')
        state["hold"] = route
    page.route("**/api/chat", handle)
    panel = open_chat(page)

    # Steps:
    # 1. Send a message
    panel.get_by_label("Your message").fill("Hello")
    panel.get_by_role("button", name="Send").click()

    # Expected Result: A loading indicator shows and send is disabled until the reply arrives
    expect(panel.get_by_text("Thinking…")).to_be_visible()
    expect(panel.get_by_role("button", name="Sending…")).to_be_disabled()
    page.wait_for_timeout(300)
    state["hold"].fulfill(status=200, content_type="application/json", body='{"reply": "Hi there."}')
    expect(panel.get_by_role("log", name="Conversation")).to_contain_text("Hi there.")
    expect(panel.get_by_text("Thinking…")).to_have_count(0)


#TC-176-09: A failure shows an error and keeps the question to try again
def test_chatbot_failure_shows_error_and_keeps_question(page):
    # Precondition: user is signed in, the chatbot is open, and the chatbot request is faked to fail once
    calls = {"n": 0}

    def handle(route):
        if route.request.method == "GET":
            return route.fulfill(status=200, content_type="application/json", body='{"available": true}')
        calls["n"] += 1
        if calls["n"] == 1:
            return route.fulfill(status=502, content_type="application/json", body='{"error": "The assistant could not answer. Please try again."}')
        return route.fulfill(status=200, content_type="application/json", body='{"reply": "Second try worked."}')
    page.route("**/api/chat", handle)
    panel = open_chat(page)

    # Steps:
    # 1. Send a message
    panel.get_by_label("Your message").fill("Help me cook")
    panel.get_by_role("button", name="Send").click()

    # Expected Result: An error shows after step 1 and the question is put back in the box
    expect(panel.get_by_role("alert")).to_contain_text("could not answer")
    expect(panel.get_by_label("Your message")).to_have_value("Help me cook")
    # 2. Click Send again
    panel.get_by_role("button", name="Send").click()
    # Expected Result: The reply shows after step 2 with the question in the chat
    log = panel.get_by_role("log", name="Conversation")
    expect(log).to_contain_text("Second try worked.")
    expect(log).to_contain_text("Help me cook")


#TC-176-10: A timeout shows an error, not an endless spinner
def test_chatbot_timeout_shows_error(page):
    # Precondition: user is signed in, the chatbot is open, and the chatbot request is faked to never answer
    def handle(route):
        if route.request.method == "GET":
            return route.fulfill(status=200, content_type="application/json", body='{"available": true}')
        # never answered
    page.route("**/api/chat", handle)
    page.clock.install()
    panel = open_chat(page)

    # Steps:
    # 1. Send a message
    panel.get_by_label("Your message").fill("Anyone there?")
    panel.get_by_role("button", name="Send").click()
    expect(panel.get_by_text("Thinking…")).to_be_visible()
    # 2. Wait past the 30 second time limit
    page.clock.run_for(31_000)

    # Expected Result: A timeout message shows and the question is back in the box
    expect(panel.get_by_role("alert")).to_contain_text("timed out")
    expect(panel.get_by_label("Your message")).to_have_value("Anyone there?")


#TC-176-10b: When the assistant is not set up, a setup message shows and Send is disabled
def test_chatbot_not_connected_message(page):
    # Precondition: user is signed in and the server reports the assistant is not connected
    fake_chat(page, available=False)

    # Steps:
    # 1. Open the Kitchen assistant
    panel = open_chat(page)
    panel.get_by_label("Your message").fill("Hello")

    # Expected Result: A setup message shows and Send is disabled
    expect(panel.get_by_text("hasn’t been connected yet")).to_be_visible()
    expect(panel.get_by_role("button", name="Send")).to_be_disabled()


#TC-176-10c: New chat clears the conversation
def test_new_chat_clears_conversation(page):
    # Precondition: user is signed in and the chat already holds one question and reply
    fake_chat(page, reply="Eight minutes.")
    panel = open_chat(page)
    panel.get_by_label("Your message").fill("Boil an egg?")
    panel.get_by_role("button", name="Send").click()
    expect(panel.get_by_role("log", name="Conversation")).to_contain_text("Eight minutes.")

    # Steps:
    # 1. Click "New chat"
    panel.get_by_role("button", name="New chat").click()

    # Expected Result: The conversation is empty and the welcome message shows
    expect(panel.get_by_text("What’s cooking?")).to_be_visible()
    expect(panel.get_by_role("log", name="Conversation")).not_to_contain_text("Eight minutes.")


#TC-176-11: A signed-out user cannot use it
def test_signed_out_user_cannot_use_chatbot(browser, browser_context_args):
    # Precondition: user is signed out and is on the Login page
    context = browser.new_context(**browser_context_args)
    page = context.new_page()
    try:
        # Steps:
        # 1. Look for the chatbot button
        page.goto(f"{BASE_URL}/login")
        page.wait_for_load_state("networkidle")

        # Expected Result: There is no chatbot button
        expect(page.get_by_role("button", name="Kitchen assistant")).to_have_count(0)
    finally:
        context.close()
