import pytest
import uuid
from playwright.sync_api import expect

BASE_URL = "http://localhost:5173"
TEST_PASSWORD = "a-very-long-test-password"

def unique_email():
    return f"testuser+{uuid.uuid4().hex[:10]}@test.com"

def register(page, email, password):
    page.goto(f"{BASE_URL}/login")
    page.get_by_role("button", name="Create an account").click()
    page.get_by_label("Email address").fill(email)
    page.get_by_label("Password").fill(password)
    page.get_by_role("button", name="Create account").click()
    page.wait_for_url("**/calendar")

# TC-26-01: Register a new account with valid credentials
def test_register_new_account_with_valid_credentials(page):
    # Steps:
    # 1. Build a fresh, never-used email
    email = unique_email()
    # 2. Register that email with a valid 15+ char password
    register(page, email, TEST_PASSWORD)
    # 3. Assert log in page was landed on
    expect(page).to_have_url(f"{BASE_URL}/calendar")


def test_regsiter_password_too_short_blocked_by_validation(page):
    # Steps:
    # 1. Go to login, swtich to Create Account
    page.goto(f"{BASE_URL}/login")
    page.get_by_text("Create Account").click()

    # 2. Fill email with fresh address
    page.get_by_label("Email").fill(unique_email())

    # 3. Fill password with something shorter than expected
    password_input = page.get_by_label("Password")
    password_input.fill("short1")
    page.get_by_role("button", name="Create Account").click()

    # 4. Try to submit
    is_valid = password_input.evaluate("el => el.validity.valid")

    assert is_valid is False
    expect(page).to_have_url(f"{BASE_URL}/login")

#TC-26-03: Registering with an email that already has an account shows an error
def test_register_duplicate_email_shows_error(page):
    # Steps:
    # 1. Register once with a fresh email, succeeds
    email = unique_email()
    register(page, email, TEST_PASSWORD)

    # 2. Go back to login and try to register again with that same email
    page.goto(f"{BASE_URL}/login")
    page.get_by_role("button", name="Create an account").click()
    page.get_by_label("Email address").fill(email)
    page.get_by_label("Password").fill(TEST_PASSWORD)
    page.get_by_role("button", name="Create account").click()

    # Expected Result: an "already exists" error is shown, user stays on login
    error = page.get_by_role("alert")
    assert "already exists" in error.text_content()
    assert "/login" in page.url


#TC-26-04: Login with valid credentials
def test_login_with_valid_credentials(page):
    # Precondition: register a fresh account first so there's a real one to log into
    email = unique_email()
    register(page, email, TEST_PASSWORD)

    # Steps:
    # 1. Go back to the login page (simulating a brand new visit)
    page.goto(f"{BASE_URL}/login")
    # 2. Enter the registered email
    page.get_by_label("Email address").fill(email)
    # 3. Enter the matching password
    page.get_by_label("Password").fill(TEST_PASSWORD)
    # 4. Click "Sign In"
    page.get_by_role("button", name="Sign In").click()

    # Expected Result: user lands on the calendar page
    page.wait_for_url("**/calendar")
    assert "/calendar" in page.url


#TC-26-05: Wrong password shows a generic error
def test_login_wrong_password_shows_generic_error(page):
    # Precondition: register a fresh account with a known password
    email = unique_email()
    register(page, email, TEST_PASSWORD)

    # Steps:
    # 1. Go to login
    page.goto(f"{BASE_URL}/login")
    # 2. Enter the right email
    page.get_by_label("Email address").fill(email)
    # 3. Enter the wrong password
    page.get_by_label("Password").fill("totally-wrong-password")
    # 4. Click "Sign In"
    page.get_by_role("button", name="Sign In").click()

    # Expected Result: a generic "Invalid email or password" error shows
    # (same message as the nonexistent-email case below, on purpose, so the
    # error never reveals which part was wrong)
    error = page.get_by_role("alert")
    assert "Invalid email or password" in error.text_content()


#TC-26-06: Nonexistent email shows the same generic error
def test_login_nonexistent_email_shows_same_generic_error(page):
    # Steps:
    # 1. Go straight to login, skip registration entirely
    page.goto(f"{BASE_URL}/login")
    # 2. Enter an email that's never been registered
    page.get_by_label("Email address").fill(unique_email())
    # 3. Enter any password
    page.get_by_label("Password").fill(TEST_PASSWORD)
    # 4. Click "Sign In"
    page.get_by_role("button", name="Sign In").click()

    # Expected Result: same "Invalid email or password" message as TC-26-05
    # (proves the backend isn't revealing whether the account exists)
    error = page.get_by_role("alert")
    assert "Invalid email or password" in error.text_content()


#TC-26-07: Blank email is blocked by validation
def test_login_blank_email_blocked_by_validation(page):
    # Steps:
    # 1. Go to login
    page.goto(f"{BASE_URL}/login")
    # 2. Leave email blank, fill in a password
    email_input = page.get_by_label("Email address")
    page.get_by_label("Password").fill(TEST_PASSWORD)
    # 3. Try to submit
    page.get_by_role("button", name="Sign In").click()

    # Expected Result: the email field fails native HTML validation (required),
    # so no server request is even attempted
    is_valid = email_input.evaluate("el => el.validity.valid")
    assert is_valid is False


#TC-26-08: Blank password is blocked by validation
def test_login_blank_password_blocked_by_validation(page):
    # Steps:
    # 1. Go to login
    page.goto(f"{BASE_URL}/login")
    # 2. Fill in email, leave password blank
    page.get_by_label("Email address").fill(unique_email())
    password_input = page.get_by_label("Password")
    # 3. Try to submit
    page.get_by_role("button", name="Sign In").click()

    # Expected Result: the password field fails native HTML validation (required)
    is_valid = password_input.evaluate("el => el.validity.valid")
    assert is_valid is False


#TC-26-06: Username and password both left blank blocked by validation
def test_login_both_fields_blank_blocked_by_validation(page):
    # Steps:
    # 1. Go to login
    page.goto(f"{BASE_URL}/login")
    # 2. Leave both email and password blank
    email_input = page.get_by_label("Email address")
    password_input = page.get_by_label("Password")
    # 3. Try to submit
    page.get_by_role("button", name="Sign In").click()

    # Expected Result: both required fields fail native HTML validation,
    # so no server request is even attempted
    assert email_input.evaluate("el => el.validity.valid") is False
    assert password_input.evaluate("el => el.validity.valid") is False


#TC-26-09: Too many failed logins triggers the rate limit
def test_too_many_failed_logins_triggers_rate_limit(page):
    # Precondition: register a fresh account so there's a real email to target
    email = unique_email()
    register(page, email, TEST_PASSWORD)
    page.goto(f"{BASE_URL}/login")
    error = page.get_by_role("alert")

    # Steps:
    # 1. Attempt to log in with the wrong password, over and over
    # (the backend allows 20 attempts per 15 min per IP before rejecting with 429)
    # 2. Loop 21 times, one more than the limit
    for attempt in range(21):
        page.get_by_label("Email address").fill(email)
        page.get_by_label("Password").fill("totally-wrong-password")
        page.get_by_role("button", name="Sign In").click()
        error.wait_for()

    # Expected Result: on that 21st attempt, the message switches to the
    # rate-limit error instead of the normal "invalid credentials" one
    assert "Too many sign-in attempts" in error.text_content()


#TC-26-10: Session persists after closing and reopening the browser
def test_session_persists_after_reopening_browser(browser):
    # Steps:
    # 1. Open a browser context, register/log in a fresh account
    context1 = browser.new_context()
    page1 = context1.new_page()
    email = unique_email()
    register(page1, email, TEST_PASSWORD)

    # 2. Save that context's cookies/storage
    # (this is how we simulate "closing and reopening the browser" without
    # actually closing the test process)
    storage = context1.storage_state()
    context1.close()

    # 3. Open a brand new context loaded with the saved storage state
    # (this re-injects the HttpOnly session cookie)
    context2 = browser.new_context(storage_state=storage)
    page2 = context2.new_page()
    # 4. Visit the calendar page directly in the new context
    page2.goto(f"{BASE_URL}/calendar")

    # Expected Result: user is not bounced back to login
    # (proves the 8-hour session cookie actually persisted)
    assert "/calendar" in page2.url
    context2.close()


#TC-26-11: Logout returns to login and blocks protected routes
def test_logout_returns_to_login_and_blocks_protected_routes(page):
    # Precondition: register/log in a fresh account, lands on calendar
    email = unique_email()
    register(page, email, TEST_PASSWORD)

    # Steps:
    # 1. Click the Sign Out control
    page.get_by_role("button", name="Sign Out").click()
    page.wait_for_url("**/login")

    # 2. Try to navigate directly to the calendar page again
    page.goto(f"{BASE_URL}/calendar")

    # Expected Result: redirected back to login both times
    # (proves logout actually killed the session server-side, not just the UI)
    assert "/login" in page.url


#TC-26-12: Logout syncs across open tabs
def test_logout_syncs_across_open_tabs(context):
    # Steps:
    # 1. Open "tab A" and register/log in, lands on calendar
    tab_a = context.new_page()
    email = unique_email()
    register(tab_a, email, TEST_PASSWORD)

    # 2. Open "tab B" in the same context (shares the same session)
    tab_b = context.new_page()
    tab_b.goto(f"{BASE_URL}/calendar")
    assert "/calendar" in tab_b.url

    # 3. In tab A, click Sign Out
    tab_a.get_by_role("button", name="Sign Out").click()
    tab_a.wait_for_url("**/login")

    # Expected Result: tab B also gets redirected to login on its own
    # (proves the cross-tab storage-event listener wakes the other tab up
    # instead of leaving it logged in until a manual reload)
    tab_b.wait_for_url("**/login")
    assert "/login" in tab_b.url


def test_username_does_not_exist():
    # Precondition: a user account already exists, user is on the Login page

    # Steps:
    # 1. Enter invalid username
    # 2. Enter any password 
    # 3. Click "Log In"

    # Expected Result: user is given a "username does not exist" message 
    assert False  # placeholder, replace with real check once login page exists

@pytest.mark.skip(reason="Login page not yet implemented")
def test_username_blank_password_filled():
    # Precondition: a user account already exists, user is on the Login page

    # Steps:
    # 1. Leave username field blank 
    # 2. Enter any password
    # 3. Click "Log In"

    # Expected Result: user is given a "please enter a user name" message 
    assert False  # placeholder, replace with real check once login page exists

@pytest.mark.skip(reason="Login page not yet implemented")
def test_username_filled_password_blank():
    # Precondition: a user account already exists, user is on the Login page

    # Steps:
    # 1. Enter any username 
    # 2. Leave password field blank 
    # 3. Click "Log In"

    # Expected Result: user is given a "please enter a password" message 
    assert False  # placeholder, replace with real check once login page exists

@pytest.mark.skip(reason="Login page not yet implemented")
def test_username_and_password_left_blank():
    # Precondition: a user account already exists, user is on the Login page

    # Steps:
    # 1. Leave username field blank
    # 2. Leave password field blank
    # 3. Click "Log In"

    # Expected Result: user is given a "please fill out required fields" message 
    assert False  # placeholder, replace with real check once login page exists

@pytest.mark.skip(reason="Login page not yet implemented")
def test_session_persists_after_closing_and_reopening_browser():
    # Precondition: a user account already exists, user has successfully logged in
    # and has an active session

    # Steps:
    # 1. Close the browser completely (not just the tab)
    # 2. Reopen the browser
    # 3. Navigate back to the app's URL

    # Expected Result: user is still logged in and lands on their dashboard,
    # rather than being redirected to the Login page
    assert False  # placeholder, replace with real check once login page exists

@pytest.mark.skip(reason="Login page not yet implemented")
def test_logout_returns_to_login_page():
    # Precondition: a user account already exists, user has successfully logged in
    # and has an active session
    
    # Steps:
    # 1. Click "Log out"
    # 2. Navigate back to protected page's URL
    
    # Expected Result: user is redirected back to Log in rather than let in
    assert False  # placeholder, replace with real check once login page exists
