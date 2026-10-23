"""Shared sign-in for the Playwright tests.

Once login is merged (PR #11) the Calendar and Recipes pages are private, so every test that opens
them directly would be sent to the Login page. This file fixes that in one place:

- One test account is created per test run (not per test, because sign-in attempts are rate limited).
- Every test gets a fresh browser that is already signed in as that account.
- Before login is merged, there is no Login page, so nothing happens and tests run as before.
- Tests in SIGNED_OUT_MODULES keep the normal signed-out browser (they test login itself).

Tests share the one account, so give recipes unique names and use dates that other tests do not use.
"""
import tempfile
import time
from pathlib import Path

import pytest

BASE_URL = "http://localhost:5173"
TEST_PASSWORD = "shared-test-account-password-123"
SIGNED_OUT_MODULES = {"test_login", "test_login_mealplan_flow"}


@pytest.fixture(scope="session")
def signed_in_state(browser, browser_context_args):
    """Create the shared account once and save its signed-in browser state. None if there is no login yet."""
    context = browser.new_context(**browser_context_args)
    page = context.new_page()
    try:
        page.goto(f"{BASE_URL}/calendar")
        page.wait_for_load_state("networkidle")
        if "/login" not in page.url:
            return None   # login is not merged yet: the calendar opens without signing in
        page.get_by_role("button", name="Create an account").click()
        page.get_by_label("Email address").fill(f"suite{time.time_ns()}@example.com")
        page.get_by_label("Password").fill(TEST_PASSWORD)
        page.get_by_role("button", name="Create account").click()
        page.wait_for_url("**/calendar")
        state_file = Path(tempfile.gettempdir()) / f"panned_out_state_{time.time_ns()}.json"
        context.storage_state(path=str(state_file))
        return str(state_file)
    finally:
        context.close()


@pytest.fixture
def page(browser, browser_context_args, request, signed_in_state):
    """A page that is already signed in, unless the test file is one of the login test files."""
    args = dict(browser_context_args)
    if signed_in_state and request.module.__name__ not in SIGNED_OUT_MODULES:
        args["storage_state"] = signed_in_state
    context = browser.new_context(**args)
    page = context.new_page()
    yield page
    context.close()
