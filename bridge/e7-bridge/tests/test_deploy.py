"""Unit tests for the v0.7 deploy pilot; simulated phone, not device install."""
import hashlib
import importlib.util
from pathlib import Path
import socket
import tempfile
import unittest

from test_admin import FakeAdminPhone

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('e7_bridge', ROOT / 'host' / 'e7_bridge.py')
e7 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e7)


class InstallPilotTests(unittest.TestCase):
    def setUp(self):
        self.host, self.phone = socket.socketpair()
        self.addCleanup(self.host.close)
        self.addCleanup(self.phone.close)
        self.host.settimeout(2.0)
        self.phone.settimeout(2.0)
        self.key = '0123456789abcdef'
        self.nonce = 'b' * 32
        self.fake = FakeAdminPhone(self.phone, self.key, self.nonce)
        self.fake.thread.start()
        self.admin = e7.AdminSession(self.host, self.key, self.nonce)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def source(self, name='E7DeployProbe-v0.1.0.sis', payload=b'SIS simulation fixture'):
        path = Path(self.temp.name) / name
        path.write_bytes(payload)
        return path

    def test_deploy_stages_and_requests_open(self):
        path = self.source(payload=b'nonsecret-fixture\x00' * 400)
        remote, size, sha = e7.deploy_package(self.admin, str(path))
        self.assertEqual(remote, 'E:/Installs/' + path.name)
        self.assertEqual(size, path.stat().st_size)
        self.assertEqual(sha, hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(self.fake.files[remote], path.read_bytes())
        self.assertEqual(self.fake.launch_requests, [remote])
        self.assertEqual(self.fake.errors, [])

    def test_sisx_supported(self):
        path = self.source('Pilot-v2.sisx', b'fake-sisx')
        self.assertEqual(e7.deploy_package(self.admin, path)[0], 'E:/Installs/Pilot-v2.sisx')
        self.assertEqual(self.fake.launch_requests, ['E:/Installs/Pilot-v2.sisx'])

    def test_deploy_rejects_wrong_extension_before_io(self):
        path = self.source('untrusted.txt', b'not a sis')
        with self.assertRaisesRegex(e7.BridgeError, 'Only .sis'):
            e7.deploy_package(self.admin, path)
        self.assertEqual(self.admin.seq, 0)

    def test_deploy_refuses_running_bridge_upgrade(self):
        path = self.source('E7Bridge-v0.7.1.sis', b'future')
        with self.assertRaisesRegex(e7.BridgeError, 'self-upgrade'):
            e7.deploy_package(self.admin, path)
        self.assertEqual(self.admin.seq, 0)

    def test_deploy_refuses_zero_length(self):
        path = self.source('Empty.sis', b'')
        with self.assertRaisesRegex(e7.BridgeError, '1 byte'):
            e7.deploy_package(self.admin, path)
        self.assertEqual(self.admin.seq, 0)

    def test_deploy_refuses_nonexistent_and_symlink(self):
        with self.assertRaisesRegex(e7.BridgeError, 'regular non-symlink'):
            e7.deploy_package(self.admin, Path(self.temp.name) / 'missing.sis')
        file = self.source('real.sis', b'bytes')
        link = Path(self.temp.name) / 'alias.sis'
        link.symlink_to(file)
        with self.assertRaisesRegex(e7.BridgeError, 'regular non-symlink'):
            e7.deploy_package(self.admin, link)
        self.assertEqual(self.admin.seq, 0)

    def test_deploy_refuses_oversized(self):
        path = self.source('Huge.sis', b'')
        with path.open('wb') as f:
            f.truncate(e7.ADMIN_MAX_BYTES + 1)
        with self.assertRaisesRegex(e7.BridgeError, '8 MiB'):
            e7.deploy_package(self.admin, path)
        self.assertEqual(self.admin.seq, 0)

    def test_missing_staged_package_fails_without_open(self):
        sha = hashlib.sha256(b'text').hexdigest()
        with self.assertRaisesRegex(e7.BridgeError, 'PACKAGE_HASH_MISMATCH'):
            self.admin.send('LAUNCH missing.sis 4 ' + sha)
        self.assertEqual(self.fake.launch_requests, [])

    def test_changed_staged_package_fails_without_open(self):
        path = self.source('Altered.sis', b'first')
        remote, size, sha = e7.push_file(self.admin, path, 'installs')
        self.fake.files[remote] = b'second'
        with self.assertRaisesRegex(e7.BridgeError, 'PACKAGE_HASH_MISMATCH'):
            self.admin.send('LAUNCH Altered.sis {} {}'.format(size, sha))
        self.assertEqual(self.fake.launch_requests, [])

    def test_invalid_hash_fails_without_open(self):
        path = self.source('Hash.sis', b'file')
        remote, size, sha = e7.push_file(self.admin, path, 'installs')
        with self.assertRaisesRegex(e7.BridgeError, 'PACKAGE_HASH_MISMATCH'):
            self.admin.send('LAUNCH Hash.sis {} {}'.format(size, '0' * 64))
        self.assertEqual(self.fake.launch_requests, [])

    def test_no_overwrite_and_no_second_launch(self):
        path = self.source('Repeat.sis', b'original')
        remote, _, _ = e7.deploy_package(self.admin, path)
        path.write_bytes(b'revised')
        with self.assertRaisesRegex(e7.BridgeError, 'EXISTS'):
            e7.deploy_package(self.admin, path)
        self.assertEqual(self.fake.files[remote], b'original')
        self.assertEqual(self.fake.launch_requests, [remote])

    def test_normalise_deploy_and_reject_command_injection(self):
        self.assertEqual(e7.normalize_command('deploy ./foo.sis'), 'DEPLOY ./foo.sis')
        with self.assertRaises(e7.BridgeError):
            e7.normalize_command('deploy foo.sis\nQUIT')

    def test_implementation_scoped_to_staged_package(self):
        cpp = (ROOT / 'phone' / 'main.cpp').read_text()
        pro = (ROOT / 'phone' / 'e7bridge.pro').read_text()
        host = (ROOT / 'host' / 'e7_bridge.py').read_text()
        self.assertIn('items[0] == "LAUNCH"', cpp)
        self.assertIn('void launchInstaller(', cpp)
        self.assertIn('QDesktopServices::openUrl(QUrl::fromLocalFile(path))', cpp)
        self.assertIn('E:/Installs', cpp)
        self.assertIn('info.canonicalFilePath().compare(path', cpp)
        self.assertIn('info.size() != expectedSize', cpp)
        self.assertIn('actual != items[3]', cpp)
        self.assertIn('QIODevice::ReadOnly', cpp)
        self.assertIn('adminReply(seq, "OK LAUNCH_REQUESTED")', cpp)
        self.assertIn('admin.send(\'LAUNCH {} {} {}\'', host)
        self.assertIn('Pilot deploy refuses an E7 Bridge self-upgrade', host)
        self.assertNotIn('QProcess', cpp)
        self.assertNotIn('C:/sys/bin', cpp)
        self.assertIn('TARGET.CAPABILITY = NetworkServices ReadUserData WriteUserData', pro)
        cap = next(line for line in pro.splitlines() if line.strip().startswith('TARGET.CAPABILITY ='))
        self.assertNotIn('TCB', cap)
        self.assertNotIn('AllFiles', cap)

    def test_disposable_probe_pkg_has_no_executable(self):
        script = (ROOT / 'build' / 'in-container-probe.sh').read_text()
        self.assertIn('0xE94B7002', script)
        self.assertIn('E7DeployProbe', script)
        self.assertIn('C:\\\\data\\\\E7DeployProbe\\\\probe.txt', script)
        self.assertNotIn('\\\\sys\\\\bin\\\\', script)
        self.assertNotIn('E7Bridge.exe', script)


if __name__ == '__main__':
    unittest.main()
