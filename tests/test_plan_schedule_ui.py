"""SCRUM-135 real browser/API scheduling. Starts isolated Java and Vite servers.
Compile backend first; install frontend dependencies and Python Playwright.
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


class PlanScheduleUiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(temp.cleanup)
        api = subprocess.Popen(['java', '-cp', 'backend/build', 'RecipeServer', '0',
                                str(Path(temp.name) / 'recipes.properties')], cwd=ROOT,
                               stdout=subprocess.PIPE, text=True)
        def stop_api():
            api.terminate(); api.wait(timeout=10); api.stdout.close()
        cls.addClassCleanup(stop_api)
        api_url = api.stdout.readline().strip().split('Recipe API: ')[1]
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        cls.base = f'http://127.0.0.1:{port}'
        vite = subprocess.Popen(['node', 'node_modules/vite/bin/vite.js', '--host', '127.0.0.1',
                                 '--port', str(port), '--strictPort'], cwd=ROOT / 'frontend',
                                env={**os.environ, 'PANNED_OUT_API_TARGET': api_url},
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        def stop_vite():
            vite.terminate(); vite.wait(timeout=10)
        cls.addClassCleanup(stop_vite)
        for _ in range(100):
            if vite.poll() is not None:
                raise RuntimeError('Vite exited before becoming ready')
            try:
                with urlopen(cls.base, timeout=1): return
            except (URLError, OSError): time.sleep(0.1)
        raise RuntimeError('Vite did not become ready')

    def test_schedule_failure_retry_calendar_and_empty_category(self):
        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel=os.environ.get('PLAYWRIGHT_CHANNEL', 'msedge'))
            try:
                context = browser.new_context()
                page = context.new_page()
                headers = {'X-Panned-Out-Request': '1'}
                response = context.request.post(self.base + '/api/auth/register', headers=headers,
                                                form={'email': 'schedule@example.com', 'password': 'a long test password for plans'})
                self.assertEqual(response.status, 201)
                recipes = []
                for name in ('Protein bowl', 'Protein soup'):
                    response = context.request.post(self.base + '/api/recipes', headers=headers,
                        form=dict(name=name, ingredients='Beans', instructions='Cook', category='High Protein', difficulty='Easy', mealType='Dinner'))
                    self.assertEqual(response.status, 201)
                    recipes.append(response.json())
                response = context.request.post(self.base + '/api/meals', headers=headers,
                    form=dict(recipeId=recipes[0]['id'], date='2026-12-31', mealType='Lunch'))
                self.assertEqual(response.status, 201)
                page.goto(self.base + '/meal-plans')
                page.locator('.meal-plan-card').filter(has=page.get_by_role('heading', name='High Protein', exact=True)).click()
                dialog = page.get_by_role('dialog')
                expect(dialog.get_by_text('2 meals selected', exact=True)).to_be_visible()
                dialog.get_by_label('Start date').fill('2026-12-31')
                dialog.get_by_label('Meal type').select_option('Dinner')
                page.route('**/api/meals/plan', lambda route: route.fulfill(status=503, json={'error': 'Try again later'}))
                dialog.get_by_role('button', name='Add to Calendar', exact=True).click()
                expect(dialog.get_by_role('alert')).to_contain_text('Try again later')
                expect(dialog.get_by_label('Start date')).to_have_value('2026-12-31')
                self.assertEqual(len(context.request.get(self.base + '/api/meals').json()), 1)
                page.unroute('**/api/meals/plan')
                dialog.get_by_role('button', name='Add to Calendar', exact=True).click()
                expect(dialog.get_by_role('status')).to_contain_text('Added 2 meals starting 2026-12-31')
                dialog.get_by_role('link', name='View plan on calendar').click()
                expect(page).to_have_url(self.base + '/calendar?date=2026-12-31')
                expect(page.get_by_text('Protein bowl', exact=True).first).to_be_visible()
                page.reload()
                self.assertEqual(len(context.request.get(self.base + '/api/meals').json()), 3)
                page.goto(self.base + '/meal-plans')
                page.locator('.meal-plan-card').filter(has=page.get_by_role('heading', name='Keto', exact=True)).click()
                dialog = page.get_by_role('dialog')
                expect(dialog.get_by_text('Save a recipe in the Keto category', exact=False)).to_be_visible()
                expect(dialog.get_by_role('button', name='Add to Calendar', exact=True)).to_have_count(0)
                page.set_viewport_size({'width': 375, 'height': 667})
                self.assertTrue(dialog.evaluate('(el) => el.scrollWidth <= el.clientWidth'))
                context.close()
            finally:
                browser.close()
