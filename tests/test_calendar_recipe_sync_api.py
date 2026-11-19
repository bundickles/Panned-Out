"""SCRUM-181: recipe changes stay consistent with the account's calendar."""
from contextlib import contextmanager
import os
from pathlib import Path
import unittest

import test_auth_api as auth


@contextmanager
def prevent_file_replacement(path):
    """Allow Windows reads/writes but deny rename/delete to force an atomic-save error."""
    import ctypes
    from ctypes import wintypes

    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                  wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD,
                                  wintypes.HANDLE]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    handle = kernel.CreateFileW(str(path), 0x80000000, 3, None, 3, 0x80, None)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        yield
    finally:
        kernel.CloseHandle(handle)


class CalendarRecipeSyncApiTest(unittest.TestCase):
    setUp = auth.AuthApiTest.setUp
    tearDown = auth.AuthApiTest.tearDown
    start = auth.AuthApiTest.start
    stop = auth.AuthApiTest.stop
    client = auth.AuthApiTest.client
    request = auth.AuthApiTest.request
    register = auth.AuthApiTest.register

    def storage_file(self, account, name):
        return Path(str(self.storage) + '.accounts', 'users', account['id'], name)

    def recipe(self, client, name='Rice bowl'):
        status, recipe, _ = self.request(client, '/api/recipes', 'POST',
                                         {**auth.RECIPE, 'name': name})
        self.assertEqual(status, 201, recipe)
        return recipe

    def schedule(self, client, recipe, date='2026-11-19', meal_type='Dinner'):
        status, meal, _ = self.request(client, '/api/meals', 'POST',
                                       dict(recipeId=recipe['id'], date=date, mealType=meal_type))
        self.assertEqual(status, 201, meal)
        return meal

    def login(self, client, email):
        status, result, _ = self.request(client, '/api/auth/login', 'POST',
                                         dict(email=email, password=auth.PASSWORD))
        self.assertEqual(status, 200, result)

    def test_rename_updates_each_calendar_name_without_rescheduling(self):
        alice, bob = self.client(), self.client()
        self.register(alice, 'alice@example.com')
        self.register(bob, 'bob@example.com')
        recipe = self.recipe(alice)
        first = self.schedule(alice, recipe)
        second = self.schedule(alice, recipe, date='2026-11-20', meal_type='Lunch')
        bob_recipe = self.recipe(bob, 'Bob rice')
        bob_meal = self.schedule(bob, bob_recipe)
        self.assertEqual(recipe['id'], bob_recipe['id'])
        path = '/api/recipes/' + str(recipe['id'])
        status, _, _ = self.request(alice, path, 'PUT', {**auth.RECIPE, 'name': 'Renamed rice bowl'})
        self.assertEqual(status, 200)
        expected = [{**meal, 'name': 'Renamed rice bowl'} for meal in (first, second)]
        self.assertEqual(self.request(alice, '/api/meals')[:2], (200, expected))
        self.assertEqual(self.request(bob, '/api/meals')[1], [bob_meal])
        self.stop()
        self.start()
        self.login(alice, 'alice@example.com')
        self.assertEqual(self.request(alice, '/api/meals')[1], expected)

    def test_delete_cascades_privately_and_preserves_saved_shopping_snapshot(self):
        alice, bob, anonymous = self.client(), self.client(), self.client()
        account, _ = self.register(alice, 'alice@example.com')
        self.register(bob, 'bob@example.com')
        recipe = self.recipe(alice)
        first = self.schedule(alice, recipe)
        second = self.schedule(alice, recipe, date='2026-11-20')
        other_recipe = self.recipe(alice, 'Keep this recipe')
        other_meal = self.schedule(alice, other_recipe)
        bob_recipe = self.recipe(bob, 'Bob rice')
        bob_meal = self.schedule(bob, bob_recipe)
        self.assertEqual(recipe['id'], bob_recipe['id'])
        snapshot = {'start': first['date'], 'end': second['date'], 'itemCount': 1, 'warningCount': 0,
                    'item.0.text': 'Rice', 'item.0.occurrences': 2, 'item.0.sourceCount': 2,
                    'item.0.source.0.mealId': first['id'], 'item.0.source.0.recipeId': recipe['id'],
                    'item.0.source.1.mealId': second['id'], 'item.0.source.1.recipeId': recipe['id']}
        status, saved, _ = self.request(alice, '/api/shopping-lists', 'POST', snapshot)
        self.assertEqual(status, 201, saved)
        list_path = '/api/shopping-lists/' + saved['id']
        status, saved, _ = self.request(alice, list_path + '/items/' + saved['items'][0]['id'] + '/purchased',
                                        'PATCH', dict(purchased='true'))
        self.assertEqual(status, 200)
        list_storage = self.storage_file(account, 'shopping-lists') / (saved['id'] + '.properties')
        original_snapshot = list_storage.read_bytes()
        recipe_path = '/api/recipes/' + str(recipe['id'])
        self.assertEqual(self.request(anonymous, recipe_path, 'DELETE')[0], 401)
        self.assertEqual(self.request(alice, recipe_path, 'DELETE', verified=False)[0], 403)
        self.assertEqual(len(self.request(alice, '/api/meals')[1]), 3)
        self.assertEqual(self.request(alice, recipe_path, 'DELETE')[0], 200)
        self.assertEqual(self.request(alice, '/api/meals')[1], [other_meal])
        self.assertEqual(self.request(alice, '/api/recipes')[1], [other_recipe])
        self.assertEqual(self.request(bob, '/api/meals')[1], [bob_meal])
        self.assertEqual(self.request(bob, '/api/recipes')[1], [bob_recipe])
        for removed in (first, second):
            self.assertEqual(self.request(alice, '/api/meals/' + removed['id'], 'DELETE')[0], 404)
        self.assertEqual(self.request(alice, list_path)[1], saved)
        self.assertEqual(list_storage.read_bytes(), original_snapshot)
        self.assertIn('count=1', self.storage_file(account, 'meals.properties').read_text())
        self.stop()
        self.start()
        self.login(alice, 'alice@example.com')
        self.login(bob, 'bob@example.com')
        self.assertEqual(self.request(alice, '/api/meals')[1], [other_meal])
        self.assertEqual(self.request(bob, '/api/meals')[1], [bob_meal])
        self.assertEqual(self.request(alice, list_path)[1], saved)
        self.assertEqual(list_storage.read_bytes(), original_snapshot)
        self.assertEqual(self.request(alice, recipe_path, 'DELETE')[0], 404)

    def test_corrupt_storage_fails_without_claiming_success_or_changing_other_file(self):
        alice = self.client()
        account, _ = self.register(alice, 'alice@example.com')
        recipe = self.recipe(alice)
        meal = self.schedule(alice, recipe)
        recipe_path = '/api/recipes/' + str(recipe['id'])
        recipe_storage = self.storage_file(account, 'recipes.properties')
        meal_storage = self.storage_file(account, 'meals.properties')
        recipe_bytes, meal_bytes = recipe_storage.read_bytes(), meal_storage.read_bytes()
        meal_storage.write_text('broken calendar storage')
        status, error, _ = self.request(alice, recipe_path, 'DELETE')
        self.assertEqual(status, 500)
        self.assertIn('Storage unavailable', error['error'])
        self.assertEqual(recipe_storage.read_bytes(), recipe_bytes)
        self.assertEqual(meal_storage.read_text(), 'broken calendar storage')
        meal_storage.write_bytes(meal_bytes)
        recipe_storage.write_text('broken recipe storage')
        self.assertEqual(self.request(alice, recipe_path, 'DELETE')[0], 500)
        self.assertEqual(meal_storage.read_bytes(), meal_bytes)
        self.assertEqual(recipe_storage.read_text(), 'broken recipe storage')
        recipe_storage.write_bytes(recipe_bytes)
        self.assertEqual(self.request(alice, '/api/meals')[1], [meal])

    @unittest.skipUnless(os.name == 'nt', 'Windows sharing flags exercise atomic replacement failures')
    def test_atomic_replacement_failures_do_not_lose_calendar_or_recipe(self):
        alice = self.client()
        account, _ = self.register(alice, 'alice@example.com')
        recipe = self.recipe(alice)
        meal = self.schedule(alice, recipe)
        recipe_path = '/api/recipes/' + str(recipe['id'])
        for filename in ('meals.properties', 'recipes.properties'):
            with self.subTest(filename=filename):
                with prevent_file_replacement(self.storage_file(account, filename)):
                    status, error, _ = self.request(alice, recipe_path, 'DELETE')
                    self.assertEqual(status, 500)
                    self.assertIn('Storage unavailable', error['error'])
                self.assertEqual(self.request(alice, '/api/recipes')[1], [recipe])
                self.assertEqual(self.request(alice, '/api/meals')[1], [meal])
        self.assertEqual(self.request(alice, recipe_path, 'DELETE')[0], 200)
        self.assertEqual(self.request(alice, '/api/meals')[1], [])


if __name__ == '__main__':
    unittest.main()
