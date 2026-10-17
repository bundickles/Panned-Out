"""SCRUM-119: public generation contract against the real authenticated API."""
import unittest
import test_auth_api as auth


class GenerationContractTest(unittest.TestCase):
    setUp = auth.AuthApiTest.setUp
    tearDown = auth.AuthApiTest.tearDown
    start = auth.AuthApiTest.start
    stop = auth.AuthApiTest.stop
    client = auth.AuthApiTest.client
    request = auth.AuthApiTest.request
    register = auth.AuthApiTest.register
    path = '/api/shopping-list?start=2026-10-01&end=2026-10-07'

    def recipe(self, client, name, ingredients):
        status, result, _ = self.request(client, '/api/recipes', 'POST',
                                         {**auth.RECIPE, 'name': name, 'ingredients': ingredients})
        self.assertEqual(status, 201)
        return result

    def schedule(self, client, recipe, date):
        status, meal, _ = self.request(client, '/api/meals', 'POST',
                                       dict(recipeId=recipe['id'], date=date, mealType='Dinner'))
        self.assertEqual(status, 201)
        return meal

    @staticmethod
    def source(meal):
        return dict(mealId=meal['id'], recipeId=meal['recipeId'], date=meal['date'], recipeName=meal['name'])

    def test_schema_grouping_order_counts_and_inclusive_dates(self):
        client = self.client()
        self.register(client, 'contract@example.com')
        first = self.recipe(client, 'Bowl "日本"', '  Rice\r\n\r\nRed   beans\nRICE\n1 cup rice\n2 cups rice\n Café ')
        second = self.recipe(client, 'Beans bowl', ' red\tbeans \nSpinach\nCAFÉ')
        # Store the later date first to verify first-appearance rather than date sorting.
        end = self.schedule(client, first, '2026-10-07')
        start = self.schedule(client, second, '2026-10-01')
        self.schedule(client, first, '2026-09-30')
        self.schedule(client, second, '2026-10-08')
        status, result, headers = self.request(client, self.path)
        self.assertEqual(status, 200)
        self.assertEqual(set(result), {'start', 'end', 'items', 'warnings'})
        self.assertEqual((result['start'], result['end'], result['warnings']), ('2026-10-01', '2026-10-07', []))
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertIn('application/json', headers['Content-Type'])
        self.assertEqual([i['name'] for i in result['items']], ['Rice', 'Red beans', '1 cup rice', '2 cups rice', 'Café', 'Spinach'])
        expected_sources = [[end, end], [end, start], [end], [end], [end, start], [start]]
        actual_meals = {meal['id']: meal for meal in self.request(client, '/api/meals')[1]}
        for item, expected in zip(result['items'], expected_sources):
            self.assertEqual(set(item), {'name', 'occurrences', 'sources'})
            self.assertEqual(item['occurrences'], len(expected))
            self.assertEqual(item['occurrences'], len(item['sources']))
            self.assertEqual(item['sources'], [self.source(meal) for meal in expected])
            for source in item['sources']:
                self.assertEqual(source, self.source(actual_meals[source['mealId']]))
        self.assertEqual(self.request(client, self.path)[1], result)

    def test_empty_range_single_day_and_signed_out(self):
        client = self.client()
        self.assertEqual(self.request(client, self.path)[0], 401)
        self.register(client, 'empty@example.com')
        self.assertEqual(self.request(client, self.path)[1],
                         dict(start='2026-10-01', end='2026-10-07', items=[], warnings=[]))
        recipe = self.recipe(client, 'Rice bowl', 'Rice\nBeans')
        meal = self.schedule(client, recipe, '2026-10-04')
        status, result, _ = self.request(client, '/api/shopping-list?start=2026-10-04&end=2026-10-04')
        self.assertEqual(status, 200)
        self.assertEqual([item['sources'] for item in result['items']], [[self.source(meal)], [self.source(meal)]])
        self.assertEqual(self.request(client, '/api/shopping-list?start=2026-10-05&end=2026-10-06')[1]['items'], [])

    def test_unicode_whitespace_is_grouped_with_first_spelling(self):
        client = self.client()
        self.register(client, 'unicode@example.com')
        recipe = self.recipe(client, 'Beans', '\u00a0 Red\u00a0 beans \u00a0\nRED\tBEANS\n\u2003\nRice')
        self.schedule(client, recipe, '2026-10-04')
        result = self.request(client, self.path)[1]
        self.assertEqual([item['name'] for item in result['items']], ['Red beans', 'Rice'])
        self.assertEqual([item['occurrences'] for item in result['items']], [2, 1])


if __name__ == '__main__':
    unittest.main()
