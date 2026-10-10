"""Read-only single-fixture transfer tests. No real phone or network needed."""
import base64
import hashlib
import importlib.util
import os
from pathlib import Path
import socket
import stat
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('e7_bridge', ROOT / 'host' / 'e7_bridge.py')
e7 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e7)


class ProbeProtocolTests(unittest.TestCase):
    def setUp(self):
        self.sock, self.fake = socket.socketpair()
        self.sock.settimeout(3)
        self.fake.settimeout(3)
        self.addCleanup(self.sock.close)
        self.addCleanup(self.fake.close)
        self.work = tempfile.TemporaryDirectory()
        self.addCleanup(self.work.cleanup)
        self.directory = Path(self.work.name) / 'received'

    def responder(self, data, claimed_hash=None, size=None, short_chunk=False):
        error = []
        size = len(data) if size is None else size
        claimed_hash = claimed_hash or hashlib.sha256(data).hexdigest()

        def run():
            try:
                while True:
                    command = e7.recv_line(self.fake)
                    if command == 'FILEINFO':
                        info = 'size={}\nsha256={}'.format(size, claimed_hash)
                        e7.send_line(self.fake, 'B64 ' + base64.b64encode(info.encode()).decode())
                    elif command.startswith('FILECHUNK '):
                        offset = int(command.split()[1])
                        chunk = data[offset: offset + e7.PROBE_CHUNK]
                        if short_chunk:
                            chunk = chunk[:-1]
                        e7.send_line(self.fake, 'B64 ' + base64.b64encode(chunk).decode())
                    else:
                        error.append('unexpected request: ' + command)
                        break
            except (OSError, e7.BridgeError):
                pass  # Expected when the client socket is closed.

        t = threading.Thread(target=run, daemon=True)
        t.start()
        return t, error

    def test_complete_binary_multichunk_transaction(self):
        payload = bytes(range(256)) * 10 + b'\x00\xff\r\n'
        thread, errors = self.responder(payload)
        path, size, digest = e7.pull_probe(self.sock, self.directory)
        self.assertEqual(size, len(payload))
        self.assertEqual(path.read_bytes(), payload)
        self.assertEqual(digest, hashlib.sha256(payload).hexdigest())
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.directory.stat().st_mode), 0o700)
        self.assertEqual(list(self.directory.glob('*.part')), [])
        self.assertEqual(errors, [])
        self.assertEqual(path.parent, self.directory)
        self.sock.close()
        thread.join(2)

    def test_empty_file(self):
        thread, errors = self.responder(b'')
        path, size, digest = e7.pull_probe(self.sock, self.directory)
        self.assertEqual(size, 0)
        self.assertEqual(path.read_bytes(), b'')
        self.assertEqual(digest, hashlib.sha256(b'').hexdigest())
        self.assertEqual(errors, [])
        self.sock.close()
        thread.join(2)

    def test_mismatched_hash_discards_partial_output(self):
        self.responder(b'not the claimed content', claimed_hash='0' * 64)
        with self.assertRaisesRegex(e7.BridgeError, 'SHA-256 validation'):
            e7.pull_probe(self.sock, self.directory)
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_short_chunk_discards_partial_output(self):
        self.responder(b'chunk length error', short_chunk=True)
        with self.assertRaisesRegex(e7.BridgeError, 'Wrong chunk length'):
            e7.pull_probe(self.sock, self.directory)
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_disconnection_midstream_removes_part(self):
        payload = b'x' * (e7.PROBE_CHUNK * 2 + 100)
        errors = []

        def device():
            try:
                while True:
                    req = e7.recv_line(self.fake)
                    if req == 'FILEINFO':
                        info = ('size={}\nsha256={}'.format(
                            len(payload), hashlib.sha256(payload).hexdigest()))
                        e7.send_line(self.fake, 'B64 ' + base64.b64encode(info.encode()).decode())
                    elif req == 'FILECHUNK 0':
                        e7.send_line(self.fake, 'B64 ' + base64.b64encode(
                            payload[:e7.PROBE_CHUNK]).decode())
                    elif req == 'FILECHUNK 1024':
                        self.fake.shutdown(socket.SHUT_RDWR)
                        self.fake.close()
                        break
                    else:
                        errors.append(req)
                        break
            except OSError:
                pass

        thread = threading.Thread(target=device, daemon=True)
        thread.start()
        with self.assertRaisesRegex(e7.BridgeError, 'Connection closed'):
            e7.pull_probe(self.sock, self.directory)
        self.assertEqual(list(self.directory.iterdir()), [])
        self.assertEqual(errors, [])
        thread.join(2)

    def test_probe_over_limit_is_rejected_before_host_write(self):
        self.responder(b'', size=65537)
        with self.assertRaisesRegex(e7.BridgeError, '64 KiB limit'):
            e7.pull_probe(self.sock, self.directory)
        self.assertFalse(self.directory.exists())

    def test_maximum_64k_file(self):
        payload = b'K' * 65536
        thread, errors = self.responder(payload)
        path, size, digest = e7.pull_probe(self.sock, self.directory)
        self.assertEqual(size, 65536)
        self.assertEqual(digest, hashlib.sha256(payload).hexdigest())
        self.assertEqual(path.read_bytes(), payload)
        self.assertEqual(errors, [])
        self.sock.close()
        thread.join(2)

    def test_symlink_directory_rejected(self):
        external = Path(self.work.name) / 'other'
        external.mkdir(mode=0o700)
        self.directory.symlink_to(external, target_is_directory=True)
        self.responder(b'ok')
        with self.assertRaisesRegex(e7.BridgeError, 'symlinked'):
            e7.pull_probe(self.sock, self.directory)
        self.assertEqual(list(external.iterdir()), [])

    def test_nonprivate_directory_rejected(self):
        self.directory.mkdir(mode=0o755)
        self.directory.chmod(0o755)
        self.responder(b'ok')
        with self.assertRaisesRegex(e7.BridgeError, 'private'):
            e7.pull_probe(self.sock, self.directory)
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_strict_probe_metadata(self):
        digest = 'a' * 64
        self.assertEqual(e7.parse_probe_info('size=5\nsha256=' + digest), (5, digest))
        for bad in ('size=-1\nsha256=' + digest,
                    'size=5\nsha256=' + 'g' * 64,
                    'size=5\nsha256=' + digest + '\nsource=E:/Private',
                    'size=999999\nsha256=' + digest,
                    'size=5\nsha256=' + digest.upper()):
            with self.subTest(bad=bad[:25]):
                with self.assertRaises(e7.BridgeError):
                    e7.parse_probe_info(bad)

    def test_only_named_fixture_transfer_exposed(self):
        self.assertEqual(e7.normalize_command('pull probe'), 'PULL_PROBE')
        self.assertEqual(e7.normalize_command('PULL PROBE'), 'PULL_PROBE')
        for bad in ('pull', 'pull E:/KAI/INDEX.HTM',
                    'pull E:/private/passwords', 'pull probe C:/',
                    'get E:/KAI/INDEX.HTM', 'send /etc/passwd'):
            with self.subTest(bad=bad):
                with self.assertRaises(e7.BridgeError):
                    e7.normalize_command(bad)

    def test_static_nokia_read_boundary(self):
        cpp = (ROOT / 'phone' / 'main.cpp').read_text()
        self.assertIn('static const char kProbePath[] = "E:/KAI/INDEX.HTM"', cpp)
        self.assertIn('static const qint64 kProbeLimit = 65536', cpp)
        self.assertIn('static const qint64 kProbeChunk = 1024', cpp)
        self.assertIn('if (line == "FILEINFO")', cpp)
        self.assertIn('if (line.startsWith("FILECHUNK "))', cpp)
        self.assertIn('file->open(QIODevice::ReadOnly)', cpp)
        self.assertIn('info.canonicalFilePath()', cpp)
        self.assertIn('e7_sha256_update', cpp)
        self.assertIn('file->open(QIODevice::ReadOnly)', cpp)
        self.assertIn('void beginUpload(', cpp)
        self.assertNotIn('FILEDELETE', cpp)


if __name__ == '__main__':
    unittest.main()
