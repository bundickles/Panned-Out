"""Daily planned nutrition from current private recipe data (SCRUM-182)."""
from pathlib import Path
import unittest
import test_auth_api as auth


NUTRIENTS = ('calories', 'protein', 'carbohydrates', 'fat', 'fiber')
NUTRITION = dict(calories=400, protein=25, carbohydrates=50, fat=12, fiber=8)
BASE = '/api/nutrition/daily'


class DailyNutritionApiTest(unittest.TestCase):
    setUp = auth.AuthApiTest.setUp
    tearDown = auth.AuthApiTest.tearDown
    start = auth.AuthApiTest.start
    stop = auth.AuthApiTest.stop
    client = auth.AuthApiTest.client
    request = auth.AuthApiTest.request
    register = auth.AuthApiTest.register

    def recipe(self, client, **fields):
        status, recipe, _ = self.request(client, '/api/recipes', 'POST', {**auth.RECIPE, **fields})
        self.assertEqual(status, 201)
        return recipe

    def meal(self, client, recipe, date):
        status, meal, _ = self.request(client, '/api/meals', 'POST',
                                      dict(recipeId=recipe['id'], date=date, mealType='Dinner'))
        self.assertEqual(status, 201)
        return meal

    def totals(self, client, start='2026-11-18', end='2026-11-18'):
        status, body, headers = self.request(client, BASE + '?start=' + start + '&end=' + end)
        self.assertEqual(status, 200, body)
        self.assertEqual(headers['Cache-Control'], 'no-store')
        return body

    def test_inclusive_dates_repeated_meals_empty_days_and_account_isolation(self):
        alice, bob = self.client(), self.client()
        self.register(alice, 'alice@example.com')
        self.register(bob, 'bob@example.com')
        recipe = self.recipe(alice, **NUTRITION)
        other = self.recipe(bob, **{n: 999 for n in NUTRIENTS})
        self.assertEqual(recipe['id'], other['id'])
        self.meal(bob, other, '2026-11-18')
        for date in ['2026-11-16', '2026-11-17', '2026-11-17', '2026-11-19', '2026-11-20']:
            self.meal(alice, recipe, date)
        result = self.totals(alice, '2026-11-17', '2026-11-19')
        self.assertEqual([d['date'] for d in result['days']], ['2026-11-17', '2026-11-18', '2026-11-19'])
        self.assertEqual(result['warnings'], [])
        for day, count in zip(result['days'], [2, 0, 1]):
            self.assertEqual(day['mealCount'], count)
            self.assertTrue(day['complete'])
            self.assertEqual(day['missingNutrition'], {n: 0 for n in NUTRIENTS})
            for nutrient, value in NUTRITION.items():
                self.assertEqual(day[nutrient], count * value)
        self.assertEqual(self.totals(bob)['days'][0]['calories'], 999)

    def test_recipe_edits_meal_removal_and_recipe_deletion_update_next_request(self):
        client = self.client()
        self.register(client, 'alice@example.com')
        recipe = self.recipe(client, **NUTRITION)
        meal = self.meal(client, recipe, '2026-11-18')
        self.assertEqual(self.totals(client)['days'][0]['calories'], 400)
        changed = {n: value + 1 for n, value in NUTRITION.items()}
        self.assertEqual(self.request(client, '/api/recipes/' + str(recipe['id']), 'PUT',
                                      {**auth.RECIPE, **changed})[0], 200)
        for nutrient, value in changed.items():
            self.assertEqual(self.totals(client)['days'][0][nutrient], value)
        self.assertEqual(self.request(client, '/api/meals/' + meal['id'], 'DELETE')[0], 200)
        self.assertEqual(self.totals(client)['days'][0]['mealCount'], 0)
        self.meal(client, recipe, '2026-11-18')
        self.assertEqual(self.request(client, '/api/recipes/' + str(recipe['id']), 'DELETE')[0], 200)
        day = self.totals(client)['days'][0]
        self.assertEqual(day['mealCount'], 0)
        self.assertTrue(day['complete'])
        self.assertTrue(all(day[n] == 0 for n in NUTRIENTS))

    def test_missing_values_are_null_explicit_zero_is_known_and_both_survive_restart(self):
        client = self.client()
        account, _ = self.register(client, 'alice@example.com')
        zero = self.recipe(client, **{n: 0 for n in NUTRIENTS})
        partial = self.recipe(client, calories=100, fat=0)
        self.meal(client, zero, '2026-11-18')
        self.meal(client, partial, '2026-11-19')
        self.meal(client, partial, '2026-11-19')
        before = self.totals(client, '2026-11-18', '2026-11-19')
        first, second = before['days']
        self.assertTrue(first['complete'])
        self.assertTrue(all(first[n] == 0 for n in NUTRIENTS))
        self.assertFalse(second['complete'])
        self.assertEqual(second['calories'], 200)
        self.assertEqual(second['fat'], 0)
        for nutrient in ['protein', 'carbohydrates', 'fiber']:
            self.assertIsNone(second[nutrient])
            self.assertEqual(second['missingNutrition'][nutrient], 2)
        stored = Path(str(self.storage) + '.accounts', 'users', account['id'], 'recipes.properties')
        saved_bytes = stored.read_bytes()
        self.stop()
        self.start()
        self.request(client, '/api/auth/login', 'POST', dict(email='alice@example.com', password=auth.PASSWORD))
        self.assertEqual(self.totals(client, '2026-11-18', '2026-11-19'), before)
        self.assertEqual(stored.read_bytes(), saved_bytes)

    def test_legacy_zeroes_remain_unknown_without_changing_existing_recipe_responses(self):
        client = self.client()
        account, _ = self.register(client, 'alice@example.com')
        recipe = self.recipe(client, **{**NUTRITION, 'fiber': 0})
        self.meal(client, recipe, '2026-11-18')
        stored = Path(str(self.storage) + '.accounts', 'users', account['id'], 'recipes.properties')
        legacy = '\n'.join(line for line in stored.read_text().splitlines() if '.knownNutrition=' not in line) + '\n'
        stored.write_text(legacy)
        self.assertEqual(self.request(client, '/api/recipes')[1], [recipe])
        day = self.totals(client)['days'][0]
        self.assertEqual(day['calories'], 400)
        self.assertIsNone(day['fiber'])
        self.assertEqual(day['missingNutrition']['fiber'], 1)
        self.assertFalse(day['complete'])
        self.assertEqual(stored.read_text(), legacy)
        # Saving a different recipe preserves the old entry's uncertainty.
        self.recipe(client, name='Another recipe', **NUTRITION)
        self.assertEqual(self.totals(client)['days'][0], day)

    def test_authentication_methods_strict_dates_and_bounded_range(self):
        client = self.client()
        valid = BASE + '?start=2026-11-18&end=2026-11-18'
        self.assertEqual(self.request(client, valid)[0], 401)
        self.register(client, 'alice@example.com')
        self.assertEqual(self.request(client, valid, verified=False)[0], 200)
        status, _, headers = self.request(client, valid, 'POST', {})
        self.assertEqual(status, 405)
        self.assertEqual(headers['Allow'], 'GET')
        self.assertEqual(self.request(client, valid, 'POST', {}, verified=False)[0], 403)
        for query in ['', '?start=2026-11-18', '?end=2026-11-18',
                      '?start=2026-02-29&end=2026-03-01', '?start=0000-01-01&end=2026-01-01',
                      '?start=2026-1-01&end=2026-01-02', '?start=2026-11-19&end=2026-11-18',
                      '?start=2026-11-18&end=2026-11-18&ownerId=someone',
                      '?start=2026-11-18&end=2026-11-18&%73tart=2026-11-18',
                      '?start=2026-11-18&end=2026-11-18&',
                      '?start=2024-01-01&end=2025-01-01']:
            with self.subTest(query=query):
                self.assertEqual(self.request(client, BASE + query)[0], 400)
        self.assertEqual(self.request(client, BASE + '/extra')[0], 404)
        days = self.totals(client, '2024-01-01', '2024-12-31')['days']
        self.assertEqual(len(days), 366)
        self.assertIn('2024-02-29', [d['date'] for d in days])
        self.assertEqual(self.totals(client, '9999-12-31', '9999-12-31')['days'][0]['mealCount'], 0)

    def test_orphaned_meals_are_reported_and_storage_failures_do_not_look_like_zero(self):
        client = self.client()
        account, _ = self.register(client, 'alice@example.com')
        recipe = self.recipe(client, **NUTRITION)
        meal = self.meal(client, recipe, '2026-11-18')
        directory = Path(str(self.storage) + '.accounts', 'users', account['id'])
        stored = directory / 'recipes.properties'
        original = stored.read_bytes()
        # Represents old/external storage damage, not the normal cascade-delete API.
        stored.write_text('version=1\ncount=0\nlastId=1\n')
        result = self.totals(client)
        self.assertEqual(result['days'][0]['mealCount'], 1)
        self.assertFalse(result['days'][0]['complete'])
        self.assertTrue(all(result['days'][0][n] is None for n in NUTRIENTS))
        self.assertEqual(result['warnings'][0]['mealId'], meal['id'])
        self.assertEqual(result['warnings'][0]['recipeId'], recipe['id'])
        self.assertEqual(stored.read_text(), 'version=1\ncount=0\nlastId=1\n')
        malformed_stores = [
            'broken recipe storage',
            original.decode().replace('knownNutrition=', 'knownNutrition=unknown,'),
            original.decode().replace('recipe.0.calories=400', 'recipe.0.calories=-1'),
            original.decode().replace('recipe.0.calories=400', 'recipe.0.calories=100001'),
        ]
        for malformed in malformed_stores:
            malformed_bytes = malformed.encode()
            stored.write_bytes(malformed_bytes)
            self.assertEqual(self.request(client, BASE + '?start=2026-11-18&end=2026-11-18')[0], 500)
            self.assertEqual(stored.read_bytes(), malformed_bytes)
        stored.write_bytes(original)
        meal_file = directory / 'meals.properties'
        meal_file.write_text('broken meal storage')
        self.assertEqual(self.request(client, BASE + '?start=2026-11-18&end=2026-11-18')[0], 500)
        self.assertEqual(meal_file.read_text(), 'broken meal storage')


if __name__ == '__main__':
    unittest.main()
