import pytest

# TC-26-01: Successful login with valid credentials
@pytest.mark.skip(reason="Login page not yet implemented")
def test_successful_login_with_valid_credentials():
    # Precondition: a user account already exists, user is on the Login page

    # Steps:
    # 1. Enter the correct username
    # 2. Enter the correct password
    # 3. Click "Log In"

    # Expected Result: user is redirected to their dashboard, session is active
    assert False  # placeholder, replace with real check once login page exists

@pytest.mark.skip(reason="Login page not yet implemented")
def test_correct_user_wrong_password():
    # Precondition: a user account already exists, user is on the Login page

    # Steps:
    # 1. Enter the correct username
    # 2. Enter the incorrect password
    # 3. Click "Log In"

    # Expected Result: user is given an "incorrect password" message
    assert False  # placeholder, replace with real check once login page exists

@pytest.mark.skip(reason="Login page not yet implemented")
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
