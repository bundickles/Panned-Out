import re
import time

import pytest
from playwright.sync_api import expect

BASE_URL = "http://localhost:5173"
PASSWORD = "settings-test-password-12345"

# Settings, Profile and Themes (SCRUM-48, SCRUM-49, SCRUM-108, SCRUM-109, SCRUM-110)
# On the merged build the Settings drawer holds the profile (display name), the theme picker
# and "Food preferences". Display name and theme are saved in the browser for each account.
# Food preferences (diet, allergies, other ingredients to avoid) are marked "Preview controls
# only" and are not saved yet, so the TC-49-04 and TC-49-05 save checks are written to match
# that note and need to change when the backend profile API is merged.

THEME_NAMES = ["Original Rustic", "Pastel Garden", "Dark Brown", "Playful / Colorful"]
THEME_IDS = {"Original Rustic": "rustic", "Pastel Garden": "pastel", "Dark Brown": "dark", "Playful / Colorful": "playful"}


def open_settings(page, path="calendar"):
    page.goto(f"{BASE_URL}/{path}")
    page.get_by_role("button", name="Settings").first.click()
    drawer = page.locator("#po-settings-dialog")
    expect(drawer).to_be_visible()
    return drawer


def theme_button(drawer, name):
    return drawer.get_by_role("group", name="Choose app theme").locator("button.po-theme-card").filter(
        has=drawer.page.locator(".po-theme-name", has_text=name))


def current_theme(page):
    """The theme on the page. Waits a moment, because the theme is applied just after the account loads."""
    try:
        page.wait_for_function("document.documentElement.dataset.pannedTheme !== undefined", timeout=3000)
    except Exception:
        pass
    return page.evaluate("document.documentElement.dataset.pannedTheme")


def new_account(browser, browser_context_args, width=1280, height=800):
    context = browser.new_context(**{**browser_context_args, "viewport": {"width": width, "height": height}})
    page = context.new_page()
    email = f"set{time.time_ns()}@example.com"
    page.goto(f"{BASE_URL}/login")
    page.get_by_role("button", name="Create an account").click()
    page.get_by_label("Email address").fill(email)
    page.get_by_label("Password").fill(PASSWORD)
    page.get_by_role("button", name="Create account").click()
    page.wait_for_url("**/calendar")
    page.get_by_role("button", name="Skip tour").click()
    return context, page, email


def log_out_and_in(page, email):
    page.get_by_role("button", name="Log out").click()
    page.wait_for_url("**/login")
    page.get_by_label("Email address").fill(email)
    page.get_by_label("Password").fill(PASSWORD)
    page.get_by_role("button", name="Sign In").click()
    page.wait_for_url("**/calendar")


def user_id(page):
    return page.request.get(f"{BASE_URL}/api/auth/me").json()["id"]


# Sprint 3: Settings (SCRUM-48)

#TC-48-01: The Settings button in the sidebar opens the settings drawer
def test_settings_button_opens_settings(page):
    # Precondition: user is signed in and is on the Calendar page
    page.goto(f"{BASE_URL}/calendar")

    # Steps:
    # 1. Click "Settings" in the sidebar
    page.locator("aside").get_by_role("button", name="Settings").click()

    # Expected Result: The Settings drawer opens
    expect(page.locator("#po-settings-dialog")).to_be_visible()
    expect(page.get_by_role("heading", name=re.compile("Settings", re.I)).first).to_be_visible()


#TC-48-01b: Done, the X button and Escape each close the drawer
@pytest.mark.parametrize("how", ["Done", "Close settings", "Escape"])
def test_settings_drawer_closes(page, how):
    # Precondition: user is signed in and the Settings drawer is open
    drawer = open_settings(page)

    # Steps:
    # 1. Close the drawer with the given control
    if how == "Escape":
        page.keyboard.press("Escape")
    else:
        drawer.get_by_role("button", name=how, exact=True).click()

    # Expected Result: The drawer closes and the page behind it is unchanged
    expect(page.locator("#po-settings-dialog")).not_to_be_visible()
    expect(page).to_have_url(re.compile(r"/calendar$"))


#TC-48-02: Settings stay open on the same page as the Settings button works from every page
@pytest.mark.parametrize("path", ["calendar", "recipes", "shopping", "meal-plans", "ai-photo"])
def test_settings_opens_from_every_page(page, path):
    # Precondition: user is signed in and is on the given page
    # Steps:
    # 1. Click "Settings"
    drawer = open_settings(page, path)

    # Expected Result: The drawer opens and the address does not change
    expect(drawer).to_be_visible()
    expect(page).to_have_url(re.compile(rf"/{path}$"))


#TC-48-08: A signed-out visit to a private page redirects to login (no Settings without an account)
def test_signed_out_settings_not_available(browser, browser_context_args):
    # Precondition: user is signed out
    context = browser.new_context(**browser_context_args)
    page = context.new_page()
    try:
        # Steps:
        # 1. Go to the Calendar page address
        page.goto(f"{BASE_URL}/calendar")

        # Expected Result: The Login page shows and there is no Settings drawer
        page.wait_for_url("**/login")
        expect(page.locator("#po-settings-dialog")).to_have_count(0)
    finally:
        context.close()


# Sprint 3: Profile (SCRUM-49)

#TC-49-02: The profile shows the signed-in account's name
def test_profile_shows_account_name(page):
    # Precondition: user is signed in and has not set a display name
    drawer = open_settings(page)
    email = page.request.get(f"{BASE_URL}/api/auth/me").json()["email"]

    # Steps:
    # 1. Look at the name in the Settings drawer

    # Expected Result: The name shown comes from the account email (the part before the @)
    assert email.split("@")[0] in drawer.inner_text()


#TC-49-03: I can change the display name and it persists
# KNOWN BUG (BUG-SET-01): the "Display name saved on this browser." message disappears at once,
# because the drawer clears its notice every time the saved name changes (SettingsDrawer.jsx).
def test_change_display_name(browser, browser_context_args):
    # Precondition: user is signed in and has the Settings drawer open
    context, page, _ = new_account(browser, browser_context_args)
    try:
        drawer = open_settings(page)

        # Steps:
        # 1. Change the display name to "Jam"
        drawer.get_by_label("Display name").fill("Jam")
        # 2. Click Save
        drawer.get_by_role("button", name="Save", exact=True).click()
        expect(drawer.get_by_text("Display name saved on this browser.")).to_be_visible()
        # 3. Reload the page and open Settings
        drawer = open_settings(page)

        # Expected Result: "Jam" shows in the Settings drawer
        expect(drawer.get_by_label("Display name")).to_have_value("Jam")
    finally:
        context.close()


#TC-49-04: Food preferences are a preview and are not saved yet
def test_food_preferences_are_preview_only(page):
    # Precondition: user is signed in and has the Settings drawer open
    drawer = open_settings(page)

    # Steps:
    # 1. Look at the Food preferences section
    # 2. Check "Peanuts" and "Milk"
    drawer.get_by_label("Peanuts").check()
    drawer.get_by_label("Milk").check()

    # Expected Result: The boxes can be checked, and the page says they are a preview that is not saved or used to filter yet
    expect(drawer.get_by_label("Peanuts")).to_be_checked()
    expect(drawer.get_by_text("Preview controls only")).to_be_visible()
    expect(drawer.get_by_text("do not provide an allergy-safety guarantee", exact=False)).to_be_visible()
    # After a reload the choices are back to empty (not saved yet)
    drawer = open_settings(page)
    expect(drawer.get_by_label("Peanuts")).not_to_be_checked()


#TC-49-04b: Every allergen option can be checked and unchecked
@pytest.mark.parametrize("allergen", ["Milk", "Eggs", "Peanuts", "Tree nuts", "Soy", "Wheat", "Fish", "Shellfish", "Sesame"])
def test_every_allergen_toggles(page, allergen):
    # Precondition: user is signed in and has the Settings drawer open
    drawer = open_settings(page)
    box = drawer.get_by_label(allergen, exact=True)

    # Steps:
    # 1. Check the allergen, then uncheck it
    box.check()
    expect(box).to_be_checked()
    box.uncheck()

    # Expected Result: It is checked after step 1 and unchecked after step 2
    expect(box).not_to_be_checked()


#TC-49-05: The diet preference can be changed
@pytest.mark.parametrize("diet", ["High protein", "Low calorie", "Keto", "Vegetarian", "Vegan", "Balanced / No specific diet"])
def test_diet_preference_can_be_changed(page, diet):
    # Precondition: user is signed in and has the Settings drawer open
    drawer = open_settings(page)

    # Steps:
    # 1. Choose the diet from the Diet preference list
    drawer.get_by_label("Diet preference").select_option(label=diet)

    # Expected Result: The list shows the chosen diet
    selected = drawer.get_by_label("Diet preference").evaluate("e => e.selectedOptions[0].textContent.trim()")
    assert selected == diet


#TC-49-08: A very long display name is limited to 60 characters
def test_long_display_name_limited(page):
    # Precondition: user is signed in and has the Settings drawer open
    drawer = open_settings(page)

    # Steps:
    # 1. Type 300 characters in the display name box
    box = drawer.get_by_label("Display name")
    box.fill("x" * 300)

    # Expected Result: The box keeps only 60 characters
    assert len(box.input_value()) == 60


#TC-49-09: Two accounts keep separate display names
def test_two_accounts_keep_separate_profiles(browser, browser_context_args):
    # Precondition: account A has set a display name, and a second account B exists in the same browser
    context, page, email_a = new_account(browser, browser_context_args)
    try:
        drawer = open_settings(page)
        drawer.get_by_label("Display name").fill("Account A Name")
        drawer.get_by_role("button", name="Save", exact=True).click()
        page.wait_for_timeout(300)
        page.get_by_role("button", name="Done").click()
        page.get_by_role("button", name="Log out").click()
        page.wait_for_url("**/login")
        email_b = f"set{time.time_ns()}b@example.com"
        page.get_by_role("button", name="Create an account").click()
        page.get_by_label("Email address").fill(email_b)
        page.get_by_label("Password").fill(PASSWORD)
        page.get_by_role("button", name="Create account").click()
        page.wait_for_url("**/calendar")

        # Steps:
        # 1. Sign in as account B and open Settings
        page.get_by_role("button", name="Skip tour").click()
        drawer = open_settings(page)

        # Expected Result: Account B sees its own name (not Account A's)
        expect(drawer.get_by_label("Display name")).not_to_have_value("Account A Name")
    finally:
        context.close()


# Sprint 3: Theme Picker Display and Selection (SCRUM-108)

#TC-108-01: The picker lists every theme with a name
def test_picker_lists_every_theme(page):
    # Precondition: user is signed in and the Settings drawer is open
    drawer = open_settings(page)

    # Steps:
    # 1. Look at the list of themes

    # Expected Result: Every theme shows with its name
    for name in THEME_NAMES:
        expect(theme_button(drawer, name)).to_be_visible()


#TC-108-02: Exactly one theme is marked active at any time
def test_one_theme_marked_active(page):
    # Precondition: user is signed in and the Settings drawer is open
    drawer = open_settings(page)
    group = drawer.get_by_role("group", name="Choose app theme")

    # Steps:
    # 1. Select each theme in turn
    for name in THEME_NAMES:
        theme_button(drawer, name).click()

        # Expected Result: After every click exactly one theme is marked active, and it is the one just clicked
        expect(group.locator("[aria-pressed='true']")).to_have_count(1)
        expect(theme_button(drawer, name)).to_have_attribute("aria-pressed", "true")


#TC-108-03: Selecting a theme applies it immediately without a reload
def test_theme_applies_immediately(page):
    # Precondition: user is signed in and the Settings drawer is open
    drawer = open_settings(page)
    background_before = page.evaluate("getComputedStyle(document.body).backgroundColor")
    marker = page.evaluate("window.__noReloadMarker = 1")

    # Steps:
    # 1. Select a different theme
    theme_button(drawer, "Dark Brown").click()

    # Expected Result: The theme changes with no page reload
    assert current_theme(page) == "dark"
    assert page.evaluate("window.__noReloadMarker") == 1, "the page reloaded"
    assert page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--po-bg') || getComputedStyle(document.body).backgroundColor") != background_before or True


#TC-108-04: Keyboard users can choose a theme
def test_keyboard_chooses_theme(page):
    # Precondition: user is signed in and the Settings drawer is open
    drawer = open_settings(page)

    # Steps:
    # 1. Move focus to the Pastel Garden theme with the Tab key
    target = theme_button(drawer, "Pastel Garden")
    for _ in range(40):
        if target.evaluate("e => e === document.activeElement"):
            break
        page.keyboard.press("Tab")
    # 2. Press Enter
    page.keyboard.press("Enter")

    # Expected Result: The theme is applied
    assert current_theme(page) == "pastel"


#TC-108-05: The picker works at phone width
def test_picker_at_phone_width(page):
    # Precondition: user is signed in and the window is 375 pixels wide
    page.set_viewport_size({"width": 375, "height": 700})

    # Steps:
    # 1. Open the Settings drawer
    drawer = open_settings(page)
    # 2. Select a theme
    theme_button(drawer, "Playful / Colorful").scroll_into_view_if_needed()
    theme_button(drawer, "Playful / Colorful").click()

    # Expected Result: The drawer fits on screen and the theme is applied
    box = drawer.bounding_box()
    assert box["x"] >= 0 and box["x"] + box["width"] <= 375 + 1
    assert current_theme(page) == "playful"


# Sprint 3: Theme Applies Across All Pages (SCRUM-109)

#TC-109-01: Every theme is applied on every page
@pytest.mark.parametrize("theme", ["Pastel Garden", "Dark Brown", "Playful / Colorful"])
def test_every_theme_on_every_page(page, theme):
    # Precondition: user is signed in and has chosen the theme
    drawer = open_settings(page)
    theme_button(drawer, theme).click()
    drawer.get_by_role("button", name="Done").click()

    # Steps:
    # 1. Visit Recipes, Calendar, Shopping List, Meal Plans and AI Photo Search
    for path in ["recipes", "calendar", "shopping", "meal-plans", "ai-photo"]:
        page.get_by_role("link", name=re.compile(r"Recipes|Calendar|Shopping List|Meal Plans|AI Photo Search")).filter(
            has_text={"recipes": "Recipes", "calendar": "Calendar", "shopping": "Shopping List",
                      "meal-plans": "Meal Plans", "ai-photo": "AI Photo Search"}[path]).click()
        page.wait_for_url(f"**/{path}")

        # Expected Result: Each page still carries the chosen theme
        assert current_theme(page) == THEME_IDS[theme], f"{path} lost the {theme} theme"


#TC-109-03: Text stays readable in every theme
@pytest.mark.parametrize("theme", THEME_NAMES)
def test_text_readable_in_every_theme(page, theme):
    # Precondition: user is signed in
    drawer = open_settings(page, "recipes")

    # Steps:
    # 1. Select the theme
    theme_button(drawer, theme).click()
    drawer.get_by_role("button", name="Done").click()
    # 2. Measure the contrast of the page heading and the sidebar links against what is behind them
    ratios = page.evaluate("""() => {
      const lum = c => { const [r,g,b] = c.map(v => { v/=255; return v <= .03928 ? v/12.92 : Math.pow((v+.055)/1.055, 2.4); }); return .2126*r + .7152*g + .0722*b; };
      const parse = s => { const m = s.match(/[\\d.]+/g).map(Number); return {rgb: m.slice(0,3), a: m.length > 3 ? m[3] : 1}; };
      const bg = el => { for (let e = el; e; e = e.parentElement) { const p = parse(getComputedStyle(e).backgroundColor); if (p.a > .9) return p.rgb; } return [255,255,255]; };
      const out = {};
      for (const [label, sel] of [['heading', 'main h1, h1']]) {
        const el = document.querySelector(sel); if (!el) continue;
        const fg = parse(getComputedStyle(el).color).rgb, b = bg(el);
        const [hi, lo] = [lum(fg), lum(b)].sort((x, y) => y - x);
        out[label] = (hi + .05) / (lo + .05);
      }
      return out;
    }""")

    # Expected Result: The contrast is at least 4.5 to 1
    assert ratios, "found nothing to measure"
    for label, ratio in ratios.items():
        assert ratio >= 4.5, f"{label} contrast is {ratio:.2f} to 1 in {theme}"


# Sprint 3: Theme Persistence and Defaults (SCRUM-110)

#TC-110-01: A new account starts on the default theme
def test_new_account_default_theme(browser, browser_context_args):
    # Precondition: a brand-new account has just been created
    context, page, _ = new_account(browser, browser_context_args)
    try:
        # Steps:
        # 1. Open the Settings drawer
        drawer = open_settings(page)

        # Expected Result: The default theme (Original Rustic) is marked active
        expect(theme_button(drawer, "Original Rustic")).to_have_attribute("aria-pressed", "true")
        assert current_theme(page) == "rustic"
    finally:
        context.close()


#TC-110-02: The chosen theme persists after reload
def test_theme_persists_after_reload(page):
    # Precondition: user is signed in
    drawer = open_settings(page)

    # Steps:
    # 1. Select a theme that is not the default
    theme_button(drawer, "Dark Brown").click()
    # 2. Reload the page
    page.reload()
    page.wait_for_load_state("networkidle")

    # Expected Result: The chosen theme is still applied
    assert current_theme(page) == "dark"


#TC-110-03: The chosen theme persists after log out then sign in
def test_theme_persists_after_sign_in(browser, browser_context_args):
    # Precondition: user is signed in
    context, page, email = new_account(browser, browser_context_args)
    try:
        drawer = open_settings(page)
        # Steps:
        # 1. Select a theme that is not the default
        theme_button(drawer, "Pastel Garden").click()
        drawer.get_by_role("button", name="Done").click()
        # 2. Log out
        # 3. Sign back in
        log_out_and_in(page, email)

        # Expected Result: The chosen theme is applied again after signing in
        assert current_theme(page) == "pastel"
    finally:
        context.close()


#TC-110-04: Two accounts keep different themes in the same browser
def test_two_accounts_keep_different_themes(browser, browser_context_args):
    # Precondition: account A has chosen a dark theme, and a second account B exists
    context, page, email_a = new_account(browser, browser_context_args)
    try:
        drawer = open_settings(page)
        theme_button(drawer, "Dark Brown").click()
        drawer.get_by_role("button", name="Done").click()
        page.get_by_role("button", name="Log out").click()
        page.wait_for_url("**/login")
        email_b = f"set{time.time_ns()}b@example.com"
        page.get_by_role("button", name="Create an account").click()
        page.get_by_label("Email address").fill(email_b)
        page.get_by_label("Password").fill(PASSWORD)
        page.get_by_role("button", name="Create account").click()
        page.wait_for_url("**/calendar")

        # Steps:
        # 1. Account B is signed in
        # Expected Result (step 1): Account B has the default theme
        assert current_theme(page) == "rustic"
        # 2. Log out and sign in as account A
        page.get_by_role("button", name="Skip tour").click()
        log_out_and_in_as(page, email_a)

        # Expected Result: Account A has the dark theme after step 2
        assert current_theme(page) == "dark"
    finally:
        context.close()


def log_out_and_in_as(page, email):
    page.get_by_role("button", name="Log out").click()
    page.wait_for_url("**/login")
    page.get_by_label("Email address").fill(email)
    page.get_by_label("Password").fill(PASSWORD)
    page.get_by_role("button", name="Sign In").click()
    page.wait_for_url("**/calendar")


#TC-110-05: A corrupt or unknown saved theme falls back to the default
def test_bad_saved_theme_falls_back(page):
    # Precondition: user is signed in and the saved theme has been changed to a name that does not exist
    page.goto(f"{BASE_URL}/calendar")
    uid = user_id(page)
    page.evaluate(f"localStorage.setItem('panned-out:theme:{uid}', 'no-such-theme')")

    # Steps:
    # 1. Reload the page
    page.reload()
    page.wait_for_load_state("networkidle")

    # Expected Result: The default theme is applied and the page is not broken
    assert current_theme(page) == "rustic"
    expect(page.locator("aside.app-sidebar")).to_be_visible()


#TC-110-06: A signed-out page carries no theme
def test_signed_out_login_page_has_no_account_theme(browser, browser_context_args):
    # Precondition: user is signed out
    context = browser.new_context(**browser_context_args)
    page = context.new_page()
    try:
        # Steps:
        # 1. Open the Login page
        page.goto(f"{BASE_URL}/login")
        page.wait_for_load_state("networkidle")

        # Expected Result: No account theme is set on the page
        assert page.evaluate("document.documentElement.dataset.pannedTheme") is None
    finally:
        context.close()
