"""Chatbot UI regression; starts an isolated Vite server automatically.
Install frontend dependencies and Python Playwright, then run with unittest.
"""
import json
import os
import unittest
from pathlib import Path
import socket
import subprocess
import time
from urllib.request import urlopen
from urllib.error import URLError
from urllib.parse import parse_qs
from playwright.sync_api import sync_playwright, expect

class ChatUiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        cls.base = f'http://127.0.0.1:{port}'
        server = subprocess.Popen(['node', 'node_modules/vite/bin/vite.js', '--host', '127.0.0.1',
                                   '--port', str(port), '--strictPort'],
                                  cwd=Path(__file__).resolve().parents[1] / 'frontend',
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        def cleanup():
            server.terminate(); server.wait(timeout=10)
        cls.addClassCleanup(cleanup)
        for _ in range(100):
            if server.poll() is not None: raise RuntimeError('Vite exited before becoming ready')
            try:
                with urlopen(cls.base, timeout=1): return
            except (URLError, OSError): time.sleep(0.1)
        raise RuntimeError('Vite did not become ready')

    def test_chat(self):
        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel=os.environ.get('PLAYWRIGHT_CHANNEL', 'msedge'))
            try:
                page = browser.new_page()
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.route('**/api/auth/me', lambda route: route.fulfill(json={'id': 'alice', 'email': 'alice@example.com'}))
                page.route('**/api/recipes', lambda route: route.fulfill(json=[]))
                available = False
                status = 200
                requests = []
                def chat(route):
                    if route.request.method == 'GET':
                        route.fulfill(json={'available': available})
                    else:
                        requests.append(parse_qs(route.request.post_data))
                        route.fulfill(status=status, json={'reply': 'Try rice and beans. <b>Enjoy!</b>'} if status == 200 else {'error': 'Usage limit reached. Try again later.'})
                page.route('**/api/chat', chat)
                page.goto(self.base + '/recipes')
                launcher = page.get_by_role('button', name='✳ Kitchen assistant', exact=True)
                launcher.click()
                expect(page.get_by_text('Messages and recent chat history are sent to GroqCloud.', exact=False)).to_be_visible()
                expect(page.get_by_text('Google Gemini', exact=False)).to_have_count(0)
                expect(page.get_by_text('The AI assistant hasn’t been connected yet.', exact=False)).to_be_visible()
                expect(page.get_by_role('button', name='Send', exact=True)).to_be_disabled()
                page.get_by_role('button', name='Close kitchen assistant').click()
                available = True
                launcher.click()
                page.get_by_role('button', name='What can I cook with rice and beans?', exact=True).click()
                page.get_by_role('button', name='Send', exact=True).click()
                expect(page.get_by_text('Try rice and beans. <b>Enjoy!</b>', exact=True)).to_be_visible()
                self.assertEqual(page.locator('.chat-message b').count(), 0)
                self.assertEqual(json.loads(requests[0]['history'][0]), [])
                page.get_by_label('Your message').fill('Can I add carrots?')
                page.get_by_role('button', name='Send', exact=True).click()
                expect(page.locator('.chat-model')).to_have_count(2)
                self.assertEqual(len(json.loads(requests[1]['history'][0])), 2)
                page.keyboard.press('Escape')
                expect(launcher).to_be_focused()
                launcher.click()
                expect(page.locator('.chat-model')).to_have_count(2)
                status = 429
                page.get_by_label('Your message').fill('Try another idea')
                page.get_by_role('button', name='Send', exact=True).click()
                expect(page.get_by_role('alert')).to_contain_text('Usage limit reached')
                expect(page.get_by_label('Your message')).to_have_value('Try another idea')
                expect(page.locator('.chat-user')).to_have_count(2)
                page.get_by_role('button', name='New chat', exact=True).click()
                expect(page.locator('.chat-message')).to_have_count(0)
                expect(page.get_by_label('Your message')).to_have_value('')
                page.set_viewport_size({'width': 375, 'height': 667})
                expect(page.get_by_role('button', name='Send', exact=True)).to_be_in_viewport()
                self.assertTrue(page.locator('.chat-panel').evaluate('(el) => el.scrollWidth <= el.clientWidth'))
                page.screenshot(path='/private/tmp/panned-chat-mobile.png')
                # Resetting cancels a pending reply so it cannot leak into the next conversation.
                pending = []
                page.route('**/api/chat', lambda route: pending.append(route) if route.request.method == 'POST' else route.fulfill(json={'available': True}))
                page.get_by_label('Your message').fill('Pending request')
                page.get_by_role('button', name='Send', exact=True).click()
                expect(page.get_by_text('Thinking…')).to_be_visible()
                page.get_by_role('button', name='New chat', exact=True).click()
                expect(page.locator('.chat-message')).to_have_count(0)
                page.route('**/api/auth/me', lambda route: route.fulfill(json={'id': 'bob', 'email': 'bob@example.com'}))
                page.reload()
                launcher.click()
                expect(page.locator('.chat-message')).to_have_count(0)
                self.assertEqual(errors, [])
            finally:
                browser.close()
