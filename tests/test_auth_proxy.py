"""Verify Vite replaces untrusted client-address headers before the API sees them."""
import os
from pathlib import Path
import socket
import subprocess
import time
import unittest
from urllib.error import URLError
from urllib.request import urlopen
import test_auth_api as auth


class AuthProxyTest(unittest.TestCase):
    setUp = auth.AuthApiTest.setUp
    tearDown = auth.AuthApiTest.tearDown
    start = auth.AuthApiTest.start
    stop = auth.AuthApiTest.stop
    client = auth.AuthApiTest.client
    request = auth.AuthApiTest.request

    def test_forwarded_header_cannot_bypass_client_limit(self):
        root = Path(__file__).resolve().parents[1]
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        vite = subprocess.Popen(
            ['node', 'node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--port', str(port), '--strictPort'],
            cwd=root / 'frontend', env={**os.environ, 'PANNED_OUT_API_TARGET': self.url},
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            self.url = f'http://127.0.0.1:{port}'
            for _ in range(100):
                if vite.poll() is not None:
                    self.fail('Vite exited before becoming ready')
                try:
                    with urlopen(self.url, timeout=1):
                        break
                except (URLError, OSError):
                    time.sleep(0.1)
            else:
                self.fail('Vite did not become ready')
            client = self.client()
            fields = dict(email='invalid', password='')
            for index in range(20):
                self.assertEqual(self.request(client, '/api/auth/login', 'POST', fields,
                                              headers={'X-Forwarded-For': f'192.0.2.{index + 1}'})[0], 400)
            # Changing spoofed addresses cannot evade the real source's limit.
            self.assertEqual(self.request(client, '/api/auth/login', 'POST', fields,
                                          headers={'X-Forwarded-For': '203.0.113.1'})[0], 429)
            # A different email behind the same proxy is not blocked.
            self.assertEqual(self.request(client, '/api/auth/login', 'POST', dict(email='other-invalid', password=''))[0], 400)
        finally:
            vite.terminate()
            vite.wait(timeout=10)
