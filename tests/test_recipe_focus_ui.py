"""SCRUM-166 browser checks against Vite with deterministic API fixtures.
Run: python -m unittest discover -s tests -p test_recipe_focus_ui.py
Starts an isolated Vite server; install frontend dependencies first.
Requires playwright and Edge, or set PLAYWRIGHT_CHANNEL.
"""
import json
import os
from pathlib import Path
import socket
import subprocess
import time
import unittest
from urllib.request import urlopen
from urllib.error import URLError
from playwright.sync_api import sync_playwright, expect


class RecipeFocusTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        cls.base = f'http://127.0.0.1:{port}'
        server = subprocess.Popen(
            ['node', 'node_modules/vite/bin/vite.js', '--host', '127.0.0.1',
             '--port', str(port), '--strictPort'], cwd=root / 'frontend',
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        def stop_server():
            server.terminate()
            server.wait(timeout=10)
        cls.addClassCleanup(stop_server)
        for _ in range(100):
            if server.poll() is not None:
                raise RuntimeError('Vite exited before becoming ready')
            try:
                with urlopen(cls.base, timeout=1):
                    return
            except (URLError, OSError):
                time.sleep(0.1)
        raise RuntimeError('Vite did not become ready')

    def test_focus_and_timer(self):
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel=os.environ.get('PLAYWRIGHT_CHANNEL', 'msedge'))
            try:
                page = browser.new_page()
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.route('**/api/auth/me', lambda route: route.fulfill(json={'id': 1, 'email': 'cook@example.com'}))
                recipes = [{'id': 1, 'name': 'Test soup', 'instructions': 'Chop vegetables.\n\nSimmer soup.', 'ingredients': 'Carrots'},
                           {'id': 2, 'name': 'Empty recipe', 'instructions': ''}]
                page.route('**/api/recipes', lambda route: route.fulfill(body=json.dumps(recipes), content_type='application/json'))
                base = self.base
                page.goto(base + '/recipes/1')
                page.clock.install()
                opener = page.get_by_role('button', name='Open cooking focus view')
                expect(page.get_by_text('Chop vegetables.', exact=True)).to_have_count(1)
                opener.click()
                dialog = page.get_by_role('dialog')
                expect(dialog).to_be_visible()
                expect(dialog.get_by_text('Step 1 of 2', exact=True)).to_be_visible()
                expect(dialog.get_by_role('button', name='Previous step')).to_be_disabled()
                dialog.get_by_role('button', name='Next step').click()
                expect(dialog.get_by_text('Simmer soup.', exact=True)).to_be_visible()
                expect(dialog.get_by_role('button', name='Next step')).to_be_disabled()
                dialog.get_by_role('button', name='Previous step').click()
                duration = dialog.get_by_label('Duration (minutes)')
                duration.fill('0')
                dialog.get_by_role('button', name='Start timer').click()
                expect(dialog.get_by_role('alert')).to_be_visible()
                duration.fill('1')
                dialog.get_by_role('button', name='Start timer').click()
                page.clock.fast_forward(10000)
                expect(dialog.get_by_role('timer')).to_have_text('00:50')
                dialog.get_by_role('button', name='Pause timer').click()
                page.clock.fast_forward(10000)
                expect(dialog.get_by_role('timer')).to_have_text('00:50')
                dialog.get_by_role('button', name='Resume timer').click()
                page.keyboard.press('Escape')
                expect(dialog).not_to_be_visible()
                expect(page.get_by_text('Chop vegetables.', exact=True)).to_have_count(1)
                expect(page.locator('.cooking-instruction')).to_have_count(0)
                expect(opener).to_be_focused()
                page.clock.fast_forward(50000)
                expect(page.get_by_text('Time’s up! Check your food.', exact=True).first).to_be_visible()
                opener.click()
                expect(dialog.get_by_role('timer')).to_have_text('00:00')
                dialog.get_by_role('button', name='Reset timer').click()
                expect(dialog.get_by_text('Set a cooking timer')).to_be_visible()
                duration.fill('0.05')
                dialog.get_by_role('button', name='Start timer').click()
                page.clock.fast_forward(3000)
                expect(dialog.get_by_text('Time’s up! Check your food.')).to_be_visible()
                page.set_viewport_size({'width': 375, 'height': 667})
                self.assertTrue(dialog.evaluate('(el) => el.scrollWidth <= el.clientWidth'))
                page.screenshot(path='/private/tmp/panned-focus-mobile.png')
                dialog.get_by_role('button', name='Close focus view').click()
                page.goto(base + '/recipes/1')
                opener.click()
                expect(page.get_by_role('timer')).to_have_text('00:00')
                page.goto(base + '/recipes/2')
                expect(page.get_by_text('No instructions have been added yet.')).to_be_visible()
                expect(opener).to_have_count(0)
                self.assertEqual(errors, [])
            finally:
                browser.close()
