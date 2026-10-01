"""Run from the repository root after compiling backend/src/*.java."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class RecipeApiTest(unittest.TestCase):
    def request(self, method='GET', path='/api/recipes', fields=None):
        body = urlencode(fields).encode() if fields is not None else None
        request = Request(self.url + path, data=body, method=method)
        try:
            response = urlopen(request, timeout=5)
        except HTTPError as error:
            response = error
        with response:
            return response.status, json.load(response)

    def start(self, storage):
        self.process = subprocess.Popen(
            ['java', '-cp', 'backend/build', 'RecipeServer', '0', str(storage)],
            stdout=subprocess.PIPE, text=True,
        )
        self.url = self.process.stdout.readline().strip().split('Recipe API: ')[1]

    def stop(self):
        self.process.terminate()
        self.process.wait(timeout=5)
        self.process.stdout.close()

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
                self.assertEqual(self.request('DELETE', '/api/recipes/' + str(saved['id']))[0], 200)
                self.assertEqual(self.request('DELETE', '/api/recipes/' + str(saved['id']))[0], 404)
                self.stop()
                self.start(storage)
                self.assertEqual(self.request(), (200, []))
                storage.write_text('broken storage')
                self.assertEqual(self.request()[0], 500)
                self.assertEqual(self.request('POST', fields=fields)[0], 500)
                self.assertEqual(storage.read_text(), 'broken storage')
            finally:
                self.stop()


if __name__ == '__main__':
    unittest.main()
