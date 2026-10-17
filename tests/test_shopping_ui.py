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


class ShoppingUiTest(unittest.TestCase):
    def test_shopping_integration(self):
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
                        page.goto(url + '/shopping')
                        expect(page).to_have_url(url + '/login')
                        # Seed real private data through the same origin and cookie jar as the UI.
                        response = context.request.post(url + '/api/auth/register', form={'email': 'alice@example.com', 'password': PASSWORD}, headers={'X-Panned-Out-Request': '1'})
                        self.assertEqual(response.status, 201)
                        recipe = context.request.post(url + '/api/recipes', form={'name': 'Alice rice', 'ingredients': 'Rice\nBeans', 'instructions': 'Cook', 'category': 'My Recipes', 'difficulty': 'Easy', 'mealType': 'Dinner'}, headers={'X-Panned-Out-Request': '1'}).json()
                        context.request.post(url + '/api/meals', form={'recipeId': recipe['id'], 'date': '2026-10-04', 'mealType': 'Dinner'}, headers={'X-Panned-Out-Request': '1'})
                        shopping = url + '/shopping?start=2026-10-01&end=2026-10-07'
                        page.goto(shopping)
                        expect(page.get_by_text('Rice', exact=True)).to_be_visible()
                        expect(page.get_by_text('Alice rice — 2026-10-04', exact=True)).to_have_count(2)
                        page.get_by_label('End date').fill('2026-10-02')
                        expect(page.get_by_text('No ingredients found', exact=False)).to_be_visible()
                        page.get_by_label('Start date').fill('2026-10-08')
                        expect(page.get_by_role('alert')).to_contain_text('Start date must be')
                        page.get_by_label('Start date').fill('2026-10-01')
                        expect(page.get_by_text('No ingredients found', exact=False)).to_be_visible()
                        page.route('**/api/shopping-list?**', lambda route: route.abort())
                        page.get_by_label('End date').fill('2026-10-07')
                        expect(page.get_by_role('alert')).to_contain_text('Cannot reach')
                        page.unroute('**/api/shopping-list?**')
                        page.get_by_role('button', name='Retry', exact=True).click()
                        expect(page.get_by_text('Rice', exact=True)).to_be_visible()
                        # Let an obsolete response arrive after a newer empty result.
                        pending = []
                        page.route('**/api/shopping-list?**', lambda route: pending.append(route))
                        page.get_by_role('button', name='Generate from Meal Plan').click()
                        expect(page.get_by_role('status')).to_contain_text('Loading')
                        page.wait_for_timeout(100)
                        page.get_by_label('End date').fill('2026-10-02')
                        page.wait_for_timeout(100)
                        self.assertEqual(len(pending), 2)
                        pending[1].fulfill(json={'start': '2026-10-01', 'end': '2026-10-02', 'items': [], 'warnings': []})
                        expect(page.get_by_text('No ingredients found', exact=False)).to_be_visible()
                        pending[0].fulfill(json={'items': [{'name': 'STALE RESULT', 'occurrences': 1, 'sources': []}], 'warnings': []})
                        expect(page.get_by_text('STALE RESULT')).to_have_count(0)
                        page.unroute('**/api/shopping-list?**')
                        context.request.delete(url + '/api/recipes/' + str(recipe['id']), headers={'X-Panned-Out-Request': '1'})
                        page.get_by_label('End date').fill('2026-10-07')
                        expect(page.get_by_role('heading', name='Some ingredients are unavailable')).to_be_visible()
                        page.screenshot(path=str(ROOT / 'backend/build/shopping-desktop.png'), full_page=True)
                        page.set_viewport_size({'width': 390, 'height': 844})
                        page.screenshot(path=str(ROOT / 'backend/build/shopping-mobile.png'), full_page=True)
                        page.set_viewport_size({'width': 1280, 'height': 900})
                        # Expiry routes through the normal login screen and drops private results.
                        page.route('**/api/shopping-list?**', lambda route: route.fulfill(status=401, json={'error': 'Please sign in to continue.'}))
                        page.get_by_role('button', name='Generate from Meal Plan').click()
                        expect(page).to_have_url(url + '/login')
                        expect(page.get_by_text('Alice rice', exact=True)).to_have_count(0)
                        page.unroute('**/api/shopping-list?**')
                        context.request.post(url + '/api/auth/register', form={'email': 'bob@example.com', 'password': PASSWORD}, headers={'X-Panned-Out-Request': '1'})
                        page.goto(shopping)
                        expect(page.get_by_text('No ingredients found', exact=False)).to_be_visible()
                        expect(page.get_by_role('heading', name='Some ingredients are unavailable')).to_have_count(0)
                        page.get_by_role('button', name='Log out', exact=True).click()
                        expect(page).to_have_url(url + '/login')
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
