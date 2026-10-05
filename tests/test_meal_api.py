"""Calendar persistence and privacy through the authenticated Java API."""
from pathlib import Path
import unittest
import test_auth_api as auth


class MealApiTest(unittest.TestCase):
    # Reuse the isolated server/client fixture without rerunning its test cases.
    setUp = auth.AuthApiTest.setUp
    tearDown = auth.AuthApiTest.tearDown
    start = auth.AuthApiTest.start
    stop = auth.AuthApiTest.stop
    client = auth.AuthApiTest.client
    request = auth.AuthApiTest.request
    register = auth.AuthApiTest.register

    def test_calendar_persistence_and_account_isolation(self):
        alice, bob, anonymous = self.client(), self.client(), self.client()
        for method, path, fields in [('GET', '/api/meals', None),
                                     ('POST', '/api/meals', {}),
                                     ('DELETE', '/api/meals/00000000-0000-0000-0000-000000000000', None)]:
            self.assertEqual(self.request(anonymous, path, method, fields)[0], 401)
        self.register(alice, 'alice@example.com')
        self.register(bob, 'bob@example.com')
        recipe = self.request(alice, '/api/recipes', 'POST', auth.RECIPE)[1]
        fields = dict(recipeId=recipe['id'], date='2026-10-04', mealType='Dinner')
        self.assertEqual(self.request(alice, '/api/meals', 'POST', fields, verified=False)[0], 403)
        self.assertEqual(self.request(bob, '/api/meals', 'POST', fields)[0], 404)
        status, meal, _ = self.request(alice, '/api/meals', 'POST', fields)
        self.assertEqual(status, 201)
        self.assertEqual(meal['name'], recipe['name'])
        self.assertEqual(meal['date'], fields['date'])
        self.assertEqual(meal['type'], 'Dinner')
        self.assertEqual(self.request(bob, '/api/meals')[1], [])
        self.assertEqual(self.request(bob, '/api/meals/' + meal['id'], 'DELETE')[0], 404)
        # Recipe IDs can overlap between accounts, but meal names come from the caller's recipe.
        bob_recipe = self.request(bob, '/api/recipes', 'POST', {**auth.RECIPE, 'name': 'Bob meal'})[1]
        self.assertEqual(bob_recipe['id'], recipe['id'])
        bob_meal = self.request(bob, '/api/meals', 'POST', {**fields, 'ownerId': 'alice'})[1]
        self.assertEqual(bob_meal['name'], 'Bob meal')
        self.assertEqual(self.request(alice, '/api/meals')[1], [meal])
        # Existing scheduled meals retain their snapshot after the recipe is deleted.
        self.assertEqual(self.request(alice, '/api/recipes/' + str(recipe['id']), 'DELETE')[0], 200)
        self.stop()
        self.start()
        self.assertEqual(self.request(alice, '/api/meals')[0], 401)
        self.assertEqual(self.request(alice, '/api/auth/login', 'POST',
                                     dict(email='alice@example.com', password=auth.PASSWORD))[0], 200)
        self.assertEqual(self.request(alice, '/api/meals')[1], [meal])
        self.assertEqual(self.request(alice, '/api/meals/' + meal['id'], 'DELETE')[0], 200)
        self.assertEqual(self.request(alice, '/api/meals/' + meal['id'], 'DELETE')[0], 404)
        self.stop()
        self.start()
        self.request(alice, '/api/auth/login', 'POST', dict(email='alice@example.com', password=auth.PASSWORD))
        self.assertEqual(self.request(alice, '/api/meals')[1], [])

    def test_validation_and_storage_failure(self):
        client = self.client()
        account, _ = self.register(client, 'alice@example.com')
        recipe = self.request(client, '/api/recipes', 'POST', auth.RECIPE)[1]
        fields = dict(recipeId=recipe['id'], date='2026-10-04', mealType='Lunch')
        for changed in [dict(date='2026-02-30'), dict(date=''), dict(date='0000-01-01'),
                        dict(mealType='Invalid'), dict(recipeId='not-an-id')]:
            self.assertEqual(self.request(client, '/api/meals', 'POST', {**fields, **changed})[0], 400)
        self.assertEqual(self.request(client, '/api/meals')[1], [])
        first = self.request(client, '/api/meals', 'POST', fields)[1]
        second = self.request(client, '/api/meals', 'POST', {**fields, 'date': '2026-10-05'})[1]
        self.assertNotEqual(first['id'], second['id'])
        self.assertEqual(len(self.request(client, '/api/meals')[1]), 2)
        storage = Path(str(self.storage) + '.accounts', 'users', account['id'], 'meals.properties')
        storage.write_text('broken meal storage')
        self.assertEqual(self.request(client, '/api/meals')[0], 500)
        self.assertEqual(self.request(client, '/api/meals', 'POST', fields)[0], 500)
        self.assertEqual(storage.read_text(), 'broken meal storage')


if __name__ == '__main__':
    unittest.main()
