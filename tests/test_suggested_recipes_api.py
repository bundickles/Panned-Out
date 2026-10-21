"""SCRUM-137/136: fixture catalog, filtered retrieval, and account isolation."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import test_auth_api as auth


# Deliberately test-only content, not shipped as suggested recipes.
CATALOG = """version=1
count=2
recipe.0.id=1
recipe.0.name=Fixture bowl 日本
recipe.0.ingredients=Rice\\nBeans
recipe.0.instructions=Cook.\\nServe \\"warm\\".
recipe.0.plan=High Protein
recipe.0.difficulty=Easy
recipe.0.prepTime=15
recipe.1.id=2
recipe.1.name=Fixture salad
recipe.1.ingredients=Leaves
recipe.1.instructions=Mix.
recipe.1.plan=Keto
recipe.1.difficulty=Medium
recipe.1.prepTime=5
"""


class SuggestedRecipesApiTest(unittest.TestCase):
    client = auth.AuthApiTest.client
    request = auth.AuthApiTest.request
    register = auth.AuthApiTest.register
    start = auth.AuthApiTest.start
    stop = auth.AuthApiTest.stop

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.storage = Path(directory.name) / 'recipes.properties'
        self.catalog = Path(directory.name) / 'catalog.properties'
        self.catalog.write_text(CATALOG, encoding='utf-8')
        environment = patch.dict(os.environ, PANNED_OUT_SUGGESTED_RECIPES=str(self.catalog))
        environment.start()
        self.addCleanup(environment.stop)
        self.start()
        self.addCleanup(self.stop)

    def test_filters_isolation_and_read_only_catalog(self):
        alice, bob, anonymous = self.client(), self.client(), self.client()
        for value in ('suggested', 'saved', 'all'):
            self.assertEqual(self.request(anonymous, '/api/recipes?filter=' + value)[0], 401)
        self.register(alice, 'alice@example.com')
        self.register(bob, 'bob@example.com')
        self.assertEqual(self.request(alice, '/api/recipes')[1], [])
        self.assertEqual(self.request(alice, '/api/recipes?filter=saved')[1], [])
        status, suggestions, _ = self.request(alice, '/api/recipes?filter=suggested')
        self.assertEqual(status, 200)
        self.assertEqual(len(suggestions), 2)
        self.assertEqual(suggestions[0], dict(id='suggested:1', source='suggested',
                         name='Fixture bowl 日本', ingredients='Rice\nBeans',
                         instructions='Cook.\nServe "warm".', difficulty='Easy', prepTime=15,
                         plan='High Protein', category='High Protein'))
        self.assertEqual(self.request(bob, '/api/recipes?filter=suggested')[1], suggestions)
        self.assertEqual(self.request(alice, '/api/recipes?filter=all')[1], suggestions)
        for client, name in ((alice, 'Alice only'), (bob, 'Bob only')):
            status, saved, _ = self.request(client, '/api/recipes', 'POST', {**auth.RECIPE, 'name': name})
            self.assertEqual(status, 201)
            self.assertEqual(saved['id'], 1)  # Private IDs overlap but cannot leak.
            self.assertEqual(saved['source'], 'saved')
            self.assertEqual(self.request(client, '/api/recipes')[1], [saved])
            self.assertEqual(self.request(client, '/api/recipes?filter=saved')[1], [saved])
            self.assertEqual(self.request(client, '/api/recipes?filter=all')[1], [saved] + suggestions)
            for method in ('PUT', 'DELETE'):
                self.assertEqual(self.request(client, '/api/recipes/suggested:1', method,
                                 auth.RECIPE if method == 'PUT' else None)[0], 404)
            self.assertEqual(self.request(client, '/api/recipes')[1], [saved])
        self.assertEqual(self.request(alice, '/api/recipes/1', 'DELETE')[0], 200)
        self.assertEqual(self.request(alice, '/api/recipes?filter=all')[1], suggestions)
        self.assertEqual(self.request(bob, '/api/recipes?filter=all')[1][0]['name'], 'Bob only')
        self.assertEqual(self.catalog.read_text(encoding='utf-8'), CATALOG)

    def test_filter_validation(self):
        alice = self.client()
        self.register(alice, 'alice@example.com')
        for query in ('filter=', 'filter', 'filter=unknown', 'filter=Suggested',
                      'filter=saved&filter=all', 'filter=%25broken'):
            self.assertEqual(self.request(alice, '/api/recipes?' + query)[0], 400, query)
        self.assertEqual(self.request(alice, '/api/recipes?filter=%73uggested')[0], 200)

    def test_restart_preserves_catalog_without_copying_to_account(self):
        alice = self.client()
        self.register(alice, 'alice@example.com')
        before = self.request(alice, '/api/recipes?filter=suggested')[1]
        self.stop()
        self.start()
        self.assertEqual(self.request(alice, '/api/recipes?filter=suggested')[0], 401)
        self.assertEqual(self.request(alice, '/api/auth/login', 'POST',
                         dict(email='alice@example.com', password=auth.PASSWORD))[0], 200)
        self.assertEqual(self.request(alice, '/api/recipes?filter=suggested')[1], before)
        self.assertEqual(self.request(alice, '/api/recipes')[1], [])
        self.assertFalse(any(Path(str(self.storage) + '.accounts').glob('users/*/recipes.properties')))

    def test_invalid_catalog_prevents_startup(self):
        self.stop()
        for content in (CATALOG.replace('recipe.1.id=2', 'recipe.1.id=1'),
                        CATALOG.replace('recipe.0.plan=High Protein', 'recipe.0.plan=Unknown'),
                        CATALOG.replace('recipe.0.name=Fixture bowl 日本', 'recipe.0.name='),
                        CATALOG.replace('recipe.0.prepTime=15', 'recipe.0.prepTime=-1'),
                        CATALOG.replace('version=1', 'version=2')):
            self.catalog.write_text(content, encoding='utf-8')
            result = subprocess.run(['java', '-cp', 'backend/build', 'RecipeServer', '0', str(self.storage)],
                                    capture_output=True, text=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn('Recipe API:', result.stdout)

    def test_empty_catalog(self):
        self.stop()
        self.catalog.write_text('version=1\ncount=0\n', encoding='utf-8')
        self.start()
        alice = self.client()
        self.register(alice, 'alice@example.com')
        self.assertEqual(self.request(alice, '/api/recipes?filter=suggested')[1], [])
        self.assertEqual(self.request(alice, '/api/recipes?filter=all')[1], [])
