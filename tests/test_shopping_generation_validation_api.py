"""SCRUM-120: generation validation, method errors, isolation and storage recovery."""
from pathlib import Path
import unittest
import test_auth_api as auth


class GenerationValidationTest(unittest.TestCase):
    setUp = auth.AuthApiTest.setUp
    tearDown = auth.AuthApiTest.tearDown
    start = auth.AuthApiTest.start
    stop = auth.AuthApiTest.stop
    client = auth.AuthApiTest.client
    request = auth.AuthApiTest.request
    register = auth.AuthApiTest.register
    path = '/api/shopping-list?start=2026-10-01&end=2026-10-07'

    def signed_in(self, email='validation@example.com'):
        client = self.client()
        account, _ = self.register(client, email)
        return client, account

    def recipe(self, client, name='Rice bowl', ingredients='Rice\nBeans'):
        status, result, _ = self.request(client, '/api/recipes', 'POST',
                                         {**auth.RECIPE, 'name': name, 'ingredients': ingredients})
        self.assertEqual(status, 201)
        return result

    def schedule(self, client, recipe):
        status, result, _ = self.request(client, '/api/meals', 'POST',
                                         dict(recipeId=recipe['id'], date='2026-10-04', mealType='Dinner'))
        self.assertEqual(status, 201)
        return result

    @staticmethod
    def source(meal):
        return dict(mealId=meal['id'], recipeId=meal['recipeId'], date=meal['date'], recipeName=meal['name'])

    def test_missing_malformed_reversed_and_repeated_dates(self):
        client, _ = self.signed_in()
        queries = ['', '?start=2026-10-01', '?end=2026-10-07', '?start=&end=2026-10-07',
                   '?start=10-01-2026&end=2026-10-07', '?start=2026-02-30&end=2026-10-07',
                   '?start=0000-01-01&end=2026-10-07', '?start=2026-10-01&end=2026-13-01',
                   '?start=2026-10-08&end=2026-10-07', '?start=2026-10-01T00:00:00&end=2026-10-07',
                   '?start=2026-10-01&start=2026-10-02&end=2026-10-07',
                   '?start=2026-10-01&end=2026-10-07&end=2026-10-08',
                   '?start=2026-10-01&end=2026-10-07&broken', '?start=%25ZZ&end=2026-10-07']
        for query in queries:
            with self.subTest(query=query):
                status, result, _ = self.request(client, '/api/shopping-list' + query)
                self.assertEqual(status, 400)
                self.assertIsInstance(result['error'], str)
        for start, end in [('2026-10-04', '2026-10-04'), ('2028-02-29', '2028-02-29')]:
            self.assertEqual(self.request(client, f'/api/shopping-list?start={start}&end={end}')[0], 200)

    def test_auth_and_wrong_methods(self):
        self.assertEqual(self.request(self.client(), self.path)[0], 401)
        client, _ = self.signed_in()
        for method in ['POST', 'PUT', 'DELETE']:
            with self.subTest(method=method):
                status, result, headers = self.request(client, self.path, method, {})
                self.assertEqual(status, 405)
                self.assertEqual(headers['Allow'], 'GET')
                self.assertIsInstance(result['error'], str)
        self.request(client, '/api/auth/logout', 'POST', {})
        self.assertEqual(self.request(client, self.path)[0], 401)

    def test_overlapping_recipe_ids_and_ignored_owner_override(self):
        alice, _ = self.signed_in('alice@example.com')
        bob, _ = self.signed_in('bob@example.com')
        a = self.recipe(alice, 'Alice meal', 'Alice private ingredient')
        b = self.recipe(bob, 'Bob meal', 'Bob private ingredient')
        self.assertEqual(a['id'], b['id'])
        alice_meal = self.schedule(alice, a)
        bob_meal = self.schedule(bob, b)
        for client, meal, ingredient in [(alice, alice_meal, 'Alice private ingredient'), (bob, bob_meal, 'Bob private ingredient')]:
            result = self.request(client, self.path)[1]
            self.assertEqual(result['items'], [dict(name=ingredient, occurrences=1, sources=[self.source(meal)])])
            self.assertEqual(self.request(client, self.path + '&ownerId=alice&userId=bob')[1], result)

    def test_deleted_recipe_warning_keeps_available_ingredients(self):
        client, _ = self.signed_in()
        deleted = self.recipe(client, 'Deleted meal', 'Deleted ingredient')
        available = self.recipe(client, 'Available meal', 'Beans')
        missing_meal = self.schedule(client, deleted)
        self.schedule(client, available)
        self.request(client, '/api/recipes/' + str(deleted['id']), 'DELETE')
        status, result, _ = self.request(client, self.path)
        self.assertEqual(status, 200)
        self.assertEqual([item['name'] for item in result['items']], ['Beans'])
        self.assertEqual(result['warnings'], [dict(message='Recipe unavailable; its ingredients were omitted.', source=self.source(missing_meal))])

    def test_legacy_recipe_without_ingredients_warns_instead_of_crashing(self):
        client, account = self.signed_in()
        recipe = self.recipe(client)
        meal = self.schedule(client, recipe)
        storage = Path(str(self.storage) + '.accounts', 'users', account['id'], 'recipes.properties')
        original = storage.read_text()
        # Older model constructors legitimately persisted recipes without this field.
        storage.write_text('\n'.join(line for line in original.splitlines()
                                     if not line.startswith('recipe.0.ingredients=')) + '\n')
        status, result, _ = self.request(client, self.path)
        self.assertEqual(status, 200)
        self.assertEqual(result['items'], [])
        self.assertEqual(result['warnings'], [dict(message='Recipe has no ingredients; its ingredients were omitted.', source=self.source(meal))])

    def test_corrupt_storage_returns_json_without_overwriting_and_recovers(self):
        client, account = self.signed_in()
        recipe = self.recipe(client)
        self.schedule(client, recipe)
        user_path = Path(str(self.storage) + '.accounts', 'users', account['id'])
        for name in ['meals.properties', 'recipes.properties']:
            with self.subTest(storage=name):
                storage = user_path / name
                original = storage.read_bytes()
                try:
                    storage.write_text('broken storage')
                    status, result, _ = self.request(client, self.path)
                    self.assertEqual(status, 500)
                    self.assertIsInstance(result['error'], str)
                    self.assertEqual(storage.read_text(), 'broken storage')
                finally:
                    storage.write_bytes(original)
                self.assertEqual(self.request(client, self.path)[0], 200)


if __name__ == '__main__':
    unittest.main()
