import importlib.util
import json
from pathlib import Path
import socket
import struct
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]

def import_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

e7 = import_module('e7_bridge_recon', ROOT / 'host/e7_bridge.py')
boot = import_module('audit_boot_recon', ROOT / 'tools/audit_boot.py')


class ProcessProtocolTests(unittest.TestCase):
    def setUp(self):
        self.a, self.b = socket.socketpair()
        self.addCleanup(self.a.close)
        self.addCleanup(self.b.close)
        self.a.settimeout(1)
        self.b.settimeout(1)

    def test_parse_commands(self):
        self.assertEqual(e7.normalize_command('ps'), 'PROCS 0')
        self.assertEqual(e7.normalize_command('ps all'), 'PS_ALL')
        self.assertEqual(e7.normalize_command('ps save'), 'PS_SAVE')
        self.assertEqual(e7.normalize_command('ps 20'), 'PROCS 20')
        for invalid in ['ps 2001', 'ps -1', 'ps junk', 'ps 1 2', 'ps 99999']:
            with self.assertRaises(e7.BridgeError):
                e7.normalize_command(invalid)

    def test_paged_enumeration_and_snapshot(self):
        import base64
        def device():
            self.assertEqual(e7.recv_line(self.b), 'PROCS 0')
            e7.send_line(self.b, 'B64 ' + base64.b64encode(b'sysap.exe[12]\nsysmon.exe[1]\n[NEXT] 2').decode())
            self.assertEqual(e7.recv_line(self.b), 'PROCS 2')
            e7.send_line(self.b, 'B64 ' + base64.b64encode(b'iaupdatedaemon.exe[2]\n[END]').decode())
        worker = threading.Thread(target=device)
        worker.start()
        names = e7.collect_processes(self.a)
        worker.join(1)
        self.assertFalse(worker.is_alive())
        self.assertEqual(len(names), 3)
        with tempfile.TemporaryDirectory() as td:
            dest = e7.save_process_snapshot(names, td)
            data = json.loads(dest.read_text(encoding='utf-8'))
            self.assertEqual(data['count'], 3)
            self.assertEqual(data['processes'], names)
            self.assertEqual(dest.stat().st_mode & 0o777, 0o600)

    def test_reject_nonprogressing_pagination(self):
        import base64
        def device():
            self.assertEqual(e7.recv_line(self.b), 'PROCS 0')
            e7.send_line(self.b, 'B64 ' + base64.b64encode(b'x.exe\n[NEXT] 0').decode())
        worker=threading.Thread(target=device)
        worker.start()
        with self.assertRaisesRegex(e7.BridgeError, 'pagination'):
            e7.collect_processes(self.a)
        worker.join(1)


class ArchiveScannerTests(unittest.TestCase):
    def test_tiny_rpkg_reference(self):
        name = r'Z:\PRIVATE\2000D75B\startup\0\uiservicescmdlist_ext.rsc'
        payload = b'hello iaupdatedaemon.exe and z:\\sys\\bin\\sysap.exe end'
        raw = ('RPK2'.encode('utf-32le') + struct.pack('<IIII', 0, 1, 32, 0x516dc0)
               + b'\x01' + b'\x00'*7 + b'\x00'*8
               + struct.pack('<Q',len(name)) + name.encode('utf-16le')
               + struct.pack('<Q',len(payload)) + payload)
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)/'sample.RPKG'
            path.write_bytes(raw)
            actual=boot.scan_archive(path)
            self.assertEqual(actual['entry_count'],1)
            report=boot.make_report(actual,{'iaupdatedaemon.exe'})
            refs=report['startup_resources'][0]['references']
            self.assertEqual({r['basename'] for r in refs}, {'iaupdatedaemon.exe','sysap.exe'})
            self.assertTrue(next(r for r in refs if r['basename']=='iaupdatedaemon.exe')['running_observed'])
            self.assertFalse(next(r for r in refs if r['basename']=='sysap.exe')['running_observed'])

    def test_invalid_truncated_archive(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'bad.RPKG';path.write_bytes('RPK2'.encode('utf-32le')+b'\0'*9)
            with self.assertRaises(ValueError):
                boot.scan_archive(path)

    def test_snapshot_matching(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'ps.json'
            path.write_text(json.dumps({'format':'e7-bridge-process-snapshot-v1',
                              'processes':[r'Z:\sys\bin\sysap.exe[12]', 'iaupdatedaemon.exe[9]']}))
            self.assertEqual(boot.process_names(path),{'sysap.exe','iaupdatedaemon.exe'})

if __name__ == '__main__':
    unittest.main()
