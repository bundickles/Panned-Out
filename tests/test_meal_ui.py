"""Real browser integration, isolated servers and data.
Requires Python playwright and an installed Edge browser (or PLAYWRIGHT_CHANNEL).
Compile backend first, then run: python -m unittest discover -s tests -p test_meal_ui.py
"""
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
import unittest
from urllib.request import urlopen
from urllib.error import URLError
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
PASSWORD = 'a long browser test password'


class MealUiTest(unittest.TestCase):
    def test_add_meal_calendar_flow(self):
        with tempfile.TemporaryDirectory() as directory:
            api = subprocess.Popen(['java', '-cp', 'backend/build', 'RecipeServer', '0',
                                    str(Path(directory) / 'recipes.properties')], stdout=subprocess.PIPE, text=True, cwd=ROOT)
            vite = None
            try:
                api_url = api.stdout.readline().strip().split('Recipe API: ')[1]
                with socket.socket() as sock:
                    sock.bind(('127.0.0.1', 0))
                    port = sock.getsockname()[1]
                env = {**os.environ, 'PANNED_OUT_API_TARGET': api_url}
                vite = subprocess.Popen(['node', 'node_modules/vite/bin/vite.js', '--host', '127.0.0.1',
                                         '--port', str(port), '--strictPort'], cwd=ROOT / 'frontend', env=env,
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                url = f'http://127.0.0.1:{port}'
                for _ in range(100):
                    if vite.poll() is not None:
                        self.fail('Vite exited before becoming ready')
                    try:
                        with urlopen(url, timeout=1):
                            break
                    except (URLError, OSError):
                        time.sleep(0.1)
                else:
                    self.fail('Vite did not become ready')
                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch(channel=os.environ.get('PLAYWRIGHT_CHANNEL', 'msedge'))
                    try:
                        context = browser.new_context()
                        page = context.new_page()
                        errors = []
                        page.on('pageerror', lambda error: errors.append(str(error)))
                        page.goto(url + '/calendar')
                        expect(page).to_have_url(url + '/login')
                        page.get_by_role('button', name='Create an account', exact=True).click()
                        page.get_by_label('Email address').fill('alice@example.com')
                        page.get_by_label('Password', exact=True).fill(PASSWORD)
                        page.get_by_role('button', name='Create account', exact=True).click()
                        expect(page).to_have_url(url + '/calendar')
                        page.get_by_role('button', name='+ Add Meal', exact=True).first.click()
                        expect(page.get_by_text('You have no saved recipes yet.', exact=False)).to_be_visible()
                        page.get_by_role('link', name='Create a recipe').click()
                        page.get_by_role('button', name='+ Add Recipe', exact=True).first.click()
                        page.get_by_label('Recipe name').fill('Calendar dinner')
                        page.get_by_label('Ingredients', exact=True).fill('Rice')
                        page.get_by_label('Instructions', exact=True).fill('Cook rice')
                        page.get_by_role('button', name='Save recipe', exact=True).click()
                        expect(page.get_by_role('heading', name='Calendar dinner')).to_be_visible()
                        page.locator('.sidebar-nav button').filter(has_text='Calendar').click()
                        selected = page.locator('.calendar-cell.selected').get_attribute('aria-label')
                        page.get_by_role('button', name='+ Add Meal', exact=True).first.click()
                        page.get_by_label('Recipe', exact=True).select_option(label='Calendar dinner')
                        page.get_by_label('Meal type', exact=True).select_option('Dinner')
                        # A failed save keeps the form and selection available for retry.
                        page.route('**/api/meals', lambda route: route.abort())
                        page.get_by_role('button', name='Save meal', exact=True).click()
                        expect(page.get_by_role('alert')).to_contain_text('Cannot reach the server')
                        expect(page.get_by_label('Recipe', exact=True)).to_have_value('1')
                        page.unroute('**/api/meals')
                        page.get_by_role('button', name='Save meal', exact=True).click()
                        expect(page.get_by_role('heading', name='Calendar dinner')).to_be_visible()
                        expect(page.locator('.calendar-cell.selected .meal-count')).to_have_text('1 planned')
                        page.locator('.calendar-cell[aria-label]:not(.selected)').first.click()
                        expect(page.get_by_role('heading', name='No meals for this day.')).to_be_visible()
                        page.get_by_role('button', name=selected, exact=True).click()
                        page.reload()
                        expect(page.get_by_role('heading', name='Calendar dinner')).to_be_visible()
                        # Another account starts with an empty calendar.
                        page.get_by_role('button', name='Log out', exact=True).click()
                        expect(page).to_have_url(url + '/login')
                        page.get_by_role('button', name='Create an account', exact=True).click()
                        page.get_by_label('Email address').fill('bob@example.com')
                        page.get_by_label('Password', exact=True).fill(PASSWORD)
                        page.get_by_role('button', name='Create account', exact=True).click()
                        expect(page).to_have_url(url + '/calendar')
                        expect(page.get_by_role('heading', name='No meals for this day.')).to_be_visible()
                        expect(page.get_by_role('heading', name='Calendar dinner')).to_have_count(0)
                        page.get_by_role('button', name='Log out', exact=True).click()
                        expect(page).to_have_url(url + '/login')
                        page.get_by_label('Email address').fill('alice@example.com')
                        page.get_by_label('Password', exact=True).fill(PASSWORD)
                        page.get_by_role('button', name='Sign In', exact=True).click()
                        expect(page).to_have_url(url + '/calendar')
                        expect(page.get_by_role('heading', name='Calendar dinner')).to_be_visible()
                        page.screenshot(path=str(ROOT / 'backend/build/meal-calendar-check.png'), full_page=True)
                        page.get_by_role('button', name='Remove Calendar dinner from calendar', exact=True).click()
                        expect(page.get_by_role('heading', name='No meals for this day.')).to_be_visible()
                        page.reload()
                        expect(page.get_by_role('heading', name='No meals for this day.')).to_be_visible()
                        self.assertEqual(errors, [])
                        context.close()
                    finally:
                        browser.close()
            finally:
                if vite is not None:
                    vite.terminate()
                    vite.wait(timeout=10)
                api.terminate()
                api.wait(timeout=10)
                api.stdout.close()


if __name__ == '__main__':
    unittest.main()
