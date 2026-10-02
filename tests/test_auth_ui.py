"""Real browser integration, isolated servers and data.
Requires Python playwright and an installed Edge browser (or PLAYWRIGHT_CHANNEL).
Compile backend first, then run: python -m unittest discover -s tests -p test_auth_ui.py
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


class AuthUiTest(unittest.TestCase):
    def test_accounts_and_private_recipes(self):
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
                        page.goto(url + '/recipes')
                        expect(page).to_have_url(url + '/login')
                        page.get_by_role('button', name='Create an account', exact=True).click()
                        page.get_by_label('Email address').fill('alice@example.com')
                        page.get_by_label('Password', exact=True).fill(PASSWORD)
                        page.get_by_role('button', name='Create account', exact=True).click()
                        expect(page).to_have_url(url + '/calendar')
                        page.locator('.sidebar-nav button').filter(has_text='Recipes').click()
                        expect(page.get_by_role('heading', name='No recipes found.')).to_be_visible()
                        page.get_by_role('button', name='+ Add Recipe', exact=True).first.click()
                        page.get_by_label('Recipe name').fill('Alice private dinner')
                        page.get_by_label('Ingredients', exact=True).fill('Rice\nBeans')
                        page.get_by_label('Instructions', exact=True).fill('Cook rice.\nAdd beans.')
                        page.get_by_role('button', name='Save recipe', exact=True).click()
                        expect(page.get_by_role('heading', name='Alice private dinner')).to_be_visible()
                        page.reload()
                        expect(page.get_by_role('heading', name='Alice private dinner')).to_be_visible()
                        # Restore browser state in another context: no password is needed while session is valid.
                        restored = browser.new_context(storage_state=context.storage_state())
                        other = restored.new_page()
                        other.goto(url + '/recipes')
                        expect(other.get_by_role('heading', name='Alice private dinner')).to_be_visible()
                        restored.close()
                        tab = context.new_page()
                        tab.goto(url + '/recipes')
                        expect(tab.get_by_role('heading', name='Alice private dinner')).to_be_visible()
                        page.get_by_role('button', name='Log out', exact=True).click()
                        expect(page).to_have_url(url + '/login')
                        expect(tab).to_have_url(url + '/login')
                        page.get_by_role('button', name='Create an account', exact=True).click()
                        page.get_by_label('Email address').fill('bob@example.com')
                        page.get_by_label('Password', exact=True).fill(PASSWORD)
                        page.get_by_role('button', name='Create account', exact=True).click()
                        expect(page).to_have_url(url + '/calendar')
                        page.goto(url + '/recipes')
                        expect(page.get_by_role('heading', name='No recipes found.')).to_be_visible()
                        expect(page.get_by_role('heading', name='Alice private dinner')).to_have_count(0)
                        page.get_by_role('button', name='Log out', exact=True).click()
                        expect(page).to_have_url(url + '/login')
                        page.get_by_label('Email address').fill('alice@example.com')
                        page.get_by_label('Password', exact=True).fill('wrong password')
                        page.get_by_role('button', name='Sign In', exact=True).click()
                        expect(page.get_by_role('alert')).to_contain_text('Invalid email or password')
                        page.get_by_label('Password', exact=True).fill(PASSWORD)
                        page.get_by_role('button', name='Sign In', exact=True).click()
                        expect(page).to_have_url(url + '/calendar')
                        page.goto(url + '/recipes')
                        expect(page.get_by_role('heading', name='Alice private dinner')).to_be_visible()
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
