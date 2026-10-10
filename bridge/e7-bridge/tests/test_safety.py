"""Source/protocol assertions that can run without a Symbian toolchain."""
import base64
import importlib.util
from pathlib import Path
import socket
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('e7_bridge', ROOT / 'host' / 'e7_bridge.py')
e7 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e7)


class FrameSafety(unittest.TestCase):
    def setUp(self):
        self.a, self.b = socket.socketpair()
        self.addCleanup(self.a.close)
        self.addCleanup(self.b.close)
        self.a.settimeout(1)
        self.b.settimeout(1)

    def test_line_limit(self):
        with self.assertRaisesRegex(e7.BridgeError, 'Protocol line too long'):
            e7.send_line(self.a, 'x' * e7.MAX_LINE)
        self.b.sendall(b'X' * e7.MAX_LINE + b'\n')
        with self.assertRaisesRegex(e7.BridgeError, 'Protocol line too long'):
            e7.recv_line(self.a)

    def test_crlf_injection_rejected(self):
        with self.assertRaisesRegex(e7.BridgeError, 'Invalid protocol line'):
            e7.send_line(self.a, 'PING\nSTAT E:/')
        with self.assertRaises(e7.BridgeError):
            e7.normalize_command('ls E:/Images\nQUIT')

    def test_untrusted_base64_rejected(self):
        self.b.sendall(b'B64 ###\n')
        with self.assertRaisesRegex(e7.BridgeError, 'Invalid base64'):
            e7.request(self.a, 'PING')

    def test_utf8_response(self):
        reply = 'directory | path=E:/Música'
        wire = b'B64 ' + base64.b64encode(reply.encode('utf-8')) + b'\n'
        self.b.sendall(wire)
        self.assertEqual(e7.request(self.a, 'STAT E:/Música'), reply)

    def test_device_error(self):
        self.b.sendall(b'ERR PATH_NOT_ALLOWED_OR_MISSING\n')
        with self.assertRaisesRegex(e7.BridgeError, 'PATH_NOT_ALLOWED_OR_MISSING'):
            e7.request(self.a, 'LIST Z:/')


class PackageSafety(unittest.TestCase):
    def test_name_uid_and_capabilities_are_consistent(self):
        pro = (ROOT / 'phone' / 'e7bridge.pro').read_text()
        builder = (ROOT / 'build' / 'in-container.sh').read_text()
        self.assertIn('TARGET = E7Bridge', pro)
        self.assertIn('0xE94B7001', pro)
        self.assertIn('uid=0xE94B7001', builder)
        self.assertIn('TARGET.CAPABILITY = NetworkServices ReadUserData', pro)
        self.assertIn('E7Bridge_reg.rsc', builder)
        self.assertIn('E7Bridge-v0.4.0.sis', builder)

    def test_agent_has_read_only_commands(self):
        cpp = (ROOT / 'phone' / 'main.cpp').read_text()
        for verb in ('PING', 'INFO', 'DRIVES', 'PROCS ', 'METRICS', 'LIST ', 'STAT ', 'QUIT'):
            self.assertIn('"' + verb + '"', cpp)
        self.assertNotIn('QProcess', cpp)
        self.assertNotIn('QFile::WriteOnly', cpp)
        self.assertNotIn('QFile::Remove', cpp)
        self.assertIn('canonicalFilePath()', cpp)
        self.assertNotIn('QCryptographicHash::Sha256', cpp)
        self.assertIn('sha256_compat.h', cpp)
        self.assertIn('sha256_compat.h', (ROOT / 'build' / 'in-container.sh').read_text())
        self.assertIn('wantConnection', cpp)
        self.assertIn('TFindProcess', cpp)
        self.assertIn('listProcesses(int offset)', cpp)
        self.assertIn('RProperty::Get', cpp)
        self.assertIn('HAL::Get', cpp)
        self.assertIn('sendMetrics()', cpp)
        self.assertIn('LIBS += -lhal', (ROOT / 'phone' / 'e7bridge.pro').read_text())
        self.assertNotIn('RProperty::Set', cpp)
        self.assertNotIn('HAL::Set', cpp)


if __name__ == '__main__':
    unittest.main()
