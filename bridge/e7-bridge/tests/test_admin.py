"""v0.6 admin upload protocol: transport-integrity, boundaries and aborts.

The fake Symbian endpoint below is a strict model, not a native runtime test.
"""
import base64
import hashlib
import hmac
import importlib.util
import os
from pathlib import Path
import socket
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('e7_bridge', ROOT / 'host' / 'e7_bridge.py')
e7 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e7)


class FakeAdminPhone:
    def __init__(self, sock, key, nonce):
        self.sock, self.key, self.nonce = sock, key, nonce
        self.seq = 0
        self.current = None
        self.files = {}
        self.errors = []
        self.done = threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=True)

    def mac(self, direction, seq, body):
        return hmac.new(self.key.encode(),
            '{}:{}:{}:{}'.format(direction, self.nonce, seq, body).encode(),
            hashlib.sha256).hexdigest()

    def reply(self, seq, result):
        e7.send_line(self.sock, 'ADMREPLY {} {} {}'.format(
            seq, result, self.mac('reply', seq, result)))

    def run(self):
        try:
            while True:
                line = e7.recv_line(self.sock)
                words = line.split(' ')
                if len(words) < 4 or words[0] != 'ADM':
                    self.errors.append('Malformed admin frame')
                    break
                seq = int(words[1])
                message = ' '.join(words[2:-1])
                if seq != self.seq + 1 or not hmac.compare_digest(words[-1], self.mac('admin', seq, message)):
                    self.errors.append('Invalid MAC or sequence')
                    e7.send_line(self.sock, 'ERR ADMIN_AUTH')
                    break
                self.seq = seq
                parts = message.split(' ')
                if parts[0] == 'BEGIN' and len(parts) == 5:
                    _, bucket, name, size, expected = parts
                    destination = ('E:/Installs/' if bucket == 'installs' else 'E:/KAI/INBOX/') + name
                    if destination in self.files:
                        self.reply(seq, 'ERR EXISTS')
                    elif len(name) > 64 or not name.isascii():
                        self.reply(seq, 'ERR NAME_REJECTED')
                    else:
                        self.current = dict(destination=destination, size=int(size), sha=expected, data=bytearray())
                        self.reply(seq, 'OK READY')
                elif parts[0] == 'CHUNK' and len(parts) == 3 and self.current is not None:
                    offset = int(parts[1])
                    data = base64.b64decode(parts[2], validate=True)
                    if offset != len(self.current['data']):
                        self.reply(seq, 'ERR OFFSET_MISMATCH')
                    else:
                        self.current['data'].extend(data)
                        self.reply(seq, 'OK CHUNK')
                elif message == 'FINISH' and self.current is not None:
                    info = self.current
                    self.current = None
                    data = bytes(info['data'])
                    if len(data) != info['size'] or hashlib.sha256(data).hexdigest() != info['sha']:
                        self.reply(seq, 'ERR HASH_MISMATCH')
                    else:
                        self.files[info['destination']] = data
                        self.reply(seq, 'OK STORED {} {}'.format(len(data), info['sha']))
                elif message == 'CANCEL':
                    self.current = None
                    self.reply(seq, 'OK CANCELLED')
                else:
                    self.reply(seq, 'ERR UNKNOWN')
        except (OSError, e7.BridgeError):
            pass
        finally:
            self.current = None
            self.done.set()


class AdminProtocolTests(unittest.TestCase):
    def setUp(self):
        self.host, self.phone = socket.socketpair()
        self.host.settimeout(2)
        self.phone.settimeout(2)
        self.addCleanup(self.host.close)
        self.addCleanup(self.phone.close)
        self.key = '0123456789abcdef'
        self.nonce = 'c' * 32
        self.client = e7.AdminSession(self.host, self.key, self.nonce)
        self.mock = FakeAdminPhone(self.phone, self.key, self.nonce)
        self.mock.thread.start()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def source(self, name, data):
        path = Path(self.temp.name) / name
        path.write_bytes(data)
        return path

    def test_binary_multichunk_transfer(self):
        payload = bytes(range(256)) * 25 + b'\x00\xff\r\n'
        path = self.source('firmware-test.bin', payload)
        remote, size, digest = e7.push_file(self.client, path)
        self.assertEqual(remote, 'E:/KAI/INBOX/firmware-test.bin')
        self.assertEqual(size, len(payload))
        self.assertEqual(self.mock.files[remote], payload)
        self.assertEqual(digest, hashlib.sha256(payload).hexdigest())
        self.assertEqual(self.client.seq, 6)  # BEGIN + four chunks + FINISH
        self.assertEqual(self.mock.errors, [])

    def test_empty_file_can_be_staged(self):
        path = self.source('empty.txt', b'')
        remote, count, digest = e7.push_file(self.client, path)
        self.assertEqual(count, 0)
        self.assertEqual(digest, hashlib.sha256(b'').hexdigest())
        self.assertEqual(self.mock.files[remote], b'')

    def test_sis_package_staged_without_installing(self):
        payload = b'Synthetic SIS-like payload only; do not install.'
        path = self.source('bridge-0.6.0.sis', payload)
        remote, size, digest = e7.push_file(self.client, path, 'installs')
        self.assertEqual(remote, 'E:/Installs/bridge-0.6.0.sis')
        self.assertEqual(self.mock.files[remote], payload)
        self.assertEqual(digest, hashlib.sha256(payload).hexdigest())

    def test_existing_destination_rejected_without_overwrite(self):
        path = self.source('keep.txt', b'first')
        remote, _, _ = e7.push_file(self.client, path)
        path.write_bytes(b'changed')
        with self.assertRaisesRegex(e7.BridgeError, 'EXISTS'):
            e7.push_file(self.client, path)
        self.assertEqual(self.mock.files[remote], b'first')

    def test_bad_filename_bucket_and_oversize_refuse_before_transfer(self):
        self.assertEqual(e7.validate_push_name('normal.txt', 'inbox'), 'normal.txt')
        for name, bucket in [('..', 'inbox'), ('.foo', 'inbox'),
                             ('my..dat', 'inbox'), ('something.exe', 'installs'),
                             ('a;rm', 'inbox'), ('foo.txt', 'root'),
                             ('a' * 65, 'inbox')]:
            with self.subTest(name=name, bucket=bucket):
                with self.assertRaises(e7.BridgeError):
                    e7.validate_push_name(name, bucket)
        path = self.source('too-large.bin', b'')
        with open(path, 'wb') as file:
            file.truncate(e7.ADMIN_MAX_BYTES + 1)
        with self.assertRaisesRegex(e7.BridgeError, '<=8 MiB'):
            e7.push_file(self.client, path)
        self.assertEqual(self.client.seq, 0)

    def test_local_symlinks_refused(self):
        original = self.source('real.txt', b'yes')
        link = Path(self.temp.name) / 'link.txt'
        link.symlink_to(original)
        with self.assertRaisesRegex(e7.BridgeError, 'non-symlink'):
            e7.push_file(self.client, link)

    def test_wrong_mac_acknowledgement_detected(self):
        self.phone.close()
        self.mock.thread.join(1)
        a, b = socket.socketpair()
        a.settimeout(2)
        self.addCleanup(a.close)
        self.addCleanup(b.close)
        cli = e7.AdminSession(a, self.key, self.nonce)
        def tamper():
            request = e7.recv_line(b)
            seq = request.split(' ')[1]
            e7.send_line(b, 'ADMREPLY {} OK READY {}'.format(seq, '0' * 64))
        thread = threading.Thread(target=tamper, daemon=True)
        thread.start()
        with self.assertRaisesRegex(e7.BridgeError, 'HMAC'):
            cli.send('BEGIN inbox test.txt 0 ' + hashlib.sha256(b'').hexdigest())
        thread.join(1)

    def test_nonce_and_sequence_bind_signature(self):
        body = 'CANCEL'
        sig = self.client._mac('admin', 1, body)
        other = e7.AdminSession(self.host, self.key, 'd'*32)
        self.assertNotEqual(sig, other._mac('admin', 1, body))
        self.assertNotEqual(sig, self.client._mac('admin', 2, body))
        self.assertNotEqual(sig, self.client._mac('reply', 1, body))

    def test_cancel_discards_staged_payload(self):
        sha = hashlib.sha256(b'bad').hexdigest()
        self.assertEqual(self.client.send('BEGIN inbox cancel.txt 3 '+sha), 'READY')
        self.assertEqual(self.client.send('CHUNK 0 '+base64.b64encode(b'bad').decode()), 'CHUNK')
        self.assertEqual(self.client.send('CANCEL'), 'CANCELLED')
        self.assertEqual(self.mock.files, {})
        self.assertIsNone(self.mock.current)

    def test_phone_stops_without_exposed_partial_upload(self):
        sha = hashlib.sha256(b'x'*8192).hexdigest()
        self.assertEqual(self.client.send('BEGIN inbox incomplete.txt 8192 '+sha), 'READY')
        self.assertEqual(self.client.send('CHUNK 0 '+base64.b64encode(b'x'*2048).decode()), 'CHUNK')
        self.host.close()
        self.mock.done.wait(2)
        self.assertIsNone(self.mock.current)
        self.assertEqual(self.mock.files, {})

    def test_source_and_symbian_scope(self):
        cpp = (ROOT / 'phone' / 'main.cpp').read_text()
        pro = (ROOT / 'phone' / 'e7bridge.pro').read_text()
        self.assertIn('NetworkServices ReadUserData WriteUserData', pro)
        capability = next(line for line in pro.splitlines() if line.strip().startswith('TARGET.CAPABILITY ='))
        self.assertNotIn('AllFiles', capability)
        self.assertNotIn('TCB', capability)
        for name in ('handleAdminLine', 'beginUpload', 'uploadChunk', 'finishUpload', 'abortUpload'):
            self.assertIn(name, cpp)
        self.assertIn('QFile::rename(uploadTemp, uploadTarget)', cpp)
        self.assertIn('if (line.startsWith("ADM "))', cpp)
        self.assertIn('adminSequence = seq', cpp)
        self.assertIn('QDir().mkpath(parent)', cpp)
        self.assertIn('E:/KAI/INBOX', cpp)
        self.assertIn('E:/Installs', cpp)
        self.assertNotIn('QProcess', cpp)
        self.assertNotIn('RProperty::Set', cpp)
        self.assertNotIn('HAL::Set', cpp)
        self.assertNotIn('C:/sys/bin', cpp)


if __name__ == '__main__':
    unittest.main()
