"""Generated shopping lists, stable IDs and review regressions against the real API."""
from pathlib import Path
import unittest
import test_auth_api as auth


class ShoppingApiTest(unittest.TestCase):
    setUp = auth.AuthApiTest.setUp
    tearDown = auth.AuthApiTest.tearDown
    start = auth.AuthApiTest.start
    stop = auth.AuthApiTest.stop
    client = auth.AuthApiTest.client
    request = auth.AuthApiTest.request
    register = auth.AuthApiTest.register
    path = '/api/shopping-list?start=2026-10-01&end=2026-10-07'

    def test_generation_privacy_missing_recipe_and_id_persistence(self):
        alice, bob = self.client(), self.client()
        self.assertEqual(self.request(alice, self.path)[0], 401)
        self.register(alice, 'alice@example.com')
        self.register(bob, 'bob@example.com')
        empty = {'start': '2026-10-01', 'end': '2026-10-07', 'items': [], 'warnings': []}
        self.assertEqual(self.request(alice, self.path)[1], empty)
        recipe = self.request(alice, '/api/recipes', 'POST', {**auth.RECIPE, 'ingredients': ' Rice\nBeans\n\n rice '})[1]
        for date in ['2026-10-01', '2026-10-07', '2026-10-08']:
            self.assertEqual(self.request(alice, '/api/meals', 'POST', dict(recipeId=recipe['id'], date=date, mealType='Dinner'))[0], 201)
        status, result, _ = self.request(alice, self.path)
        self.assertEqual(status, 200)
        self.assertEqual([item['name'] for item in result['items']], ['Rice', 'Beans'])
        self.assertEqual([item['occurrences'] for item in result['items']], [4, 2])
        self.assertEqual({s['date'] for s in result['items'][0]['sources']}, {'2026-10-01', '2026-10-07'})
        self.assertEqual(self.request(bob, self.path + '&ownerId=alice')[1], empty)
        self.request(alice, '/api/recipes/' + str(recipe['id']), 'DELETE')
        self.stop(); self.start()
        self.assertEqual(self.request(alice, self.path)[0], 401)
        self.request(alice, '/api/auth/login', 'POST', dict(email='alice@example.com', password=auth.PASSWORD))
        replacement = self.request(alice, '/api/recipes', 'POST', auth.RECIPE)[1]
        self.assertGreater(replacement['id'], recipe['id'])
        missing = self.request(alice, self.path)[1]
        self.assertEqual(missing['items'], [])
        self.assertEqual(len(missing['warnings']), 2)
        self.assertEqual(missing['warnings'][0]['source']['recipeId'], recipe['id'])

    def test_range_validation_and_storage_failure(self):
        alice = self.client()
        account, _ = self.register(alice, 'alice@example.com')
        for query in ['', '?start=2026-02-30&end=2026-03-01', '?start=2026-10-08&end=2026-10-01',
                      '?start=0000-01-01&end=2026-10-01', '?start=2026-10-01&start=2026-10-02&end=2026-10-07']:
            self.assertEqual(self.request(alice, '/api/shopping-list' + query)[0], 400)
        self.assertEqual(self.request(alice, self.path, 'POST', {})[0], 405)
        storage = Path(str(self.storage) + '.accounts', 'users', account['id'], 'meals.properties')
        storage.parent.mkdir(parents=True)
        storage.write_text('broken')
        self.assertEqual(self.request(alice, self.path)[0], 500)
        storage.unlink()
        self.assertEqual(self.request(alice, self.path)[0], 200)

    def test_throttling_does_not_block_other_accounts_or_count_successes(self):
        alice = self.client()
        self.register(alice, 'alice@example.com')
        fields = dict(email='alice@example.com', password=auth.PASSWORD)
        for _ in range(21):
            self.assertEqual(self.request(alice, '/api/auth/login', 'POST', fields)[0], 200)
        for _ in range(20):
            self.assertEqual(self.request(alice, '/api/auth/login', 'POST', dict(email='bad', password=''))[0], 400)
        self.assertEqual(self.request(alice, '/api/auth/login', 'POST', dict(email='bad', password=''))[0], 429)
        self.assertEqual(self.request(alice, '/api/auth/login', 'POST', fields)[0], 200)

    def test_attack_on_email_cannot_lock_out_another_client(self):
        victim, attacker = self.client(), self.client()
        self.register(victim, 'victim@example.com')
        attacker_source = {'X-Forwarded-For': '192.0.2.10'}
        victim_source = {'X-Forwarded-For': '192.0.2.20'}
        bad = dict(email=' VICTIM@EXAMPLE.COM ', password='wrong password')
        for _ in range(20):
            self.assertEqual(self.request(attacker, '/api/auth/login', 'POST', bad, headers=attacker_source)[0], 401)
        # Email casing/spacing cannot evade the limit for the attacking source.
        good = dict(email='victim@example.com', password=auth.PASSWORD)
        status, _, headers = self.request(attacker, '/api/auth/login', 'POST', good, headers=attacker_source)
        self.assertEqual(status, 429)
        self.assertGreater(int(headers['Retry-After']), 0)
        # Another client can still sign into the SAME targeted account via the proxy.
        self.assertEqual(self.request(victim, '/api/auth/login', 'POST', good, headers=victim_source)[0], 200)
        # That successful login must not clear the attacker's limit.
        self.assertEqual(self.request(attacker, '/api/auth/login', 'POST', good, headers=attacker_source)[0], 429)
