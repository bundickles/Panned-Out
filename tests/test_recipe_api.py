"""Run from the repository root after compiling backend/src/*.java."""
import json
import http.cookiejar
import shutil
from pathlib import Path
import subprocess
import tempfile
import unittest
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPCookieProcessor


class RecipeApiTest(unittest.TestCase):
    def request(self, method='GET', path='/api/recipes', fields=None):
        body = urlencode(fields).encode() if fields is not None else None
        request = Request(self.url + path, data=body, method=method, headers={"X-Panned-Out-Request": "1"})
        try:
            response = self.client.open(request, timeout=15)
        except HTTPError as error:
            response = error
        with response:
            return response.status, json.load(response)

    def start(self, storage=None, cwd=None, classpath=None):
        self.process = subprocess.Popen(
            ['java', '-cp', str(classpath or Path('backend/build')), 'RecipeServer', '0']
            + ([str(storage)] if storage is not None else []),
            cwd=cwd,
            stdout=subprocess.PIPE, text=True,
        )
        self.addCleanup(self.stop)
        self.url = self.process.stdout.readline().strip().split('Recipe API: ')[1]
        self.client = build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))
        credentials = dict(email='recipe-test@example.com', password='long enough test password')
        status, account = self.request('POST', '/api/auth/register', credentials)
        if status == 409:
            status, account = self.request('POST', '/api/auth/login', credentials)
        self.assertIn(status, (200, 201))
        legacy = Path(storage) if storage is not None else Path(classpath).parent / 'data' / 'recipes.properties'
        self.private_storage = Path(str(legacy) + '.accounts') / 'users' / account['id'] / 'recipes.properties'

    def stop(self):
        if self.process.poll() is None:
            self.process.terminate()
        self.process.wait(timeout=5)
        self.process.stdout.close()

    def test_default_storage_survives_working_directory_change(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            build = root / 'backend' / 'build'
            build.mkdir(parents=True)
            for compiled in Path('backend/build').glob('*.class'):
                shutil.copy2(compiled, build)
            first = root / 'first'
            second = root / 'second'
            first.mkdir()
            second.mkdir()
            self.start(cwd=first, classpath=build)
            try:
                fields = dict(name='Saved across folders', ingredients='Rice',
                              instructions='Cook', category='My Recipes',
                              difficulty='Easy', mealType='Dinner')
                status, saved = self.request('POST', fields=fields)
                self.assertEqual(status, 201)
                self.stop()
                self.start(cwd=second, classpath=build)
                self.assertEqual(self.request(), (200, [saved]))
                self.assertTrue(self.private_storage.is_file())
                self.assertFalse((root / 'backend/data/recipes.properties').exists())
                self.assertFalse((first / 'backend').exists())
                self.assertFalse((second / 'backend').exists())
            finally:
                self.stop()

    def test_recipe_lifecycle(self):
        with tempfile.TemporaryDirectory() as directory:
            storage = Path(directory) / 'recipes.properties'
            self.start(storage)
            try:
                self.assertEqual(self.request(), (200, []))
                fields = dict(name='Rice "bowl" 日本', ingredients='Rice\nBeans',
                              instructions='Cook.\nServe \\ enjoy.', category='My Recipes',
                              difficulty='Easy', mealType='Dinner', prepTime='15')
                self.assertEqual(self.request('POST', fields={})[0], 400)
                self.assertEqual(self.request('POST', fields={**fields, 'calories': '-1'})[0], 400)
                status, saved = self.request('POST', fields=fields)
                self.assertEqual(status, 201)
                for key in ['name', 'ingredients', 'instructions']:
                    self.assertEqual(saved[key], fields[key])
                self.assertEqual(self.request(), (200, [saved]))
                self.stop()
                self.start(storage)
                self.assertEqual(self.request(), (200, [saved]))
                path = '/api/recipes/' + str(saved['id'])
                self.assertEqual(self.request('PUT', path, {**fields, 'protein': '-1'})[0], 400)
                self.assertEqual(self.request(), (200, [saved]))
                status, updated = self.request('PUT', path, {**fields, 'name': 'Updated bowl', 'protein': '25'})
                self.assertEqual(status, 200)
                self.assertEqual(updated['id'], saved['id'])
                self.assertEqual(updated['name'], 'Updated bowl')
                self.assertEqual(updated['protein'], 25)
                self.stop()
                self.start(storage)
                self.assertEqual(self.request(), (200, [updated]))
                self.assertEqual(self.request('PUT', '/api/recipes/999', fields)[0], 404)
                self.assertEqual(self.request('DELETE', path)[0], 200)
                self.assertEqual(self.request('DELETE', '/api/recipes/' + str(saved['id']))[0], 404)
                self.stop()
                self.start(storage)
                self.assertEqual(self.request(), (200, []))
                self.private_storage.write_text('broken storage')
                self.assertEqual(self.request()[0], 500)
                self.assertEqual(self.request('POST', fields=fields)[0], 500)
                self.assertEqual(self.private_storage.read_text(), 'broken storage')
            finally:
                self.stop()


if __name__ == '__main__':
    unittest.main()
