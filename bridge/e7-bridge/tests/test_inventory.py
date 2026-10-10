"""v0.9 host-only SIS/process inventory: protocol and filesystem regressions."""
import base64
import importlib.util
import json
import os
from pathlib import Path
import socket
import stat
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]

def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, filename)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj

inv = module('e7_inventory_tests', ROOT / 'host' / 'inventory.py')
e7 = module('e7_bridge_inventory_tests', ROOT / 'host' / 'e7_bridge.py')


def sample(n=3):
    packages = [{'uid': '0x{:08X}'.format(i+1), 'version': '1.0.{}'.format(i),
                 'name': ('Ovi Sync' if i == 0 else 'PhoneServer' if i == 1 else 'Nokia Music')}
                for i in range(n)]
    return inv.compose('Nokia Belle; E7 Bridge v0.8.0', packages,
                       ['PhoneServer.exe', 'PhoneServer.exe', 'MusicPlayer.exe'],
                       {'ram_total_bytes': 250000000, 'ram_free_bytes': 100000000,
                        'battery_level_raw': None, 'battery_status_raw': 1,
                        'charging_status_raw': 0},
                       '2026-10-10T18:00:00+00:00',
                       '2026-10-10T18:00:01+00:00', 'before')


class InventoryValidation(unittest.TestCase):
    def test_normal_capture_and_private_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'inventory'
            orig=sample()
            raw,md=inv.save(orig,folder)
            self.assertEqual(inv.read_snapshot(raw),orig)
            self.assertEqual(stat.S_IMODE(folder.stat().st_mode),0o700)
            self.assertEqual(stat.S_IMODE(raw.stat().st_mode),0o600)
            self.assertEqual(stat.S_IMODE(md.stat().st_mode),0o600)
            self.assertIn('Ovi Sync',md.read_text())
            self.assertIn('not removal recommendations',md.read_text())
            self.assertNotIn('Nokia Music` (',md.read_text())
            with self.assertRaises(FileExistsError):
                inv.private_write(raw,'bad overwrite')

    def test_review_candidates_are_only_name_clues(self):
        results=inv.leads(sample())
        self.assertEqual(len(results),1)
        self.assertEqual(results[0]['name'],'Ovi Sync')
        self.assertFalse(results[0]['possible_process_name_overlaps'])
        self.assertIn('not evidence',inv.report(sample()))

    def test_duplicate_registry_or_process_control_rejected(self):
        original=sample()
        variants=[]
        wrong=json.loads(json.dumps(original));wrong['packages'][1]['uid']=wrong['packages'][0]['uid'];variants.append(wrong)
        wrong=json.loads(json.dumps(original));wrong['processes'][0]='bad\nname';variants.append(wrong)
        wrong=json.loads(json.dumps(original));wrong['package_count']=500;variants.append(wrong)
        wrong=json.loads(json.dumps(original));wrong['metrics']['ram_free_bytes']=True;variants.append(wrong)
        wrong=json.loads(json.dumps(original));wrong['label']='../../foo';variants.append(wrong)
        wrong=json.loads(json.dumps(original));wrong['started_utc']='no';variants.append(wrong)
        for snapshot in variants:
            with self.subTest(snapshot=snapshot),self.assertRaises(inv.InventoryError):
                inv.validate(snapshot)

    def test_corrupt_json_duplicate_keys_symlink_and_too_large_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            target=root/'snapshot.json'
            target.write_text('{"format":"e7-inventory-v1","format":"fake"}')
            with self.assertRaisesRegex(inv.InventoryError,'Duplicate JSON key'):
                inv.read_snapshot(target)
            alias=root/'alias.json'
            alias.symlink_to(target)
            with self.assertRaisesRegex(inv.InventoryError,'symlink'):
                inv.read_snapshot(alias)
            target.write_bytes(b' '*(inv.MAX_BYTES+1))
            with self.assertRaisesRegex(inv.InventoryError,'<=1 MB'):
                inv.read_snapshot(target)

    def test_world_readable_folder_refused_not_chmod_silently(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'wide';folder.mkdir(mode=0o755)
            folder.chmod(0o755)
            with self.assertRaisesRegex(inv.InventoryError,'owner-only'):
                inv.save(sample(),folder)
            self.assertEqual(stat.S_IMODE(folder.stat().st_mode),0o755)

    def test_source_name_markup_no_direct_html(self):
        a=sample(1)
        a['packages'][0]['name']='Ovi <script>strange</script>'
        review=inv.report(a)
        self.assertIn('`Ovi <script>strange</script>`',review)
        self.assertNotIn('\n<script>',review)

    def test_diff_keeps_name_changes_and_duplicate_process_counts(self):
        a=sample()
        b=json.loads(json.dumps(a))
        b['packages'][0]['version']='2.0.0'
        b['packages']=b['packages'][1:]+[{'uid':'0x00000004','name':'New Thing','version':'1.0.0'}]
        b['packages'][-1]['uid']='0x00000004'
        b['packages'].sort(key=lambda x:x['uid'])
        b['processes']=['PhoneServer.exe','NewProcess.exe']
        b['package_count']=len(b['packages']);b['process_count']=len(b['processes'])
        b['metrics']['ram_free_bytes']=90000000
        d=inv.compare(a,b)
        self.assertEqual(len(d['packages_removed']),1)
        self.assertEqual(len(d['packages_added']),1)
        self.assertEqual(d['processes_disappeared'],['MusicPlayer.exe','PhoneServer.exe'])
        self.assertEqual(d['processes_appeared'],['NewProcess.exe'])
        self.assertEqual(d['raw_metric_deltas']['ram_free_bytes'],-10000000)
        self.assertIsNone(d['raw_metric_deltas']['battery_level_raw'])
        self.assertIn('not',inv.diff_report(d))

    def test_version_change_and_diff_files(self):
        a=sample();b=json.loads(json.dumps(a));b['packages'][1]['version']='1.9.0'
        d=inv.compare(a,b)
        self.assertEqual(d['packages_modified'][0]['uid'],'0x00000002')
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'private'
            paths=inv.save_diff(d,folder)
            self.assertEqual(len(paths),2)
            self.assertIn('1.9.0',paths[1].read_text())
            self.assertTrue(all(stat.S_IMODE(path.stat().st_mode)==0o600 for path in paths))

    def test_latest_snapshots_require_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'snapshots'
            with self.assertRaisesRegex(inv.InventoryError,'Need two'):
                inv.most_recent(folder)


class OnWireInventory(unittest.TestCase):
    @staticmethod
    def response(command):
        if command=='INFO':
            return 'Nokia Belle; Qt 4.7.4; E7 Bridge v0.8.0'
        if command=='METRICS':
            return '\n'.join(['ram_total_bytes=257228800','ram_free_bytes=123456789',
                              'battery_level_raw=unavailable','battery_status_raw=1',
                              'charging_status_raw=0'])
        if command.startswith('PKGS '):
            offset=int(command.split()[1])
            total=25
            n=min(12,total-offset)
            lines=['total=25']
            for i in range(offset,offset+n):
                name=('Ovi Sync' if i==0 else 'PhoneServer' if i==1 else 'Fixture {}'.format(i))
                lines.append('0x{:08X}|0.1.0|{}'.format(i+1,name))
            lines.append('[END]' if offset+n==total else '[NEXT] {}'.format(offset+n))
            return '\n'.join(lines)
        if command.startswith('PROCS '):
            offset=int(command.split()[1])
            total=23
            lines=['PhoneServer.exe' if i==0 else 'proc_{}'.format(i)
                   for i in range(offset,min(offset+20,total))]
            count = len(lines)
            lines.append('[END]' if offset+count==total else '[NEXT] {}'.format(offset+count))
            return '\n'.join(lines)
        raise AssertionError('Unexpected wire command: '+command)

    def test_capture_full_paginated_inventory_and_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            host,phone=socket.socketpair()
            host.settimeout(3.0);phone.settimeout(3.0)
            seen=[]
            def serve():
                try:
                    for expected in ('INFO','PKGS 0','PKGS 12','PKGS 24','PROCS 0','PROCS 20','METRICS'):
                        got=e7.recv_line(phone)
                        seen.append(got)
                        if got!=expected:
                            raise AssertionError('Expected {} got {}'.format(expected,got))
                        data=self.response(got)
                        e7.send_line(phone,'B64 '+base64.b64encode(data.encode()).decode())
                finally:
                    phone.close()
            worker=threading.Thread(target=serve)
            worker.start()
            try:
                path=e7.run_baseline_command(host,['capture','early'],directory=Path(tmp)/'inventory')
                result=inv.read_snapshot(path)
                self.assertEqual(result['package_count'],25)
                self.assertEqual(result['process_count'],23)
                self.assertEqual(result['metrics']['battery_level_raw'],None)
                self.assertEqual(result['label'],'early')
                self.assertTrue(path.with_suffix('.md').is_file())
            finally:
                host.close();worker.join(timeout=5)
            self.assertEqual(len(seen),7)

    def test_capture_failure_does_not_save_partial_inventory(self):
        with tempfile.TemporaryDirectory() as tmp:
            host,phone=socket.socketpair()
            host.settimeout(2);phone.settimeout(2)
            folder=Path(tmp)/'inventory'
            def serve():
                try:
                    self.assertEqual(e7.recv_line(phone),'INFO')
                    e7.send_line(phone,'OK Nokia Belle')
                    self.assertEqual(e7.recv_line(phone),'PKGS 0')
                    e7.send_line(phone,'ERR REGISTRY_CONNECT -46')
                finally:
                    phone.close()
            worker=threading.Thread(target=serve);worker.start()
            try:
                with self.assertRaisesRegex(e7.BridgeError,'REGISTRY_CONNECT'):
                    e7.run_baseline_command(host,['capture'],directory=folder)
            finally:
                host.close();worker.join(timeout=4)
            self.assertFalse(folder.exists())

    def test_normalization_and_no_new_phone_capabilities(self):
        self.assertEqual(e7.normalize_command('baseline capture first'),'BASELINE capture first')
        self.assertEqual(e7.normalize_command('inventory diff'),'BASELINE diff')
        project=(ROOT/'phone'/'e7bridge.pro').read_text()
        self.assertIn('ReadUserData',project)
        capabilities = next(line for line in project.splitlines() if line.strip().startswith('TARGET.CAPABILITY ='))
        self.assertNotIn('AllFiles',capabilities)
        self.assertNotIn('TCB',capabilities)
        module=(ROOT/'host'/'inventory.py').read_text()
        for token in ('socket.', 'send_line(', 'push_file(', 'deploy_package('):
            self.assertNotIn(token,module)

    def test_offline_report_and_compare_do_not_need_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'inventory'
            one=inv.save(sample(),folder)[0]
            after=sample();after['started_utc']='2026-10-10T19:00:00+00:00';after['finished_utc']='2026-10-10T19:00:01+00:00'
            two=inv.save(after,folder)[0]
            self.assertEqual(e7.run_baseline_command(None,['report',str(one)],folder),None)
            output=e7.run_baseline_command(None,['compare',str(one),str(two)],folder)
            self.assertIsNotNone(output)
            output2=e7.run_baseline_command(None,['diff'],folder)
            self.assertIsNotNone(output2)

class RealisticFullRegistry(unittest.TestCase):
    def test_407_packages_and_173_processes(self):
        """Synthetic full-size, paginated E7 inventory with nontrivial boundaries."""
        host,phone=socket.socketpair()
        host.settimeout(6)
        phone.settimeout(6)
        expected=[]
        def mock():
            try:
                for i in range(34):
                    start=i*12
                    expected.append('PKGS {}'.format(start))
                    self.assertEqual(e7.recv_line(phone),expected[-1])
                    number=min(12,407-start)
                    lines=['total=407']+['0x{:08X}|1.{}.0|Package {}'.format(j+1,j%100,j)
                                           for j in range(start,start+number)]
                    lines.append('[END]' if start+number==407 else '[NEXT] {}'.format(start+number))
                    e7.send_line(phone,'B64 '+base64.b64encode('\n'.join(lines).encode()).decode())
                for i in range(9):
                    start=i*20
                    expected.append('PROCS {}'.format(start))
                    self.assertEqual(e7.recv_line(phone),expected[-1])
                    number=min(20,173-start)
                    lines=['Process {}.exe'.format(j) for j in range(start,start+number)]
                    lines.append('[END]' if start+number==173 else '[NEXT] {}'.format(start+number))
                    e7.send_line(phone,'B64 '+base64.b64encode('\n'.join(lines).encode()).decode())
            finally:
                phone.close()
        thread=threading.Thread(target=mock)
        thread.start()
        try:
            entries=e7.collect_packages(host)
            processes=e7.collect_processes(host)
            self.assertEqual((len(entries),len(processes)),(407,173))
            self.assertEqual(entries[0]['uid'],'0x00000001')
            self.assertEqual(entries[-1]['uid'],'0x00000197')
        finally:
            host.close()
            thread.join(timeout=7)
        self.assertEqual(len(expected),43)


if __name__ == "__main__":
    unittest.main()
