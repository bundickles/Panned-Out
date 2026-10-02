"""Authentication and account isolation through the real Java HTTP server.
Run after javac: python -m unittest discover -s tests -p test_auth_api.py
"""
import http.cookiejar
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener

PASSWORD = 'a sufficiently long test password'
RECIPE = dict(name='Private rice bowl', ingredients='Rice\nBeans', instructions='Cook.\nServe.',
              category='My Recipes', difficulty='Easy', mealType='Dinner')


class AuthApiTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.storage = Path(self.directory.name) / 'recipes.properties'
        self.start()

    def start(self):
        self.process = subprocess.Popen(
            ['java', '-cp', 'backend/build', 'RecipeServer', '0', str(self.storage)],
            stdout=subprocess.PIPE, text=True)
        line = self.process.stdout.readline().strip()
        self.assertTrue(line.startswith('Recipe API: '), line)
        self.url = line.split('Recipe API: ')[1]

    def stop(self):
        self.process.terminate()
        self.process.wait(timeout=5)
        self.process.stdout.close()

    def tearDown(self):
        self.stop()
        self.directory.cleanup()

    def client(self):
        return build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def request(self, client, path, method='GET', fields=None, verified=True, headers=None):
        request_headers = {'X-Panned-Out-Request': '1'} if verified else {}
        request_headers.update(headers or {})
        request = Request(self.url + path, data=urlencode(fields).encode() if fields is not None else None,
                          method=method, headers=request_headers)
        try:
            response = client.open(request, timeout=15)
        except HTTPError as error:
            response = error
        with response:
            return response.status, json.load(response), response.headers

    def register(self, client, email):
        status, account, headers = self.request(client, '/api/auth/register', 'POST',
                                                dict(email=email, password=PASSWORD))
        self.assertEqual(status, 201, account)
        return account, headers

    def test_registration_login_logout_and_private_recipes(self):
        alice, bob, anonymous = self.client(), self.client(), self.client()
        self.assertEqual(self.request(anonymous, '/api/recipes')[0], 401)
        self.assertEqual(self.request(anonymous, '/api/recipes', 'POST', RECIPE)[0], 401)
        self.assertEqual(self.request(anonymous, '/api/recipes/1', 'DELETE')[0], 401)
        account, headers = self.register(alice, 'Alice@Example.com')
        self.assertEqual(account['email'], 'alice@example.com')
        cookie = headers['Set-Cookie']
        for attribute in ['HttpOnly', 'SameSite=Strict', 'Path=/api', 'Max-Age=28800']:
            self.assertIn(attribute, cookie)
        self.assertEqual(self.request(alice, '/api/auth/me')[1], account)
        self.register(bob, 'bob@example.com')
        status, saved, _ = self.request(alice, '/api/recipes', 'POST', {**RECIPE, 'ownerId': 'bob', 'userId': 'bob'})
        self.assertEqual(status, 201)
        for field in ['name', 'ingredients', 'instructions', 'mealType']:
            self.assertEqual(saved[field], RECIPE[field])
        self.assertEqual(self.request(bob, '/api/recipes')[1], [])
        self.assertEqual(self.request(bob, '/api/recipes/' + str(saved['id']), 'DELETE')[0], 404)
        self.assertEqual(self.request(bob, '/api/recipes/' + str(saved['id']))[0], 404)
        self.assertEqual(self.request(bob, '/api/recipes/' + str(saved['id']), 'PUT', RECIPE)[0], 404)
        self.assertEqual(self.request(alice, '/api/recipes')[1], [saved])
        self.assertEqual(self.request(alice, '/api/auth/logout', 'POST', {})[0], 200)
        self.assertEqual(self.request(alice, '/api/recipes')[0], 401)
        # A copied old session cookie is invalid after logout.
        self.assertEqual(self.request(anonymous, '/api/recipes', headers={'Cookie': cookie.split(';')[0]})[0], 401)
        status, _, headers = self.request(alice, '/api/auth/login', 'POST',
                                          dict(email='alice@example.com', password=PASSWORD))
        self.assertEqual(status, 200)
        self.assertNotEqual(headers['Set-Cookie'], cookie)
        self.assertEqual(self.request(alice, '/api/recipes')[1], [saved])
        # Per-account IDs may coincide; operations still target only the caller's storage.
        bob_recipe = self.request(bob, '/api/recipes', 'POST', {**RECIPE, 'name': 'Bob only'})[1]
        self.assertEqual(self.request(bob, '/api/recipes/' + str(bob_recipe['id']), 'DELETE')[0], 200)
        self.assertEqual(self.request(alice, '/api/recipes')[1], [saved])
        self.stop()
        self.start()
        self.assertEqual(self.request(alice, '/api/recipes')[0], 401)
        self.assertEqual(self.request(alice, '/api/auth/login', 'POST',
                                     dict(email='alice@example.com', password=PASSWORD))[0], 200)
        self.assertEqual(self.request(alice, '/api/recipes')[1], [saved])

    def test_credentials_and_hash_storage(self):
        client = self.client()
        self.assertEqual(self.request(client, '/api/auth/register', 'POST', dict(email='bad', password=PASSWORD))[0], 400)
        self.assertEqual(self.request(client, '/api/auth/register', 'POST', dict(email='a@example.com', password='short'))[0], 400)
        self.register(client, 'a@example.com')
        self.assertEqual(self.request(client, '/api/auth/register', 'POST', dict(email=' A@EXAMPLE.COM ', password=PASSWORD))[0], 409)
        other = self.client()
        wrong = self.request(other, '/api/auth/login', 'POST', dict(email='a@example.com', password='wrong'))
        missing = self.request(other, '/api/auth/login', 'POST', dict(email='missing@example.com', password='wrong'))
        self.assertEqual(wrong[:2], missing[:2])
        self.assertEqual(wrong[0], 401)
        self.assertEqual(self.request(other, '/api/auth/me')[0], 401)
        self.register(other, 'b@example.com')
        stored = Path(str(self.storage) + '.accounts', 'accounts.properties').read_text()
        self.assertNotIn(PASSWORD, stored)
        self.assertIn('600000', stored)
        values = [line.split('=', 1)[1] for line in stored.splitlines() if '@example.com=' in line]
        self.assertEqual(len(values), 2)
        self.assertNotEqual(values[0].split(':')[-1], values[1].split(':')[-1])

    def test_csrf_and_session_tampering(self):
        client = self.client()
        self.assertEqual(self.request(client, '/api/auth/register', 'POST', dict(email='a@example.com', password=PASSWORD), verified=False)[0], 403)
        self.register(client, 'a@example.com')
        self.assertEqual(self.request(client, '/api/recipes', 'POST', RECIPE, verified=False)[0], 403)
        self.assertEqual(self.request(client, '/api/auth/logout', 'POST', {}, verified=False)[0], 403)
        self.assertEqual(self.request(client, '/api/recipes', 'POST', RECIPE, headers={'Sec-Fetch-Site': 'cross-site'})[0], 403)
        self.assertEqual(self.request(self.client(), '/api/recipes', headers={'Cookie': 'panned_session=forged'})[0], 401)
        self.assertEqual(self.request(client, '/api/recipes')[1], [])

    def test_legacy_data_not_assigned_and_storage_failure(self):
        self.storage.write_text('legacy shared recipes must remain untouched')
        client = self.client()
        self.register(client, 'a@example.com')
        self.assertEqual(self.request(client, '/api/recipes')[1], [])
        self.assertEqual(self.storage.read_text(), 'legacy shared recipes must remain untouched')
        account_file = Path(str(self.storage) + '.accounts', 'accounts.properties')
        account_file.write_text('broken account storage')
        self.assertEqual(self.request(self.client(), '/api/auth/login', 'POST', dict(email='a@example.com', password=PASSWORD))[0], 500)
        self.assertEqual(self.request(self.client(), '/api/auth/register', 'POST', dict(email='b@example.com', password=PASSWORD))[0], 500)
        self.assertEqual(account_file.read_text(), 'broken account storage')

    def test_login_attempts_limited(self):
        client = self.client()
        for _ in range(20):
            self.assertEqual(self.request(client, '/api/auth/login', 'POST', dict(email='bad', password=''))[0], 400)
        status, _, headers = self.request(client, '/api/auth/login', 'POST', dict(email='bad', password=''))
        self.assertEqual(status, 429)
        self.assertGreater(int(headers['Retry-After']), 0)


if __name__ == '__main__':
    unittest.main()
