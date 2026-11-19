"""SCRUM-135 atomic plan scheduling, account isolation and persistent calendar meals."""
import unittest
from pathlib import Path
import test_auth_api as auth


class PlanScheduleTest(unittest.TestCase):
    setUp = auth.AuthApiTest.setUp
    tearDown = auth.AuthApiTest.tearDown
    start = auth.AuthApiTest.start
    stop = auth.AuthApiTest.stop
    client = auth.AuthApiTest.client
    request = auth.AuthApiTest.request
    register = auth.AuthApiTest.register

    def test_atomic_plan_dates_existing_meals_privacy_and_restart(self):
        alice, bob, anonymous = self.client(), self.client(), self.client()
        self.assertEqual(self.request(anonymous, '/api/meals/plan', 'POST', {})[0], 401)
        self.register(alice, 'alice@example.com')
        self.register(bob, 'bob@example.com')
        one = self.request(alice, '/api/recipes', 'POST', {**auth.RECIPE, 'category': 'High Protein', 'name': 'First'})[1]
        two = self.request(alice, '/api/recipes', 'POST', {**auth.RECIPE, 'category': 'High Protein', 'name': 'Second'})[1]
        # Different account has its own recipe 1. IDs alone cannot grant access.
        self.request(bob, '/api/recipes', 'POST', {**auth.RECIPE, 'category': 'High Protein'})
        existing = self.request(alice, '/api/meals', 'POST', dict(recipeId=one['id'], date='2026-12-31', mealType='Dinner'))[1]
        fields = dict(plan='High Protein', startDate='2026-12-31', mealType='Dinner', recipeIds=f"{one['id']},{two['id']}")
        self.assertEqual(self.request(alice, '/api/meals/plan', 'POST', fields, verified=False)[0], 403)
        self.assertEqual(self.request(alice, '/api/meals/plan')[0], 405)
        before = self.request(alice, '/api/meals')[1]
        for patch, expected in [({'recipeIds': f"{one['id']},999"}, 404),
                                ({'recipeIds': f"{one['id']},{one['id']}"}, 400),
                                ({'recipeIds': ''}, 400), ({'plan': 'Keto'}, 400),
                                ({'startDate': '2026-02-30'}, 400), ({'startDate': '9999-12-31'}, 400),
                                ({'mealType': 'invalid'}, 400)]:
            self.assertEqual(self.request(alice, '/api/meals/plan', 'POST', {**fields, **patch})[0], expected)
            self.assertEqual(self.request(alice, '/api/meals')[1], before)
        self.assertEqual(self.request(bob, '/api/meals/plan', 'POST', fields)[0], 404)
        self.assertEqual(self.request(bob, '/api/meals')[1], [])
        status, added, _ = self.request(alice, '/api/meals/plan', 'POST', fields)
        self.assertEqual(status, 201)
        self.assertEqual([meal['date'] for meal in added], ['2026-12-31', '2027-01-01'])
        self.assertEqual([meal['name'] for meal in added], ['First', 'Second'])
        self.assertEqual(self.request(alice, '/api/meals')[1], [existing, *added])
        self.stop(); self.start()
        self.request(alice, '/api/auth/login', 'POST', dict(email='alice@example.com', password=auth.PASSWORD))
        self.assertEqual(self.request(alice, '/api/meals')[1], [existing, *added])

    def test_storage_failure_leaves_previous_calendar_intact(self):
        alice = self.client()
        account, _ = self.register(alice, 'alice@example.com')
        recipe = self.request(alice, '/api/recipes', 'POST', {**auth.RECIPE, 'category': 'Keto'})[1]
        existing = self.request(alice, '/api/meals', 'POST', dict(recipeId=recipe['id'], date='2026-11-20', mealType='Dinner'))[1]
        storage = Path(str(self.storage) + '.accounts', 'users', account['id'], 'meals.properties')
        original = storage.read_bytes()
        # An unreadable/corrupted existing record must never be overwritten by a partial plan.
        storage.write_text('broken')
        fields = dict(plan='Keto', startDate='2026-11-20', mealType='Lunch', recipeIds=str(recipe['id']))
        self.assertEqual(self.request(alice, '/api/meals/plan', 'POST', fields)[0], 500)
        self.assertEqual(storage.read_text(), 'broken')
        storage.write_bytes(original)
        self.assertEqual(self.request(alice, '/api/meals')[1], [existing])
        self.assertEqual(self.request(alice, '/api/meals/plan', 'POST', fields)[0], 201)
