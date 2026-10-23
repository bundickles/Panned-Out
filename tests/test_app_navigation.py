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
    sidebar = page.locator("aside")
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
