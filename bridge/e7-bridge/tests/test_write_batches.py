"""Host-only v0.8.1 explicit administrative batches.

Physical Symbian protocol is unchanged; this suite exercises preflight,
HMAC upload/launch with a simulated endpoint, durable receipts, safe resume,
and checks that unknown write commands never hit the phone.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import tempfile
import unittest
from unittest import mock

from test_admin import FakeAdminPhone

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('e7_bridge_batch', ROOT / 'host' / 'e7_bridge.py')
e7 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e7)


class AdminBatchModel(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.manifest = self.base / 'job.batch'
        self.journals = self.base / 'journals'
        self.payload = self.base / 'new-config.txt'
        self.payload.write_bytes(b'Owner-controlled test configuration\n')
        self.host, self.phone = socket.socketpair()
        self.host.settimeout(2.0)
        self.phone.settimeout(2.0)
        self.addCleanup(self.host.close)
        self.addCleanup(self.phone.close)
        self.admin = e7.AdminSession(self.host, '0123456789abcdef', 'c' * 32)
        self.fake = FakeAdminPhone(self.phone, '0123456789abcdef', 'c' * 32)
        self.fake.thread.start()
        self.default_mock = mock.patch.object(e7, 'request', side_effect=self.request_model)
        self.default_mock.start()
        self.addCleanup(self.default_mock.stop)
        self.registry_version = '0.1.0'
        self.requests = []

    def request_model(self, sock, command):
        self.assertIs(sock, self.host)
        self.requests.append(command)
        if command == 'QUIT':
            return ''
        if command == 'PING':
            return 'PONG'
        if command == 'INFO':
            return 'Nokia Belle; Qt 4.7.4; E7 Bridge v0.8.0'
        if command.startswith('STAT '):
            path = command[5:]
            if path not in self.fake.files:
                raise e7.BridgeError('E7: PATH_NOT_ALLOWED_OR_MISSING')
            return 'file | bytes={} | path={}'.format(len(self.fake.files[path]), path)
        if command == 'PKG E94B7002':
            return 'uid=0xE94B7002\ninstalled=yes\nversion={}\nname=E7 Deployment Probe'.format(self.registry_version)
        raise AssertionError('Unexpected phone command: '+command)

    def prepare(self, contents):
        self.manifest.write_text(contents, encoding='utf-8')
        return e7.prepare_write_batch(self.manifest)

    def test_normalise_write_modes(self):
        self.assertEqual(e7.normalize_command('batch --write ./job.batch'), 'BATCH_WRITE ./job.batch')
        self.assertEqual(e7.normalize_command('batch --plan "one job.txt"'), 'BATCH_PLAN "one job.txt"')
        self.assertEqual(e7.normalize_command('batch --resume receipt.jsonl ./job.batch'),
                         'BATCH_RESUME receipt.jsonl ./job.batch')
        self.assertEqual(e7.normalize_command('batch ./safe.txt'), 'BATCH ./safe.txt')
        for value in ('batch --write', 'batch --resume', 'batch --plan', 'batch --write x\nQUIT'):
            with self.subTest(value=value), self.assertRaises(e7.BridgeError):
                e7.normalize_command(value)

    def test_plan_resolves_relative_paths_and_sha(self):
        plan = self.prepare('ping\npush ./new-config.txt\nstat E:/KAI/INBOX/new-config.txt\n')
        self.assertEqual(len(plan['steps']), 3)
        self.assertEqual(plan['steps'][1]['source'], str(self.payload))
        self.assertEqual(plan['steps'][1]['sha256'], hashlib.sha256(self.payload.read_bytes()).hexdigest())
        self.assertEqual(plan['upload_bytes'], self.payload.stat().st_size)
        self.assertEqual(self.admin.seq, 0)
        self.assertEqual(self.fake.files, {})
        e7.describe_write_batch(plan)
        self.assertEqual(self.admin.seq, 0)

    def test_manifests_must_be_explicit(self):
        for bad in ('push ./missing.txt', 'push ./new-config.txt forbidden',
                    'push ./new-config.txt\nexit',
                    'push ./new-config.txt\nbatch ./other',
                    'push ./new-config.txt\nrecord 2 5',
                    'push ./new-config.txt\nps save',
                    'push ./new-config.txt\ndeploy ./missing.sis',
                    'push ./new-config.txt\npush ./new-config.txt'):
            with self.subTest(bad=bad), self.assertRaises(e7.BridgeError):
                self.prepare(bad)
        self.assertEqual(self.fake.files, {})
        self.assertEqual(self.admin.seq, 0)

    def test_cannot_preflight_empty_or_write_free_job(self):
        for contents in ('# nothing here\n', 'ping\ninfo\n'):
            with self.assertRaises(e7.BridgeError):
                self.prepare(contents)

    def test_write_manifest_limits_and_symlink_refusal(self):
        plan = self.prepare('push ./new-config.txt')
        self.assertEqual(len(plan['steps']), 1)
        link = self.base / 'symlink.txt'
        link.symlink_to(self.payload)
        with self.assertRaisesRegex(e7.BridgeError, 'non-symlink'):
            self.prepare('push ./symlink.txt')
        self.manifest.unlink()
        self.manifest.symlink_to(self.base / 'original.txt')
        (self.base / 'original.txt').write_text('push ./new-config.txt')
        with self.assertRaisesRegex(e7.BridgeError, 'non-symlink'):
            e7.prepare_write_batch(self.manifest)

    def test_limits_count_and_size(self):
        self.manifest.write_text('ping\n'*40 + 'push ./new-config.txt\n')
        with self.assertRaisesRegex(e7.BridgeError, 'at most 40'):
            e7.prepare_write_batch(self.manifest)
        self.manifest.write_text('x'*8193)
        with self.assertRaisesRegex(e7.BridgeError, '<=8 KiB'):
            e7.prepare_write_batch(self.manifest)

    def test_changed_source_preflight_sha_blocks_upload(self):
        plan = self.prepare('push ./new-config.txt\n')
        self.payload.write_text('changed since prepared')
        with self.assertRaisesRegex(e7.BridgeError, 'Local source changed since batch preflight'):
            e7.run_write_batch(self.host, self.admin, plan, journal_dir=self.journals)
        self.assertEqual(self.fake.files, {})
        self.assertEqual(self.admin.seq, 0)

    def test_batch_upload_real_hmac_and_receipt(self):
        plan = self.prepare('info\npush ./new-config.txt inbox\nstat E:/KAI/INBOX/new-config.txt\n')
        receipt = e7.run_write_batch(self.host, self.admin, plan, journal_dir=self.journals)
        remote = 'E:/KAI/INBOX/new-config.txt'
        self.assertEqual(self.fake.files[remote], self.payload.read_bytes())
        self.assertIn('STAT '+remote, self.requests)
        self.assertEqual(receipt.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.journals.stat().st_mode & 0o777, 0o700)
        events = [json.loads(line) for line in receipt.read_text().splitlines()]
        self.assertEqual([x['event'] for x in events], ['plan', 'started', 'done', 'started', 'done', 'started', 'done'])
        self.assertEqual(events[0]['sha256'], plan['sha256'])
        self.assertFalse(self.fake.errors)

    def test_registry_assertion_stops_before_later_write(self):
        plan = self.prepare('verify 0xE94B7002 99.0.0\npush ./new-config.txt')
        with self.assertRaisesRegex(e7.BridgeError, 'Batch verification failed'):
            e7.run_write_batch(self.host, self.admin, plan, journal_dir=self.journals)
        self.assertEqual(self.admin.seq, 0)
        self.assertEqual(self.fake.files, {})

    def test_interrupted_failure_not_blindly_retried(self):
        plan = self.prepare('push ./new-config.txt\n')
        # Force a transport error after the stage has started.
        with mock.patch.object(e7, 'push_file', side_effect=e7.BridgeError('connection lost')):
            with self.assertRaisesRegex(e7.BridgeError, 'connection lost'):
                e7.run_write_batch(self.host, self.admin, plan, journal_dir=self.journals)
        receipt = next(self.journals.glob('*.jsonl'))
        with self.assertRaisesRegex(e7.BridgeError, 'Ambiguous interrupted write'):
            e7.run_write_batch(self.host, self.admin, plan, journal_dir=self.journals, receipt=str(receipt))
        self.assertEqual(self.admin.seq, 0)

    def test_resume_validates_source_and_skips_verified_upload(self):
        plan = self.prepare('push ./new-config.txt\nverify 0xE94B7002 0.1.0')
        self.registry_version = '0.0.0'
        with self.assertRaisesRegex(e7.BridgeError, 'Batch verification failed'):
            e7.run_write_batch(self.host, self.admin, plan, journal_dir=self.journals)
        receipt = next(self.journals.glob('*.jsonl'))
        seq_before = self.admin.seq
        self.registry_version = '0.1.0'
        e7.run_write_batch(self.host, self.admin, plan, receipt=str(receipt), journal_dir=self.journals)
        self.assertEqual(self.admin.seq, seq_before)  # no second BEGIN/CHUNK/FINISH
        self.assertEqual(self.fake.files['E:/KAI/INBOX/new-config.txt'], self.payload.read_bytes())
        self.assertGreaterEqual(self.requests.count('STAT E:/KAI/INBOX/new-config.txt'), 2)

    def test_resume_rejects_manifest_or_local_file_changes(self):
        plan = self.prepare('push ./new-config.txt')
        receipt = e7.run_write_batch(self.host, self.admin, plan, journal_dir=self.journals)
        self.payload.write_bytes(b'not the same contents')
        newplan = e7.prepare_write_batch(self.manifest)
        with self.assertRaisesRegex(e7.BridgeError, 'changed'):
            e7.run_write_batch(self.host, self.admin, newplan, receipt=str(receipt), journal_dir=self.journals)

    def test_resume_refuses_missing_or_altered_remote_file(self):
        plan = self.prepare('push ./new-config.txt')
        receipt = e7.run_write_batch(self.host, self.admin, plan, journal_dir=self.journals)
        self.fake.files['E:/KAI/INBOX/new-config.txt'] = b'x'
        with self.assertRaisesRegex(e7.BridgeError, 'no longer matches'):
            e7.run_write_batch(self.host, self.admin, plan, receipt=str(receipt), journal_dir=self.journals)

    def test_deploy_terminal_and_only_launch_ack_not_installed(self):
        pkg = self.base / 'SafeProbe-v0.2.0.sis'
        pkg.write_bytes(b'disposable fake sis fixture')
        plan = self.prepare('ping\ndeploy ./SafeProbe-v0.2.0.sis')
        e7.run_write_batch(self.host, self.admin, plan, journal_dir=self.journals)
        self.assertEqual(self.fake.launch_requests, ['E:/Installs/SafeProbe-v0.2.0.sis'])
        self.assertTrue((self.journals).is_dir())
        with self.assertRaisesRegex(e7.BridgeError, 'last batch step'):
            self.prepare('deploy ./SafeProbe-v0.2.0.sis\nverify 0xE94B7002 0.1.0')
        self.assertEqual(len(self.fake.launch_requests), 1)

    def test_bridge_self_upgrade_not_in_batch(self):
        pkg = self.base / 'E7Bridge-v0.8.1.sis'
        pkg.write_bytes(b'cannot self-upgrade')
        with self.assertRaisesRegex(e7.BridgeError, 'self-upgrading'):
            self.prepare('deploy ./E7Bridge-v0.8.1.sis')

    def test_no_admin_fails_before_journal(self):
        plan = self.prepare('push ./new-config.txt')
        with self.assertRaisesRegex(e7.BridgeError, 'authenticated admin'):
            e7.run_write_batch(self.host, None, plan, journal_dir=self.journals)
        self.assertFalse(self.journals.exists())

    def test_old_readonly_batch_stays_readonly(self):
        self.manifest.write_text('ping\npush ./new-config.txt')
        with self.assertRaisesRegex(e7.BridgeError, 'read-only'):
            e7.read_batch_file(self.manifest)

    def test_repl_write_invocation_executes_manifest(self):
        self.prepare('ping\npush ./new-config.txt')
        with (mock.patch('builtins.input', side_effect=[
                'batch --write '+str(self.manifest), 'exit']),
              mock.patch.object(e7, 'BATCH_JOURNAL_DIR', self.journals)):
            e7.repl(self.host, self.admin)
        self.assertEqual(self.fake.files['E:/KAI/INBOX/new-config.txt'], self.payload.read_bytes())

    def test_repl_plan_invocation_has_no_io(self):
        self.prepare('ping\npush ./new-config.txt')
        with mock.patch('builtins.input', side_effect=[
                'batch --plan '+str(self.manifest), 'exit']):
            e7.repl(self.host, self.admin)
        self.assertEqual(self.fake.files, {})
        self.assertEqual(self.admin.seq, 0)
        self.assertFalse(self.journals.exists())

    def test_no_anything_over_privileged_paths(self):
        for command in ('write C:/sys/bin/test.exe', 'delete C:/private/foo',
                        'shell rm -rf /', 'firmware flash', 'patch-rom /foo'):
            with self.subTest(command=command), self.assertRaises(e7.BridgeError):
                self.prepare('push ./new-config.txt\n'+command)


if __name__ == '__main__':
    unittest.main()
