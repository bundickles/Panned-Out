"""Photo integration tests using real Java HTTP and local demo/fake responses.

Run: python -m unittest discover -s tests -p test_photo_recipe_api.py -v
Java sources and the test harness compile into a temporary directory. No API key,
external provider request, real food photo, or third-party Python package is used.
These tests verify transport/validation behavior, not live food recognition quality.
"""
import base64
from concurrent.futures import ThreadPoolExecutor
import http.client
import http.cookiejar
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import queue
import struct
import subprocess
import tempfile
import threading
import time
import unittest
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPCookieProcessor, ProxyHandler, Request, build_opener
import zlib


ROOT = Path(__file__).resolve().parents[1]
PHOTO_PATH = '/api/ai/recipe-from-photo'
PASSWORD = 'photo transport test password'
MODEL_RECIPE = dict(status='recipe', name='Rice', ingredients='1 cup rice\n2 cups water',
                    instructions='Bring water to a boil.\nAdd rice and simmer.')


def png(width=3, height=2, color=(220, 170, 90)):
    """A genuine, decodable RGB PNG made with only the standard library."""
    def chunk(kind, data):
        return (struct.pack('!I', len(data)) + kind + data
                + struct.pack('!I', zlib.crc32(kind + data) & 0xffffffff))
    compressor = zlib.compressobj()
    row = b'\x00' + bytes(color) * width
    compressed = b''.join(compressor.compress(row) for _ in range(height)) + compressor.flush()
    return (b'\x89PNG\r\n\x1a\n'
            + chunk(b'IHDR', struct.pack('!IIBBBBB', width, height, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', compressed) + chunk(b'IEND', b''))


PNG = png()


def model_response(value=None):
    return dict(status='completed', output=[dict(type='message', content=[
        dict(type='output_text', text=json.dumps(MODEL_RECIPE if value is None else value))])])


class FakeProvider:
    """A loopback Responses endpoint with queued replies and captured requests."""
    def __init__(self):
        self.replies = queue.Queue()
        self.requests = []
        self.changed = threading.Condition()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                raw = self.rfile.read(int(self.headers.get('Content-Length', '0')))
                with owner.changed:
                    owner.requests.append(dict(path=self.path,
                                               headers=dict(self.headers.items()), raw=raw))
                    owner.changed.notify_all()
                try:
                    reply = owner.replies.get_nowait()
                except queue.Empty:
                    reply = dict(status=200, body=model_response())
                gate = reply.get('gate')
                if gate is not None:
                    gate.wait(timeout=10)
                if reply.get('delay'):
                    time.sleep(reply['delay'])
                body = reply['body']
                if not isinstance(body, bytes):
                    body = json.dumps(body).encode('utf-8')
                try:
                    self.send_response(reply['status'])
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', str(len(body)))
                    self.end_headers()
                    if reply.get('body_delay'):
                        self.wfile.flush()
                        time.sleep(reply['body_delay'])
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    pass  # Expected when the Java client times out.

            def log_message(self, *_args):
                pass

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = 'http://127.0.0.1:%d/v1/responses' % self.server.server_port

    def enqueue(self, body=None, status=200, **options):
        self.replies.put(dict(body=model_response() if body is None else body,
                             status=status, **options))

    def wait_for_requests(self, count, timeout=5):
        with self.changed:
            return self.changed.wait_for(lambda: len(self.requests) >= count, timeout)

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


class PhotoRecipeApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.build_directory = tempfile.TemporaryDirectory(prefix='photo-api-build-')
        cls.addClassCleanup(cls.build_directory.cleanup)
        cls.classpath = Path(cls.build_directory.name)
        sources = sorted((ROOT / 'backend/src').glob('*.java'))
        sources.append(ROOT / 'backend/tests/PhotoRecipeTestServer.java')
        result = subprocess.run(['javac', '--release', '11', '-d', str(cls.classpath)]
                                + [str(path.relative_to(ROOT)) for path in sources],
                                capture_output=True, text=True, cwd=ROOT)
        if result.returncode:
            raise AssertionError('Java compilation failed:\n' + result.stdout + result.stderr)
        jpeg_path = cls.classpath / 'test-image.jpg'
        subprocess.run(['java', '-cp', str(cls.classpath), 'PhotoRecipeTestServer',
                        '--write-test-jpeg', str(jpeg_path)], check=True,
                       capture_output=True, text=True)
        cls.jpeg = jpeg_path.read_bytes()

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='photo-api-data-')
        self.addCleanup(self.directory.cleanup)
        self.storage = Path(self.directory.name) / 'recipes.properties'
        self.provider = FakeProvider()
        self.addCleanup(self.provider.close)
        self.process = None
        self.addCleanup(self.stop)
        self.user_count = 0
        self.start()
        self.alice, self.alice_email = self.register_user()

    @staticmethod
    def environment(configured=None):
        environment = dict(os.environ)
        # Keep execution independent of the developer's provider and catalog settings.
        for setting in ('OPENAI_API_KEY', 'PANNED_OUT_AI_MODEL', 'PANNED_OUT_AI_MODE',
                        'PANNED_OUT_AI_DEMO_RESULT'):
            environment.pop(setting, None)
        environment['PANNED_OUT_SUGGESTED_RECIPES'] = str(
            ROOT / 'backend/catalog/suggested-recipes.properties')
        environment['PANNED_OUT_SECURE_COOKIES'] = 'false'
        environment.update(configured or {})
        return environment

    def start(self, key='photo-test-key', timeout_ms=5000, configured=None):
        arguments = (['--configured'] if configured is not None
                     else [self.provider.url, key, str(timeout_ms)])
        self.log = (Path(self.directory.name) / 'server.log').open('a', encoding='utf-8')
        self.process = subprocess.Popen(
            ['java', '-cp', str(self.classpath), 'PhotoRecipeTestServer',
             str(self.storage), *arguments],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.log,
            text=True, cwd=ROOT, env=self.environment(configured))
        line = self.process.stdout.readline().strip()
        self.assertTrue(line.startswith('Recipe API: '), line)
        self.url = line.split('Recipe API: ', 1)[1]

    def stop(self):
        if self.process is not None:
            if self.process.poll() is None:
                self.process.communicate(input='\n', timeout=5)
            else:
                self.process.communicate(timeout=5)
            self.process = None
            self.log.close()

    @staticmethod
    def client():
        return build_opener(ProxyHandler({}), HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def request(self, client, path='/api/recipes', method='GET', fields=None,
                body=None, content_type=None, verified=True, headers=None, timeout=10):
        request_headers = {'X-Panned-Out-Request': '1'} if verified else {}
        request_headers.update(headers or {})
        if fields is not None:
            body = urlencode(fields).encode('utf-8')
            content_type = 'application/x-www-form-urlencoded'
        if content_type is not None:
            request_headers['Content-Type'] = content_type
        request = Request(self.url + path, data=body, method=method, headers=request_headers)
        try:
            response = client.open(request, timeout=timeout)
        except HTTPError as error:
            response = error
        with response:
            return response.status, json.load(response), response.headers

    def photo(self, client=None, image=PNG, content_type='image/png', **options):
        return self.request(client or self.alice, PHOTO_PATH, 'POST', body=image,
                            content_type=content_type, **options)

    def register_user(self):
        self.user_count += 1
        email = 'photo-user-%d@example.com' % self.user_count
        client = self.client()
        status, account, _ = self.request(client, '/api/auth/register', 'POST',
                                          fields=dict(email=email, password=PASSWORD))
        self.assertEqual(status, 201, account)
        return client, email

    def login(self, client, email):
        result = self.request(client, '/api/auth/login', 'POST',
                              fields=dict(email=email, password=PASSWORD))
        self.assertEqual(result[0], 200, result[1])

    def save_recipe(self, client, name):
        status, saved, _ = self.request(client, method='POST', fields=dict(
            name=name, ingredients='Private ingredients', instructions='Private instructions',
            category='My Recipes', difficulty='Easy', mealType='Dinner'))
        self.assertEqual(status, 201, saved)
        return saved

    def persisted_files(self):
        accounts = Path(str(self.storage) + '.accounts')
        return {str(path.relative_to(accounts)): path.read_bytes()
                for path in accounts.rglob('*') if path.is_file()}

    def assert_error(self, result, expected):
        self.assertEqual(result[0], expected, result[1])
        self.assertIsInstance(result[1].get('error'), str)
        self.assertTrue(result[1]['error'])
        self.assertNotIn('photo-test-key', json.dumps(result[1]))
        self.assertNotIn('secret-provider-detail', json.dumps(result[1]))

    def test_success_sends_image_and_strict_schema_without_account_data(self):
        status, result, _ = self.photo()
        self.assertEqual(status, 200, result)
        self.assertEqual(result, dict(status='recipe', recipe={
            key: MODEL_RECIPE[key] for key in ('name', 'ingredients', 'instructions')}))
        self.assertEqual(len(self.provider.requests), 1)
        outgoing = self.provider.requests[0]
        headers = {key.lower(): value for key, value in outgoing['headers'].items()}
        self.assertEqual(outgoing['path'], '/v1/responses')
        self.assertEqual(headers['authorization'], 'Bearer photo-test-key')
        self.assertIn('application/json', headers['content-type'])
        self.assertNotIn('cookie', headers)
        self.assertNotIn('x-panned-out-request', headers)
        raw = outgoing['raw'].decode('utf-8')
        for private_value in (self.alice_email, PASSWORD, 'panned_session'):
            self.assertNotIn(private_value, raw)
        payload = json.loads(raw)
        self.assertEqual(payload['model'], 'test-vision-model')
        self.assertIs(payload['store'], False)
        images = [part for item in payload['input'] for part in item.get('content', [])
                  if isinstance(part, dict) and part.get('type') == 'input_image']
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0]['image_url'],
                         'data:image/png;base64,' + base64.b64encode(PNG).decode('ascii'))
        output_format = payload['text']['format']
        self.assertEqual(output_format['type'], 'json_schema')
        self.assertIs(output_format['strict'], True)
        schema = output_format['schema']
        self.assertEqual(schema['type'], 'object')
        self.assertIs(schema['additionalProperties'], False)
        self.assertEqual(set(schema['required']), {'status', 'name', 'ingredients', 'instructions'})

    def test_preview_never_saves_upload_or_recipe_for_either_account_or_restart(self):
        bob, bob_email = self.register_user()
        alice_saved = self.save_recipe(self.alice, 'Alice private recipe')
        bob_saved = self.save_recipe(bob, 'Bob private recipe')
        before = self.persisted_files()
        first = self.photo()[1]
        self.provider.enqueue(model_response({**MODEL_RECIPE, 'name': 'Second preview'}))
        second = self.photo(bob)[1]
        self.assertEqual(first['recipe']['name'], 'Rice')
        self.assertEqual(second['recipe']['name'], 'Second preview')
        self.assertEqual(self.request(self.alice)[1], [alice_saved])
        self.assertEqual(self.request(bob)[1], [bob_saved])
        self.assertEqual(self.persisted_files(), before)
        self.assertFalse(self.storage.exists())
        self.stop()
        self.start()
        self.login(self.alice, self.alice_email)
        self.login(bob, bob_email)
        self.assertEqual(self.request(self.alice)[1], [alice_saved])
        self.assertEqual(self.request(bob)[1], [bob_saved])
        self.assertEqual(self.persisted_files(), before)

    def test_valid_jpeg_reaches_model_with_matching_data_url(self):
        status, result, _ = self.photo(image=self.jpeg, content_type='image/jpeg')
        self.assertEqual(status, 200, result)
        self.assertEqual(result['recipe']['name'], 'Rice')
        payload = json.loads(self.provider.requests[0]['raw'])
        images = [part for item in payload['input'] for part in item.get('content', [])
                  if isinstance(part, dict) and part.get('type') == 'input_image']
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0]['image_url'],
                         'data:image/jpeg;base64,' + base64.b64encode(self.jpeg).decode('ascii'))

    def test_empty_account_stays_empty_after_preview_and_restart(self):
        before = self.persisted_files()
        self.assertEqual(self.photo()[0], 200)
        self.assertEqual(self.request(self.alice)[1], [])
        self.assertEqual(self.persisted_files(), before)
        self.stop()
        self.start()
        self.login(self.alice, self.alice_email)
        self.assertEqual(self.request(self.alice)[1], [])
        self.assertFalse(any(Path(str(self.storage) + '.accounts').glob('users/*/recipes.properties')))

    def test_fake_nonfood_result_and_provider_refusal_are_clear_no_results(self):
        # This solid blue fixture does not test whether a real vision model recognizes food.
        self.provider.enqueue(model_response(dict(status='no_result', name='',
                                                   ingredients='', instructions='')))
        self.provider.enqueue(dict(status='completed', output=[dict(type='message', content=[
            dict(type='refusal', refusal='Model declined the test request.')])]))
        for _ in range(2):
            status, result, _ = self.photo(image=png(color=(10, 40, 210)))
            self.assertEqual(status, 200, result)
            self.assertEqual(result['status'], 'no_result')
            self.assertIsNone(result['recipe'])
            self.assertTrue(result['message'])
        self.assertEqual(self.request(self.alice)[1], [])

    def test_session_and_request_verification_are_required_before_provider_call(self):
        self.assert_error(self.photo(self.client()), 401)
        self.assert_error(self.photo(verified=False), 403)
        self.assert_error(self.photo(headers={'Sec-Fetch-Site': 'cross-site'}), 403)
        self.assertEqual(self.provider.requests, [])

    def test_wrong_methods_are_rejected_before_provider_call(self):
        for method in ('GET', 'PUT', 'DELETE'):
            with self.subTest(method=method):
                result = self.request(self.alice, PHOTO_PATH, method)
                self.assert_error(result, 405)
                self.assertEqual(result[2]['Allow'], 'POST')
        self.assertEqual(self.provider.requests, [])

    def test_invalid_uploads_do_not_reach_provider(self):
        cases = [
            ('empty', b'', 'image/png', 400),
            ('not an image', b'not a photograph', 'image/png', 400),
            ('truncated PNG', PNG[:45], 'image/png', 400),
            ('wrong MIME', PNG, 'image/gif', 415),
            ('MIME mismatch', PNG, 'image/jpeg', 415),
            ('too many bytes', PNG + b'\x00' * (5 * 1024 * 1024), 'image/png', 413),
            ('too wide', png(8193, 1), 'image/png', 413),
            ('too many pixels', png(5000, 4000), 'image/png', 413),
        ]
        for label, image, content_type, expected in cases:
            with self.subTest(case=label):
                self.assert_error(self.photo(image=image, content_type=content_type), expected)
        self.assert_error(self.photo(headers={'Content-Encoding': 'gzip'}), 415)
        self.assertEqual(self.provider.requests, [])
        # Invalid uploads do not consume the account's model-call allowance.
        self.assertEqual(self.photo()[0], 200)
        self.assertEqual(len(self.provider.requests), 1)

    def test_missing_content_type_is_rejected(self):
        # urllib adds a form MIME type automatically; use raw HTTP to omit it entirely.
        cookie_request = Request(self.url + PHOTO_PATH)
        for handler in self.alice.handlers:
            if isinstance(handler, HTTPCookieProcessor):
                handler.cookiejar.add_cookie_header(cookie_request)
        endpoint = urlsplit(self.url)
        connection = http.client.HTTPConnection(endpoint.hostname, endpoint.port, timeout=5)
        try:
            connection.request('POST', PHOTO_PATH, body=PNG, headers={
                'X-Panned-Out-Request': '1', 'Cookie': cookie_request.get_header('Cookie')})
            response = connection.getresponse()
            self.assertEqual(response.status, 415)
            self.assertIn('error', json.loads(response.read()))
        finally:
            connection.close()
        self.assertEqual(self.provider.requests, [])

    def test_malformed_or_incomplete_provider_output_never_becomes_a_recipe(self):
        missing_field = {key: value for key, value in MODEL_RECIPE.items() if key != 'instructions'}
        cases = [b'not JSON', dict(status='completed', output=[]),
                 {**model_response(), 'status': 'incomplete'}, model_response(missing_field),
                 model_response({**MODEL_RECIPE, 'ingredients': ['rice']}),
                 model_response({**MODEL_RECIPE, 'name': ''})]
        for body in cases:
            with self.subTest(body=body):
                self.provider.enqueue(body)
                self.assert_error(self.photo(), 502)
        self.assertEqual(len(self.provider.requests), len(cases))
        self.assertEqual(self.request(self.alice)[1], [])

    def test_provider_errors_are_translated_without_leaking_provider_details(self):
        for provider_status, expected in ((500, 502), (429, 503), (401, 503), (403, 503)):
            with self.subTest(provider_status=provider_status):
                self.provider.enqueue(dict(error=dict(message='secret-provider-detail')),
                                      status=provider_status)
                self.assert_error(self.photo(), expected)
        self.assertEqual(self.request(self.alice)[0], 200)

    def test_provider_timeout_returns_504_and_releases_request_slot(self):
        self.stop()
        self.start(timeout_ms=350)
        self.login(self.alice, self.alice_email)
        self.provider.enqueue(delay=1.0)
        self.assert_error(self.photo(), 504)
        self.assertTrue(self.provider.wait_for_requests(1))
        self.assertEqual(self.request(self.alice)[0], 200)
        self.assertEqual(self.photo()[0], 200)

    def test_provider_response_body_is_covered_by_total_deadline(self):
        self.stop()
        self.start(timeout_ms=350)
        self.login(self.alice, self.alice_email)
        # Headers arrive immediately, then the body stalls beyond the deadline.
        self.provider.enqueue(body_delay=1.0)
        self.assert_error(self.photo(), 504)
        self.assertTrue(self.provider.wait_for_requests(1))
        self.assertEqual(self.request(self.alice)[0], 200)
        self.assertEqual(self.photo()[0], 200)

    def test_provider_response_size_and_strict_json_are_bounded(self):
        valid = json.dumps(model_response()).encode('utf-8')
        duplicate = valid.replace(b'{"status":', b'{"status":"completed","status":', 1)
        for body in (b' ' * (256 * 1024 + 1), valid + b' {}', duplicate):
            with self.subTest(length=len(body), prefix=body[:60]):
                self.provider.enqueue(body)
                self.assert_error(self.photo(), 502)
        self.assertEqual(self.request(self.alice)[1], [])

    def test_missing_key_disables_only_photo_generation(self):
        self.stop()
        self.start(key='')
        self.login(self.alice, self.alice_email)
        self.assert_error(self.photo(), 503)
        saved = self.save_recipe(self.alice, 'Ordinary recipes still work')
        self.assertEqual(self.request(self.alice)[1], [saved])
        self.assertEqual(self.request(self.alice, '/api/auth/me')[0], 200)
        self.assertEqual(self.provider.requests, [])

    def test_rate_limit_is_per_account_and_does_not_send_seventh_request(self):
        for _ in range(6):
            self.assertEqual(self.photo()[0], 200)
        limited = self.photo()
        self.assert_error(limited, 429)
        self.assertGreater(int(limited[2]['Retry-After']), 0)
        self.assertEqual(len(self.provider.requests), 6)
        bob, _ = self.register_user()
        self.assertEqual(self.photo(bob)[0], 200)
        self.assertEqual(len(self.provider.requests), 7)
        self.assertEqual(self.request(self.alice)[0], 200)

    def test_two_slow_generations_leave_recipes_responsive_and_reject_third(self):
        bob, _ = self.register_user()
        charlie, _ = self.register_user()
        gate = threading.Event()
        self.provider.enqueue(gate=gate)
        self.provider.enqueue(gate=gate)
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(self.photo, self.alice)
            second = pool.submit(self.photo, bob)
            try:
                self.assertTrue(self.provider.wait_for_requests(2), 'Both model calls must be in flight')
                self.assertEqual(self.request(charlie, timeout=2)[0], 200)
                busy = self.photo(charlie, timeout=2)
                self.assert_error(busy, 429)
                self.assertGreater(int(busy[2]['Retry-After']), 0)
                self.assertEqual(len(self.provider.requests), 2)
                self.assertFalse(first.done())
                self.assertFalse(second.done())
            finally:
                gate.set()
            self.assertEqual(first.result(timeout=5)[0], 200)
            self.assertEqual(second.result(timeout=5)[0], 200)
        self.assertEqual(self.photo(charlie)[0], 200)

    def restart_configured(self, settings=None):
        self.stop()
        self.start(configured={} if settings is None else settings)
        self.login(self.alice, self.alice_email)

    def assert_demo_recipe(self, result):
        status, payload, headers = result
        self.assertEqual(status, 200, payload)
        self.assertEqual(payload['status'], 'recipe')
        self.assertIs(payload['demo'], True)
        self.assertIn('not analyzed', payload['message'].lower())
        self.assertEqual(headers['X-Panned-Out-AI-Mode'], 'demo')
        self.assertEqual(set(payload['recipe']), {'name', 'ingredients', 'instructions'})
        for value in payload['recipe'].values():
            self.assertIsInstance(value, str)
            self.assertTrue(value.strip())
        return payload['recipe']

    def test_default_demo_needs_no_key_and_returns_same_sample_for_different_images(self):
        for settings in ({}, {'PANNED_OUT_AI_MODE': '  '}):
            with self.subTest(settings=settings):
                self.restart_configured(settings)
                first = self.assert_demo_recipe(self.photo())
                different = self.assert_demo_recipe(self.photo(image=png(color=(0, 20, 240))))
                jpeg = self.assert_demo_recipe(self.photo(image=self.jpeg, content_type='image/jpeg'))
                self.assertEqual(first, different)
                self.assertEqual(first, jpeg)
                self.assertEqual(self.request(self.alice)[1], [])
        self.assertEqual(self.provider.requests, [])

    def test_explicit_demo_ignores_key_and_saves_only_after_separate_save_action(self):
        self.restart_configured({'PANNED_OUT_AI_MODE': 'demo',
                                 'OPENAI_API_KEY': 'not-a-real-key-demo-must-ignore',
                                 'PANNED_OUT_AI_MODEL': 'unused-demo-model'})
        bob, _ = self.register_user()
        bob_saved = self.save_recipe(bob, 'Bob private recipe')
        before = self.persisted_files()
        recipe = self.assert_demo_recipe(self.photo())
        self.assertEqual(self.request(self.alice)[1], [])
        self.assertEqual(self.request(bob)[1], [bob_saved])
        self.assertEqual(self.persisted_files(), before)
        self.assertFalse(self.storage.exists())
        status, saved, _ = self.request(self.alice, method='POST', fields={
            **recipe, 'category': 'My Recipes', 'difficulty': 'Easy', 'mealType': 'Dinner'})
        self.assertEqual(status, 201, saved)
        for field, value in recipe.items():
            self.assertEqual(saved[field], value)
        self.assertEqual(self.request(self.alice)[1], [saved])
        self.assertEqual(self.request(bob)[1], [bob_saved])
        self.assertEqual(self.provider.requests, [])

    def test_demo_no_result_and_failure_are_labeled_and_do_not_save(self):
        for scenario in ('no_result', 'error'):
            with self.subTest(scenario=scenario):
                self.restart_configured({'PANNED_OUT_AI_MODE': 'demo',
                                         'PANNED_OUT_AI_DEMO_RESULT': scenario})
                before = self.persisted_files()
                result = self.photo()
                self.assertEqual(result[2]['X-Panned-Out-AI-Mode'], 'demo')
                if scenario == 'no_result':
                    self.assertEqual(result[0], 200, result[1])
                    self.assertEqual(result[1]['status'], 'no_result')
                    self.assertIsNone(result[1]['recipe'])
                    self.assertIs(result[1]['demo'], True)
                    self.assertIn('simulat', result[1]['message'].lower())
                    self.assertIn('not analyzed', result[1]['message'].lower())
                else:
                    self.assert_error(result, 502)
                    self.assertIn('demo', result[1]['error'].lower())
                    self.assertIn('simulat', result[1]['error'].lower())
                self.assertEqual(self.request(self.alice)[1], [])
                self.assertEqual(self.request(self.alice, '/api/auth/me')[0], 200)
                self.assertEqual(self.persisted_files(), before)
        self.assertEqual(self.provider.requests, [])

    def test_demo_still_enforces_authentication_and_image_validation(self):
        self.restart_configured()
        self.assert_error(self.photo(self.client()), 401)
        self.assert_error(self.photo(verified=False), 403)
        self.assert_error(self.photo(headers={'Sec-Fetch-Site': 'cross-site'}), 403)
        for image, mime, status in ((b'', 'image/png', 400),
                                    (b'corrupt', 'image/png', 400),
                                    (PNG, 'image/gif', 415),
                                    (PNG, 'image/jpeg', 415),
                                    (PNG + b'\x00' * (5 * 1024 * 1024), 'image/png', 413)):
            with self.subTest(status=status, mime=mime, length=len(image)):
                self.assert_error(self.photo(image=image, content_type=mime), status)
        self.assert_demo_recipe(self.photo())
        self.assertEqual(self.provider.requests, [])

    def test_demo_retains_account_request_limits(self):
        self.restart_configured()
        for _ in range(6):
            self.assert_demo_recipe(self.photo())
        limited = self.photo()
        self.assert_error(limited, 429)
        self.assertGreater(int(limited[2]['Retry-After']), 0)
        bob, _ = self.register_user()
        self.assert_demo_recipe(self.photo(bob))
        self.assertEqual(self.provider.requests, [])

    def test_invalid_demo_settings_fail_startup_without_falling_back_to_a_provider(self):
        self.stop()
        for settings, invalid_field in (
                ({'PANNED_OUT_AI_MODE': 'typo'}, 'PANNED_OUT_AI_MODE'),
                ({'PANNED_OUT_AI_MODE': 'demo', 'PANNED_OUT_AI_DEMO_RESULT': 'typo'},
                 'PANNED_OUT_AI_DEMO_RESULT')):
            with self.subTest(settings=settings):
                result = subprocess.run(
                    ['java', '-cp', str(self.classpath), 'PhotoRecipeTestServer',
                     str(self.storage), '--configured'],
                    input='\n', capture_output=True, text=True, timeout=5, cwd=ROOT,
                    env=self.environment(settings))
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('Recipe API:', result.stdout)
                self.assertIn(invalid_field, result.stderr)
        self.assertEqual(self.provider.requests, [])

    def test_explicit_openai_mode_without_key_remains_unavailable(self):
        # No key is supplied, so the real client must stop before any network request.
        self.restart_configured({'PANNED_OUT_AI_MODE': 'openai'})
        self.assert_error(self.photo(), 503)
        self.assertEqual(self.request(self.alice)[0], 200)
        self.assertEqual(self.provider.requests, [])


if __name__ == '__main__':
    unittest.main()
