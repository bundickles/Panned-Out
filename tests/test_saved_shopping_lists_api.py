"""SCRUM-59/60 real HTTP checks; generated-list payloads are explicit fixtures.
These tests do not claim that the separate shopping-list generator exists.
"""
import copy
from pathlib import Path
import unittest
import uuid
import test_auth_api as auth

BASE = '/api/shopping-lists'


class SavedShoppingListsTest(unittest.TestCase):
    setUp = auth.AuthApiTest.setUp
    tearDown = auth.AuthApiTest.tearDown
    start = auth.AuthApiTest.start
    stop = auth.AuthApiTest.stop
    client = auth.AuthApiTest.client
    request = auth.AuthApiTest.request
    register = auth.AuthApiTest.register

    def fixture(self, client):
        recipe = self.request(client, '/api/recipes', 'POST', auth.RECIPE)[1]
        status, meal, _ = self.request(client, '/api/meals', 'POST',
                                      dict(recipeId=recipe['id'], date='2026-10-15', mealType='Dinner'))
        self.assertEqual(status, 201)
        fields = {'start': '2026-10-15', 'end': '2026-10-17', 'itemCount': '2', 'warningCount': '1',
                  'item.0.text': '  Rice "\u65e5\u672c"\n1 cup  ', 'item.0.occurrences': '2', 'item.0.sourceCount': '1',
                  'item.0.source.0.mealId': meal['id'], 'item.0.source.0.recipeId': str(recipe['id']),
                  'item.1.text': 'Beans', 'item.1.occurrences': '1', 'item.1.sourceCount': '1',
                  'item.1.source.0.mealId': meal['id'], 'item.1.source.0.recipeId': str(recipe['id']),
                  'warning.0.message': 'Recipe unavailable at generation time.',
                  'warning.0.mealId': meal['id'], 'warning.0.recipeId': str(recipe['id'])}
        return fields, recipe, meal

    def save(self, client, fields):
        status, saved, headers = self.request(client, BASE, 'POST', fields)
        self.assertEqual(status, 201, saved)
        self.assertEqual(headers['Location'], BASE + '/' + saved['id'])
        return saved

    def update(self, client, saved, item=0, purchased='true', **extra):
        path = BASE + '/' + saved['id'] + '/items/' + saved['items'][item]['id'] + '/purchased'
        return self.request(client, path, 'PATCH', dict(purchased=purchased, **extra))

    def restart_login(self, client):
        self.stop()
        self.start()
        self.assertEqual(self.request(client, BASE)[0], 401)
        self.assertEqual(self.request(client, '/api/auth/login', 'POST',
                                     dict(email='alice@example.com', password=auth.PASSWORD))[0], 200)

    def test_snapshot_roundtrip_restart_and_recipe_independence(self):
        alice = self.client()
        self.register(alice, 'alice@example.com')
        self.assertEqual(self.request(alice, BASE)[:2], (200, []))
        fields, recipe, meal = self.fixture(alice)
        saved = self.save(alice, fields)
        uuid.UUID(saved['id'])
        self.assertEqual(len({item['id'] for item in saved['items']}), 2)
        for i, item in enumerate(saved['items']):
            uuid.UUID(item['id'])
            self.assertEqual(item['text'], fields[f'item.{i}.text'])
            self.assertEqual(item['occurrences'], int(fields[f'item.{i}.occurrences']))
            self.assertEqual(item['sources'], [dict(mealId=meal['id'], recipeId=recipe['id'])])
            self.assertFalse(item['purchased'])
        self.assertEqual(saved['start'], fields['start'])
        self.assertEqual(saved['end'], fields['end'])
        self.assertEqual(saved['warnings'], [dict(message=fields['warning.0.message'],
                                                source=dict(mealId=meal['id'], recipeId=recipe['id']))])
        self.assertEqual(self.request(alice, BASE)[1], [saved])
        self.assertEqual(self.request(alice, BASE + '/' + saved['id'])[1], saved)
        # Changing source data does not rewrite the saved shopping list.
        self.assertEqual(self.request(alice, '/api/recipes/' + str(recipe['id']), 'PUT',
                                     {**auth.RECIPE, 'ingredients': 'New ingredients'})[0], 200)
        self.assertEqual(self.request(alice, '/api/recipes/' + str(recipe['id']), 'DELETE')[0], 200)
        self.assertEqual(self.request(alice, '/api/meals/' + meal['id'], 'DELETE')[0], 200)
        self.restart_login(alice)
        self.assertEqual(self.request(alice, BASE + '/' + saved['id'])[1], saved)
        self.assertEqual(self.request(alice, BASE)[1], [saved])

    def test_purchased_update_uncheck_and_persistence(self):
        alice = self.client()
        self.register(alice, 'alice@example.com')
        fields, _, _ = self.fixture(alice)
        fields.update({'id': str(uuid.uuid4()), 'item.0.id': str(uuid.uuid4()), 'item.0.purchased': 'true'})
        saved = self.save(alice, fields)
        self.assertNotEqual(saved['id'], fields['id'])
        self.assertNotEqual(saved['items'][0]['id'], fields['item.0.id'])
        self.assertFalse(saved['items'][0]['purchased'])
        second = self.save(alice, fields)
        self.assertNotEqual(saved['id'], second['id'])
        expected = copy.deepcopy(saved)
        expected['items'][0]['purchased'] = True
        status, updated, _ = self.update(alice, saved)
        self.assertEqual(status, 200)
        self.assertEqual(updated, expected)
        self.assertEqual(self.update(alice, saved)[1], expected)  # Idempotent explicit status.
        self.restart_login(alice)
        self.assertEqual(self.request(alice, BASE + '/' + saved['id'])[1], expected)
        self.assertEqual(self.request(alice, BASE + '/' + second['id'])[1], second)
        self.assertEqual(self.update(alice, saved, purchased='false')[1], saved)
        self.restart_login(alice)
        self.assertEqual(self.request(alice, BASE + '/' + saved['id'])[1], saved)

    def test_account_isolation_including_source_references(self):
        alice, bob, anonymous = self.client(), self.client(), self.client()
        account, _ = self.register(alice, 'alice@example.com')
        self.register(bob, 'bob@example.com')
        fields, recipe, _ = self.fixture(alice)
        saved = self.save(alice, fields)
        bob_fields, bob_recipe, _ = self.fixture(bob)
        self.assertEqual(bob_recipe['id'], recipe['id'])
        self.assertEqual(self.request(bob, BASE)[1], [])
        self.assertEqual(self.request(bob, BASE + '/' + saved['id'])[0], 404)
        self.assertEqual(self.update(bob, saved)[0], 404)
        self.assertEqual(self.request(bob, BASE, 'POST', {**fields, 'ownerId': account['id']})[0], 409)
        bob_saved = self.save(bob, {**bob_fields, 'ownerId': account['id'], 'id': saved['id']})
        self.assertNotEqual(bob_saved['id'], saved['id'])
        self.assertEqual(self.request(alice, BASE)[1], [saved])
        self.assertEqual(self.request(bob, BASE)[1], [bob_saved])
        for method, path, data in [('GET', BASE, None), ('GET', BASE + '/' + saved['id'], None),
                                   ('POST', BASE, fields),
                                   ('PATCH', BASE + '/' + saved['id'] + '/items/' + saved['items'][0]['id'] + '/purchased',
                                    {'purchased': 'true'})]:
            self.assertEqual(self.request(anonymous, path, method, data)[0], 401)
        self.assertEqual(self.request(alice, BASE, 'POST', fields, verified=False)[0], 403)
        path = BASE + '/' + saved['id'] + '/items/' + saved['items'][0]['id'] + '/purchased'
        self.assertEqual(self.request(alice, path, 'PATCH', {'purchased': 'true'}, verified=False)[0], 403)
        self.assertEqual(self.request(alice, path, 'PATCH', {'purchased': 'true'},
                                     headers={'Sec-Fetch-Site': 'cross-site'})[0], 403)
        self.assertEqual(self.request(alice, BASE)[1], [saved])

    def test_invalid_input_does_not_change_saved_data(self):
        alice = self.client()
        self.register(alice, 'alice@example.com')
        fields, _, meal = self.fixture(alice)
        saved = self.save(alice, fields)
        for change in [{'start': '2026-02-30'}, {'end': '2026-10-14'}, {'itemCount': '-1'},
                       {'itemCount': '501'}, {'item.0.text': ' '}, {'item.0.occurrences': '0'},
                       {'item.0.sourceCount': '0'}, {'warningCount': '-1'}]:
            with self.subTest(change=change):
                self.assertEqual(self.request(alice, BASE, 'POST', {**fields, **change})[0], 400)
        for value in ['yes', '', 'TRUE', '1']:
            self.assertEqual(self.update(alice, saved, purchased=value)[0], 400)
        self.assertEqual(self.update(alice, saved, text='Changed ingredient')[0], 400)
        path = BASE + '/' + saved['id'] + '/items/' + str(uuid.uuid4()) + '/purchased'
        self.assertEqual(self.request(alice, path, 'PATCH', {'purchased': 'true'})[0], 404)
        self.assertEqual(self.request(alice, BASE + '/' + str(uuid.uuid4()))[0], 404)
        self.assertEqual(self.request(alice, BASE + '/invalid-id')[0], 400)
        self.assertEqual(self.request(alice, BASE, 'POST', {**fields, 'start': '2026-10-16'})[0], 409)
        self.assertEqual(self.request(alice, BASE, 'POST', {**fields, 'item.0.text': 'x' * 66000})[0], 413)
        self.assertEqual(self.request(alice, BASE, 'POST', fields, headers={'Content-Type': 'application/json'})[0], 415)
        self.assertEqual(self.request(alice, BASE + '/' + saved['id'], 'DELETE')[0], 405)
        self.assertEqual(self.request(alice, BASE)[1], [saved])
        self.request(alice, '/api/meals/' + meal['id'], 'DELETE')
        self.assertEqual(self.request(alice, BASE, 'POST', fields)[0], 409)
        self.assertEqual(self.request(alice, BASE)[1], [saved])

    def test_empty_snapshot_and_missing_recipe_warning(self):
        alice = self.client()
        self.register(alice, 'alice@example.com')
        empty = self.save(alice, dict(start='2026-10-15', end='2026-10-15', itemCount='0', warningCount='0'))
        self.assertEqual(empty['items'], [])
        self.assertEqual(empty['warnings'], [])
        fields, recipe, _ = self.fixture(alice)
        self.request(alice, '/api/recipes/' + str(recipe['id']), 'DELETE')
        fields['itemCount'] = '0'
        warning_only = self.save(alice, fields)
        self.restart_login(alice)
        self.assertEqual(self.request(alice, BASE + '/' + warning_only['id'])[1], warning_only)

    def test_corrupt_storage_not_overwritten(self):
        alice = self.client()
        account, _ = self.register(alice, 'alice@example.com')
        fields, _, _ = self.fixture(alice)
        saved = self.save(alice, fields)
        directory = Path(str(self.storage) + '.accounts', 'users', account['id'], 'shopping-lists')
        storage = directory / (saved['id'] + '.properties')
        storage.write_text('broken shopping list')
        self.assertEqual(self.request(alice, BASE + '/' + saved['id'])[0], 500)
        self.assertEqual(self.request(alice, BASE)[0], 500)
        self.assertEqual(self.update(alice, saved)[0], 500)
        self.assertEqual(storage.read_text(), 'broken shopping list')
        self.assertEqual(list(directory.glob('*.tmp')), [])

    def test_storage_write_failure_is_reported(self):
        alice = self.client()
        account, _ = self.register(alice, 'alice@example.com')
        fields, _, _ = self.fixture(alice)
        directory = Path(str(self.storage) + '.accounts', 'users', account['id'], 'shopping-lists')
        directory.write_text('An existing file blocks the storage directory')
        self.assertEqual(self.request(alice, BASE, 'POST', fields)[0], 500)
        self.assertEqual(directory.read_text(), 'An existing file blocks the storage directory')


if __name__ == '__main__':
    unittest.main()
