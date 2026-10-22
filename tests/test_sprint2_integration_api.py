"""Exercise PRs 12, 13, 16, and 20 together through their actual HTTP routes."""
import unittest
import test_auth_api as auth


class Sprint2IntegrationApiTest(unittest.TestCase):
    setUp = auth.AuthApiTest.setUp
    tearDown = auth.AuthApiTest.tearDown
    start = auth.AuthApiTest.start
    stop = auth.AuthApiTest.stop
    client = auth.AuthApiTest.client
    request = auth.AuthApiTest.request
    register = auth.AuthApiTest.register

    def test_suggestion_to_calendar_to_generated_and_saved_list(self):
        alice, bob = self.client(), self.client()
        self.register(alice, 'alice@example.com')
        self.register(bob, 'bob@example.com')
        status, catalog, _ = self.request(alice, '/api/recipes?filter=suggested')
        self.assertEqual(status, 200)
        self.assertEqual(len(catalog), 24)
        suggestion = catalog[0]
        fields = {key: suggestion[key] for key in
                  ('name', 'ingredients', 'instructions', 'difficulty', 'prepTime')}
        fields.update(category='My Recipes', mealType='Dinner')
        status, recipe, _ = self.request(alice, '/api/recipes', 'POST', fields)
        self.assertEqual(status, 201)
        status, meal, _ = self.request(alice, '/api/meals', 'POST',
                                      dict(recipeId=recipe['id'], date='2026-10-22', mealType='Dinner'))
        self.assertEqual(status, 201)
        path = '/api/shopping-list?start=2026-10-22&end=2026-10-22'
        status, generated, _ = self.request(alice, path)
        self.assertEqual(status, 200)
        self.assertEqual(generated['warnings'], [])
        self.assertEqual([item['name'] for item in generated['items']], suggestion['ingredients'].splitlines())
        snapshot = dict(start=generated['start'], end=generated['end'],
                        itemCount=len(generated['items']), warningCount=0)
        for i, item in enumerate(generated['items']):
            snapshot.update({f'item.{i}.text': item['name'], f'item.{i}.occurrences': item['occurrences'],
                             f'item.{i}.sourceCount': len(item['sources'])})
            for j, source in enumerate(item['sources']):
                self.assertEqual(source['mealId'], meal['id'])
                snapshot.update({f'item.{i}.source.{j}.mealId': source['mealId'],
                                 f'item.{i}.source.{j}.recipeId': source['recipeId']})
        status, saved, _ = self.request(alice, '/api/shopping-lists', 'POST', snapshot)
        self.assertEqual(status, 201)
        list_path = '/api/shopping-lists/' + saved['id']
        status, updated, _ = self.request(alice, list_path + '/items/' + saved['items'][0]['id'] + '/purchased',
                                         'PATCH', dict(purchased='true'))
        self.assertEqual(status, 200)
        self.assertTrue(updated['items'][0]['purchased'])
        self.assertEqual(self.request(alice, list_path)[1], updated)
        self.assertEqual(self.request(bob, list_path)[0], 404)
        self.assertEqual(self.request(bob, '/api/meals')[1], [])
        self.assertEqual(self.request(bob, path)[1]['items'], [])
        self.assertEqual(self.request(bob, '/api/shopping-lists')[1], [])
        self.assertEqual(self.request(bob, '/api/recipes?filter=suggested')[1], catalog)
