"""v0.8 native registry wire boundary + host batch parser model tests.

These are Linux tests of the parser/protocol contract. They do not substitute for
compiling against the Symbian SDK or querying an E7's native SIS registry.
"""
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


class UidValidation(unittest.TestCase):
    def test_hex_uid_canonical(self):
        for form in ('e94b7002', '0xE94B7002', '0Xe94b7002', ' E94b7002 '):
            self.assertEqual(e7.normalize_uid(form), 'E94B7002')

    def test_bad_uids(self):
        for form in ('0x', '1', '0xE94B70020', '0xG94B7002', '-1',
                     'E94B7002\nQUIT', '0x E94B7002', 'FFFFFFFFF'):
            with self.subTest(form=form), self.assertRaises(e7.BridgeError):
                e7.normalize_uid(form)

    def test_commands(self):
        pairs = {
            'packages': 'PKGS 0', 'packages 12': 'PKGS 12',
            'pkgs all': 'PKGS_ALL', 'pkg 0xe94b7002': 'PKG E94B7002',
            'verify 0xE94B7002 0.1.0': 'VERIFY E94B7002 0.1.0',
            'batch "a file.txt"': 'BATCH "a file.txt"',
        }
        for typed, expected in pairs.items():
            with self.subTest(typed=typed):
                self.assertEqual(e7.normalize_command(typed), expected)

    def test_command_failures(self):
        for text in ('packages -2', 'packages 2001', 'packages hello',
                     'verify 0xE94B7002 0.1', 'verify 0xE94B7002 0.1.0 oops',
                     'pkg nope', 'stat E:/foo\nquit', 'ping\rinfo',
                     'ls E:/private\x1b[200~'):
            with self.subTest(text=text), self.assertRaises(e7.BridgeError):
                e7.normalize_command(text)


class DetailValidation(unittest.TestCase):
    GOOD = 'uid=0xE94B7002\ninstalled=yes\nversion=0.1.0\nname=E7 Deployment Probe'

    def test_present(self):
        self.assertEqual(e7.parse_package_detail(self.GOOD, 'E94B7002'), {
            'uid': '0xE94B7002', 'installed': True,
            'version': '0.1.0', 'name': 'E7 Deployment Probe'})

    def test_missing(self):
        self.assertEqual(e7.parse_package_detail('uid=0xE94B7002\ninstalled=no',
                                                   'E94B7002'),
                         {'uid': '0xE94B7002', 'installed': False})

    def test_rejects_spoofed_malformed_details(self):
        for bad in (
            self.GOOD.replace('0xE94B7002', '0xE94B7001'),
            self.GOOD.replace('0.1.0', '0.1'),
            self.GOOD + '\nextra=impossible',
            self.GOOD.replace('name=E7 Deployment Probe', 'name='),
            self.GOOD.replace('E7 Deployment Probe', 'Hello\x00world'),
            'uid=0xE94B7002\ninstalled=yes',
            'uid=0xE94B7002\ninstalled=no\nversion=0.1.0',
        ):
            with self.subTest(bad=bad), self.assertRaises(e7.BridgeError):
                e7.parse_package_detail(bad, 'E94B7002')


class PageValidation(unittest.TestCase):
    @staticmethod
    def page(total, offset, count, end=None):
        lines = ['total={}'.format(total)]
        for j in range(offset, offset + count):
            lines.append('0x{:08X}|0.1.0|Fixture {}'.format(j, j))
        lines.append('[END]' if end is None else '[NEXT] {}'.format(end))
        return '\n'.join(lines)

    def test_empty(self):
        self.assertEqual(e7.parse_package_page('total=0\n[END]', 0), (0, [], None))

    def test_next_and_final(self):
        total, rows, continuation = e7.parse_package_page(self.page(14, 0, 12, 12), 0)
        self.assertEqual((total, len(rows), continuation), (14, 12, 12))
        total, rows, continuation = e7.parse_package_page(self.page(14, 12, 2), 12)
        self.assertEqual((total, len(rows), continuation), (14, 2, None))

    def test_rejects_bad_pagination(self):
        for response, offset in (
            ('total=15\n[END]', 0),
            (self.page(50, 0, 12, 0), 0),
            (self.page(50, 0, 12, 24), 0),
            (self.page(50, 0, 1, 1), 0),
            ('total=1\n0xE94B7002|oops|Probe\n[END]', 0),
            ('total=2001\n[END]', 2001),
            ('total=1\n0xE94B7002|0.1.0|Probe\nno', 0),
            ('total=1\n0xE94B7002|0.1.0|Bad\x1bname\n[END]', 0),
        ):
            with self.subTest(response=response), self.assertRaises(e7.BridgeError):
                e7.parse_package_page(response, offset)


class RegistryWire(unittest.TestCase):
    def setUp(self):
        self.host, self.phone = socket.socketpair()
        self.host.settimeout(1.0)
        self.phone.settimeout(1.0)
        self.addCleanup(self.host.close)
        self.addCleanup(self.phone.close)

    def _serve_once(self, expected, response):
        def responder():
            self.assertEqual(e7.recv_line(self.phone), expected)
            e7.send_line(self.phone, 'B64 ' + __import__('base64').b64encode(response.encode()).decode())
        thread = threading.Thread(target=responder)
        thread.start()
        self.addCleanup(thread.join)

    def test_package_detail(self):
        self._serve_once('PKG E94B7002', DetailValidation.GOOD)
        self.assertEqual(e7.package_detail(self.host, '0xE94B7002')['version'], '0.1.0')

    def test_verify_found(self):
        self._serve_once('PKG E94B7002', DetailValidation.GOOD)
        detail, match = e7.verify_package(self.host, 'E94B7002', '0.1.0')
        self.assertTrue(match)
        self.assertEqual(detail['name'], 'E7 Deployment Probe')

    def test_verify_mismatched_version(self):
        self._serve_once('PKG E94B7002', DetailValidation.GOOD)
        _, match = e7.verify_package(self.host, 'E94B7002', '99.0.0')
        self.assertFalse(match)

    def test_verify_not_installed(self):
        self._serve_once('PKG E94B7002', 'uid=0xE94B7002\ninstalled=no')
        _, match = e7.verify_package(self.host, 'E94B7002', '0.1.0')
        self.assertFalse(match)

    def test_collect_two_pages(self):
        import base64
        def responder():
            for expected, content in (
                ('PKGS 0', PageValidation.page(13, 0, 12, 12)),
                ('PKGS 12', PageValidation.page(13, 12, 1)),
            ):
                self.assertEqual(e7.recv_line(self.phone), expected)
                e7.send_line(self.phone, 'B64 ' + base64.b64encode(content.encode()).decode())
        thread = threading.Thread(target=responder)
        thread.start()
        try:
            data = e7.collect_packages(self.host)
        finally:
            thread.join(timeout=2)
        self.assertEqual(len(data), 13)
        self.assertEqual(data[-1]['uid'], '0x0000000C')

    def test_registry_duplicate_uid_is_rejected(self):
        import base64
        # Model a malicious or changed package list with duplicate UIDs.
        def responder():
            self.assertEqual(e7.recv_line(self.phone), 'PKGS 0')
            msg = 'total=2\n0xE94B7002|0.1.0|Probe\n0xE94B7002|0.1.0|Probe again\n[END]'
            e7.send_line(self.phone, 'B64 ' + base64.b64encode(msg.encode()).decode())
        worker = threading.Thread(target=responder)
        worker.start()
        with self.assertRaisesRegex(e7.BridgeError, 'repeated an entry'):
            e7.collect_packages(self.host)
        worker.join(timeout=2)

    def test_registry_error_not_swallowed(self):
        def responder():
            self.assertEqual(e7.recv_line(self.phone), 'PKG E94B7002')
            e7.send_line(self.phone, 'ERR REGISTRY_CONNECT -46')
        thread = threading.Thread(target=responder)
        thread.start()
        with self.assertRaisesRegex(e7.BridgeError, 'REGISTRY_CONNECT -46'):
            e7.package_detail(self.host, 'E94B7002')
        thread.join(timeout=2)


class BatchSafety(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'commands.txt'

    def test_read_only_prevalidated_batch(self):
        self.path.write_text('''# Handy E7 regression checks
ping
info
packages 0
pkg 0xE94B7002
verify 0xE94B7002 0.1.0
ls C:/Data/E7DeployProbe
stat C:/Data/E7DeployProbe/probe.txt
''')
        cmds = e7.read_batch_file(self.path)
        self.assertEqual(len(cmds), 7)
        self.assertEqual(cmds[4][1], 'VERIFY E94B7002 0.1.0')

    def test_disallows_mutations_before_any_execution(self):
        for verb in ('push ./a.txt', 'deploy ./b.sis', 'exit', 'batch b.txt',
                     'record 2 5', 'ps save', 'capture'):
            with self.subTest(verb=verb):
                self.path.write_text('ping\n' + verb + '\ninfo\n')
                with self.assertRaisesRegex(e7.BridgeError, 'read-only'):
                    e7.read_batch_file(self.path)

    def test_limits(self):
        self.path.write_text('ping\n' * 41)
        with self.assertRaisesRegex(e7.BridgeError, 'maximum of 40'):
            e7.read_batch_file(self.path)
        self.path.write_text(' ' * 8193)
        with self.assertRaisesRegex(e7.BridgeError, '<=8 KiB'):
            e7.read_batch_file(self.path)

    def test_rejects_symlink(self):
        target = Path(self.tmp.name) / 'target.txt'
        target.write_text('ping\n')
        self.path.symlink_to(target)
        with self.assertRaises(e7.BridgeError):
            e7.read_batch_file(self.path)


class NativeSources(unittest.TestCase):
    def test_native_api_wiring(self):
        phone = (ROOT / 'phone' / 'main.cpp').read_text()
        project = (ROOT / 'phone' / 'e7bridge.pro').read_text()
        for token in ('InstalledUidsL(uids)', 'entry.VersionL()', 'entry.PackageNameL()',
                      'void queryInstalledPackage(', 'void listInstalledPackages(',
                      'PKGS ', 'PKG ', 'REGISTRY_CONNECT'):
            self.assertIn(token, phone)
        self.assertIn('-lsisregistryclient', project)
        self.assertIn('ReadUserData', project)
        self.assertNotIn('AllFiles', project.split('TARGET.CAPABILITY = ')[1].splitlines()[0])
        self.assertNotIn(' TCB', project)


if __name__ == '__main__':
    unittest.main()
