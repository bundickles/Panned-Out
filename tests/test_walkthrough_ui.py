"""SCRUM-165 browser regression. Start Vite, then run with Python Playwright:
PANNED_OUT_UI_URL=http://127.0.0.1:5174 python -m unittest discover -s tests -p test_walkthrough_ui.py
Uses mocked API responses; requires Edge or PLAYWRIGHT_CHANNEL.
"""
import os
import unittest
from playwright.sync_api import sync_playwright, expect


class WalkthroughTest(unittest.TestCase):
    def test_first_visit_completion_replay_and_account_isolation(self):
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel=os.environ.get('PLAYWRIGHT_CHANNEL', 'msedge'))
            try:
                page = browser.new_page()
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                account = {'id': 1, 'email': 'cook@example.com'}
                page.route('**/api/auth/me', lambda route: route.fulfill(json=account))
                page.route('**/api/recipes', lambda route: route.fulfill(json=[]))
                base = os.environ.get('PANNED_OUT_UI_URL', 'http://127.0.0.1:5174')
                page.goto(base + '/recipes')
                dialog = page.get_by_role('dialog')
                expect(dialog).to_be_visible()
                expect(dialog.get_by_role('heading', name='Welcome to Panned Out')).to_be_focused()
                expect(dialog.get_by_role('button', name='Back', exact=True)).to_be_disabled()
                dialog.get_by_role('button', name='Show me around').click()
                expect(dialog.get_by_role('heading', name='Keep your favorite recipes')).to_be_focused()
                dialog.get_by_role('button', name='Back', exact=True).click()
                expect(dialog.get_by_text('Step 1 of 5')).to_be_visible()
                dialog.get_by_role('button', name='Show me around').click()
                for title in ('Make room for meals', 'Bring your shopping together', 'Find your next meal idea'):
                    dialog.get_by_role('button', name='Next', exact=True).click()
                    expect(dialog.get_by_role('heading', name=title)).to_be_focused()
                dialog.get_by_role('button', name='Finish tour').click()
                expect(dialog).not_to_be_visible()
                expect(page.get_by_role('button', name='App tour')).to_be_focused()
                expect(page).to_have_url(base + '/recipes')
                page.reload()
                expect(page.get_by_role('button', name='App tour')).to_be_visible()
                expect(dialog).not_to_be_visible()
                page.get_by_role('button', name='App tour').click()
                expect(dialog.get_by_text('Step 1 of 5')).to_be_visible()
                page.keyboard.press('Escape')
                expect(dialog).not_to_be_visible()
                # A different account on the same browser gets its own first-visit tour.
                account['id'] = 2
                page.reload()
                expect(dialog).to_be_visible()
                page.set_viewport_size({'width': 375, 'height': 667})
                self.assertTrue(dialog.evaluate('(el) => el.scrollWidth <= el.clientWidth'))
                page.screenshot(path='/private/tmp/panned-walkthrough-mobile.png')
                # Keyboard traversal stays inside the modal.
                for _ in range(6):
                    page.keyboard.press('Tab')
                    self.assertTrue(dialog.evaluate('(el) => el.contains(document.activeElement)'))
                dialog.get_by_role('button', name='Skip tour').click()
                page.reload()
                expect(page.get_by_role('button', name='App tour')).to_be_visible()
                expect(dialog).not_to_be_visible()
                # Signed-out visitors never see the tour.
                account.clear()
                page.route('**/api/auth/me', lambda route: route.fulfill(status=401, json={'error': 'Sign in'}))
                page.reload()
                expect(page.get_by_role('heading', name='Welcome back!')).to_be_visible()
                expect(page.get_by_role('button', name='App tour')).to_have_count(0)
                self.assertEqual(errors, [])
            finally:
                browser.close()

    def test_storage_unavailable(self):
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel=os.environ.get('PLAYWRIGHT_CHANNEL', 'msedge'))
            try:
                page = browser.new_page()
                page.add_init_script("Object.defineProperty(window, 'localStorage', {get() {throw new Error('Storage blocked')}})")
                page.route('**/api/auth/me', lambda route: route.fulfill(json={'id': 3, 'email': 'cook@example.com'}))
                page.route('**/api/recipes', lambda route: route.fulfill(json=[]))
                page.goto(os.environ.get('PANNED_OUT_UI_URL', 'http://127.0.0.1:5174') + '/recipes')
                dialog = page.get_by_role('dialog')
                expect(dialog).to_be_visible()
                dialog.get_by_role('button', name='Skip tour').click()
                expect(dialog).not_to_be_visible()
                page.get_by_role('button', name='App tour').click()
                expect(dialog).to_be_visible()
            finally:
                browser.close()
