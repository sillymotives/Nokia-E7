import importlib.util
import base64
import socket
import threading
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / 'host' / 'e7_bridge.py'
spec = importlib.util.spec_from_file_location('e7_bridge', SOURCE)
e7 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e7)


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.server, self.client = socket.socketpair()
        self.addCleanup(self.server.close)
        self.addCleanup(self.client.close)
        self.server.settimeout(1)
        self.client.settimeout(1)
        self.secret = '0123456789abcdef'

    def fake_device(self, secret=None):
        secret = secret or self.secret
        challenge = e7.recv_line(self.client)
        prefix, action, nonce = challenge.split(' ')
        self.assertEqual((prefix, action), ('E7B1', 'CHALLENGE'))
        e7.send_line(self.client, 'E7B1 AUTH ' + e7.expected_auth(secret, 'device:' + nonce))
        return nonce

    def test_mutual_auth_and_ping(self):
        def device():
            nonce = self.fake_device()
            ready = e7.recv_line(self.client)
            self.assertEqual(ready, 'E7B1 READY ' + e7.expected_auth(self.secret, 'host:' + nonce))
            self.assertEqual(e7.recv_line(self.client), 'PING')
            e7.send_line(self.client, 'OK PONG')
            self.assertEqual(e7.recv_line(self.client), 'DRIVES')
            e7.send_line(self.client, 'B64 ' + base64.b64encode('[D] E:/\n[D] C:/Data'.encode()).decode())
            self.assertEqual(e7.recv_line(self.client), 'LIST E:/')
            e7.send_line(self.client, 'B64 ' + base64.b64encode('[D] Images\n[F] test.txt'.encode()).decode())

        thread = threading.Thread(target=device)
        thread.start()
        e7.authenticate(self.server, self.secret)
        self.assertEqual(e7.request(self.server, 'PING'), 'PONG')
        self.assertEqual(e7.request(self.server, 'DRIVES'), '[D] E:/\n[D] C:/Data')
        self.assertEqual(e7.request(self.server, 'LIST E:/'), '[D] Images\n[F] test.txt')
        thread.join(1)
        self.assertFalse(thread.is_alive())

    def test_bad_key_rejected(self):
        thread = threading.Thread(target=lambda: self.fake_device('eeeeeeeeeeeeeeee'))
        thread.start()
        with self.assertRaisesRegex(e7.BridgeError, 'authentication failed'):
            e7.authenticate(self.server, self.secret)
        thread.join(1)

    def test_no_arbitrary_commands(self):
        self.assertEqual(e7.normalize_command('ls'), 'LIST E:/')
        self.assertEqual(e7.normalize_command('info'), 'INFO')
        self.assertEqual(e7.normalize_command('drives'), 'DRIVES')
        self.assertEqual(e7.normalize_command('stat E:/Images'), 'STAT E:/Images')
        with self.assertRaises(e7.BridgeError):
            e7.normalize_command('stat')
        with self.assertRaises(e7.BridgeError):
            e7.normalize_command('exec rm -rf C:/')
        with self.assertRaises(e7.BridgeError):
            e7.normalize_command('flash')


if __name__ == '__main__':
    unittest.main()
