"""SCRUM-179/180 checks against the real Java server and temporary account storage.

Option IDs below are the proposed draft contract, pending Vanny's UI review.
Run after compiling the backend:
    python -m unittest discover -s tests -p test_profile_settings_api.py
"""
from pathlib import Path
import unittest

import test_auth_api as auth


PROFILE = '/api/profile'
SETTINGS = '/api/settings'
DEFAULT_PROFILE = dict(displayName='', icon='default', allergenPreferences=[], proteinPreferences=[])
DEFAULT_SETTINGS = dict(theme='default', calendarView='month', reducedMotion=False)


class ProfileSettingsApiTest(unittest.TestCase):
    setUp = auth.AuthApiTest.setUp
    tearDown = auth.AuthApiTest.tearDown
    start = auth.AuthApiTest.start
    stop = auth.AuthApiTest.stop
    client = auth.AuthApiTest.client
    request = auth.AuthApiTest.request
    register = auth.AuthApiTest.register

    def patch(self, client, path, **fields):
        status, saved, _ = self.request(client, path, 'PATCH', fields)
        self.assertEqual(status, 200, saved)
        return saved

    def get(self, client, path):
        status, data, _ = self.request(client, path)
        self.assertEqual(status, 200, data)
        return data

    def account_directory(self, account):
        return Path(str(self.storage) + '.accounts', 'users', account['id'])

    def login(self, client, email='alice@example.com'):
        status, result, _ = self.request(client, '/api/auth/login', 'POST',
                                         dict(email=email, password=auth.PASSWORD))
        self.assertEqual(status, 200, result)

    def test_defaults_are_read_only_and_existing_account_data_is_preserved(self):
        alice = self.client()
        account, _ = self.register(alice, 'alice@example.com')
        directory = self.account_directory(account)
        self.assertEqual(self.get(alice, PROFILE), DEFAULT_PROFILE)
        self.assertEqual(self.get(alice, SETTINGS), DEFAULT_SETTINGS)
        self.assertFalse((directory / 'profile.properties').exists())
        self.assertFalse((directory / 'settings.properties').exists())
        recipe = self.request(alice, '/api/recipes', 'POST', auth.RECIPE)[1]
        self.patch(alice, PROFILE, displayName='Alice')
        self.patch(alice, SETTINGS, theme='pastel')
        self.assertEqual(self.get(alice, '/api/recipes'), [recipe])
        self.assertEqual(self.get(alice, '/api/auth/me'), account)

    def test_profile_roundtrip_partial_updates_and_clearing_preferences(self):
        alice = self.client()
        self.register(alice, 'alice@example.com')
        saved = self.patch(alice, PROFILE, displayName='\u2003Aayush "日本" 🍲\u2003', icon='pan',
                           allergenPreferences=' milk \n\npeanuts\n', proteinPreferences='tofu\nbeans')
        self.assertEqual(saved, dict(displayName='Aayush "日本" 🍲', icon='pan',
                                     allergenPreferences=['milk', 'peanuts'],
                                     proteinPreferences=['tofu', 'beans']))
        self.assertEqual(self.get(alice, PROFILE), saved)
        saved = self.patch(alice, PROFILE, icon='leaf')
        self.assertEqual(saved['displayName'], 'Aayush "日本" 🍲')
        self.assertEqual(saved['allergenPreferences'], ['milk', 'peanuts'])
        self.assertEqual(saved['proteinPreferences'], ['tofu', 'beans'])
        saved = self.patch(alice, PROFILE, allergenPreferences='', proteinPreferences='')
        self.assertEqual(saved['allergenPreferences'], [])
        self.assertEqual(saved['proteinPreferences'], [])
        self.assertEqual(saved['icon'], 'leaf')
        # The documented limit counts Unicode characters, not UTF-16 code units.
        saved = self.patch(alice, PROFILE, displayName='🍲' * 80)
        self.assertEqual(saved['displayName'], '🍲' * 80)

    def test_settings_partial_updates_and_persistence_after_login_and_restart(self):
        alice = self.client()
        self.register(alice, 'alice@example.com')
        profile = self.patch(alice, PROFILE, displayName='Alice', icon='bowl',
                             allergenPreferences='eggs', proteinPreferences='beans')
        settings = self.patch(alice, SETTINGS, theme='dark', calendarView='week', reducedMotion='true')
        self.assertEqual(settings, dict(theme='dark', calendarView='week', reducedMotion=True))
        settings = self.patch(alice, SETTINGS, theme='colorful')
        self.assertEqual(settings, dict(theme='colorful', calendarView='week', reducedMotion=True))
        self.assertEqual(self.get(alice, PROFILE), profile)
        self.assertEqual(self.request(alice, '/api/auth/logout', 'POST', {})[0], 200)
        for path in (PROFILE, SETTINGS):
            self.assertEqual(self.request(alice, path)[0], 401)
        self.login(alice)
        self.assertEqual(self.get(alice, PROFILE), profile)
        self.assertEqual(self.get(alice, SETTINGS), settings)
        self.stop()
        self.start()
        for path in (PROFILE, SETTINGS):
            self.assertEqual(self.request(alice, path)[0], 401)
        self.login(alice)
        self.assertEqual(self.get(alice, PROFILE), profile)
        self.assertEqual(self.get(alice, SETTINGS), settings)
        self.assertEqual(self.patch(alice, SETTINGS, reducedMotion='false'),
                         dict(theme='colorful', calendarView='week', reducedMotion=False))

    def test_profiles_and_settings_are_private_to_the_session(self):
        alice, bob, anonymous = self.client(), self.client(), self.client()
        account, _ = self.register(alice, 'alice@example.com')
        self.register(bob, 'bob@example.com')
        profile = self.patch(alice, PROFILE, displayName='Alice', icon='leaf',
                             allergenPreferences='peanuts')
        settings = self.patch(alice, SETTINGS, theme='dark')
        self.assertEqual(self.get(bob, PROFILE), DEFAULT_PROFILE)
        self.assertEqual(self.get(bob, SETTINGS), DEFAULT_SETTINGS)
        for path, fields in ((PROFILE, dict(displayName='Bob')), (SETTINGS, dict(theme='pastel'))):
            with self.subTest(path=path):
                self.assertEqual(self.request(anonymous, path)[0], 401)
                self.assertEqual(self.request(anonymous, path, 'PATCH', fields)[0], 401)
                self.assertEqual(self.request(bob, path, 'PATCH',
                                             {**fields, 'ownerId': account['id']})[0], 400)
                self.assertEqual(self.request(bob, path + '?accountId=' + account['id'])[0], 400)
                self.assertEqual(self.request(bob, path + '/' + account['id'])[0], 404)
        bob_profile = self.patch(bob, PROFILE, displayName='Bob', icon='pan')
        bob_settings = self.patch(bob, SETTINGS, theme='pastel', calendarView='day')
        self.assertEqual(self.get(alice, PROFILE), profile)
        self.assertEqual(self.get(alice, SETTINGS), settings)
        self.assertEqual(self.get(bob, PROFILE), bob_profile)
        self.assertEqual(self.get(bob, SETTINGS), bob_settings)

    def test_invalid_updates_leave_the_entire_saved_record_unchanged(self):
        alice = self.client()
        self.register(alice, 'alice@example.com')
        self.assertEqual(self.request(alice, PROFILE, 'PATCH', dict(icon='pan'))[0], 400)
        profile = self.patch(alice, PROFILE, displayName='Alice', icon='pan',
                             allergenPreferences='milk', proteinPreferences='tofu')
        settings = self.patch(alice, SETTINGS, theme='dark', calendarView='week', reducedMotion='true')
        invalid_profiles = [
            {}, dict(displayName=''), dict(displayName=' \u2003 '), dict(displayName='a' * 81),
            dict(displayName='\u00a0\u202f'), dict(displayName='\nAlice\t'),
            dict(displayName='🍲' * 81), dict(displayName='Alice\nBob'), dict(displayName='Alice\x7f'),
            dict(icon='unknown'), dict(allergenPreferences='unknown'), dict(proteinPreferences='unknown'),
            dict(allergenPreferences='milk\nmilk'), dict(proteinPreferences='tofu\n tofu'),
            dict(displayName='Changed', icon='unknown'), dict(theme='dark'), dict(userId='someone-else'),
        ]
        invalid_settings = [
            {}, dict(theme='unknown'), dict(calendarView='year'), dict(reducedMotion='yes'),
            dict(reducedMotion='TRUE'), dict(reducedMotion='1'), dict(reducedMotion=''),
            dict(theme='pastel', calendarView='year'), dict(displayName='Changed'), dict(userId='someone-else'),
        ]
        for path, cases, expected in ((PROFILE, invalid_profiles, profile), (SETTINGS, invalid_settings, settings)):
            for fields in cases:
                with self.subTest(path=path, fields=fields):
                    self.assertEqual(self.request(alice, path, 'PATCH', fields)[0], 400)
                    self.assertEqual(self.get(alice, path), expected)

    def test_request_validation_and_csrf_protection(self):
        alice = self.client()
        self.register(alice, 'alice@example.com')
        for path, fields in ((PROFILE, dict(displayName='Alice')), (SETTINGS, dict(theme='dark'))):
            with self.subTest(path=path):
                self.assertEqual(self.request(alice, path, 'PATCH', fields, verified=False)[0], 403)
                self.assertEqual(self.request(alice, path, 'PATCH', fields,
                                             headers={'Sec-Fetch-Site': 'cross-site'})[0], 403)
                self.assertEqual(self.request(alice, path, 'PATCH', fields,
                                             headers={'Content-Type': 'application/json'})[0], 415)
                self.assertEqual(self.request(alice, path, 'PATCH', {'huge': 'x' * 66000})[0], 413)
                self.assertEqual(self.request(alice, path + '?ignored=1', 'PATCH', fields)[0], 400)
                for method in ('POST', 'PUT', 'DELETE'):
                    status, _, headers = self.request(alice, path, method, fields)
                    self.assertEqual(status, 405)
                    self.assertEqual({m.strip() for m in headers['Allow'].split(',')}, {'GET', 'PATCH'})
        self.assertEqual(self.get(alice, PROFILE), DEFAULT_PROFILE)
        self.assertEqual(self.get(alice, SETTINGS), DEFAULT_SETTINGS)

    def test_corrupt_storage_is_not_overwritten_and_other_record_still_works(self):
        alice = self.client()
        account, _ = self.register(alice, 'alice@example.com')
        profile = self.patch(alice, PROFILE, displayName='Alice')
        settings = self.patch(alice, SETTINGS, theme='dark')
        directory = self.account_directory(account)
        for path, filename, fields, other_path, other_expected in (
            (PROFILE, 'profile.properties', dict(displayName='Changed'), SETTINGS, settings),
            (SETTINGS, 'settings.properties', dict(theme='pastel'), PROFILE, profile),
        ):
            with self.subTest(path=path):
                storage = directory / filename
                original = storage.read_bytes()
                damaged = 'broken record\nversion=unsupported\n'
                try:
                    storage.write_text(damaged, encoding='utf-8')
                    self.assertEqual(self.request(alice, path)[0], 500)
                    self.assertEqual(self.request(alice, path, 'PATCH', fields)[0], 500)
                    self.assertEqual(storage.read_text(encoding='utf-8'), damaged)
                    self.assertEqual(self.get(alice, other_path), other_expected)
                    self.assertEqual(list(directory.glob('*.tmp')), [])
                finally:
                    storage.write_bytes(original)

    def test_storage_failure_does_not_report_success_or_cache_unsaved_values(self):
        alice = self.client()
        account, _ = self.register(alice, 'alice@example.com')
        directory = self.account_directory(account)
        self.assertEqual(self.get(alice, PROFILE), DEFAULT_PROFILE)
        self.assertEqual(self.get(alice, SETTINGS), DEFAULT_SETTINGS)
        directory.parent.mkdir(parents=True, exist_ok=True)
        directory.write_text('A file blocks this account storage directory', encoding='utf-8')
        try:
            self.assertEqual(self.request(alice, PROFILE, 'PATCH', dict(displayName='Alice'))[0], 500)
            self.assertEqual(self.request(alice, SETTINGS, 'PATCH', dict(theme='dark'))[0], 500)
            self.assertEqual(directory.read_text(encoding='utf-8'),
                             'A file blocks this account storage directory')
            self.assertEqual(list(directory.parent.rglob('*.tmp')), [])
        finally:
            directory.unlink()
        self.assertEqual(self.get(alice, PROFILE), DEFAULT_PROFILE)
        self.assertEqual(self.get(alice, SETTINGS), DEFAULT_SETTINGS)
        self.assertFalse(directory.exists())


if __name__ == '__main__':
    unittest.main()
