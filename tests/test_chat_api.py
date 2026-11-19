"""Real authentication/validation with GroqCloud intentionally unconfigured."""
import http.cookiejar
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from urllib.request import Request, build_opener, HTTPCookieProcessor
from urllib.error import HTTPError
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
class ChatEndpointTest(unittest.TestCase):
    def test_access_and_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, GROQ_API_KEY='')
            server = subprocess.Popen(['java', '-cp', 'backend/build', 'RecipeServer', '0', str(Path(tmp)/'recipes.properties')], cwd=ROOT, env=env, stdout=subprocess.PIPE, text=True)
            try:
                url = server.stdout.readline().strip().split('Recipe API: ')[1]
                client = build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))
                def call(path, data=None, verified=True):
                    req = Request(url + path, data=None if data is None else urlencode(data).encode(), headers={'X-Panned-Out-Request': '1'} if verified else {})
                    try: response = client.open(req)
                    except HTTPError as e: response = e
                    with response: return response.status, json.load(response)
                self.assertEqual(call('/api/chat')[0], 401)
                self.assertEqual(call('/api/auth/register', {'email':'chat@example.com','password':'a long chat testing password'})[0], 201)
                self.assertEqual(call('/api/chat'), (200, {'available': False}))
                self.assertEqual(call('/api/chat', {'message':'Hi'}, False)[0], 403)
                self.assertEqual(call('/api/chat', {'message':''})[0], 400)
                self.assertEqual(call('/api/chat', {'message':'Hi','history':'not json'})[0], 400)
                self.assertEqual(call('/api/chat', {'message':'x'*70000})[0], 413)
                code, body = call('/api/chat', {'message':'Hi'})
                self.assertEqual(code, 503)
                self.assertIn('not configured', body['error'])
            finally:
                server.terminate(); server.wait(timeout=10); server.stdout.close()
