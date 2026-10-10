"""Reproducible, fully offline service-triage regressions, synthetic fixtures only."""
import importlib.util
import json
from pathlib import Path
import stat
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'host'))
import service_triage as triage
import inventory


def snapshot(label, processes, ram=110000000):
    records = [
        ('0x101FFB51','Ovi Music'),
        ('0x20006D88','-Norton AntiVirus'),
        ('0x2000F85A','Application update'),
        ('0x2000F85D','Software updater'),
        ('0x2001E277','Email'),
        ('0x200261C5','nokiastoreclient'),
        ('0x200269AE','Nokia Messaging Components'),
        ('0x20031573','NokiaAnalyticsCollector'),
        ('0xE0050C10','RomPatcher+ S3 Recovery'),
    ]
    pkgs = [dict(uid=uid, name=name, version='1.0.0') for uid,name in sorted(records)]
    return inventory.compose('Nokia Belle; E7 Bridge v0.8.0', pkgs, processes,
                             {'ram_total_bytes':257228800,'ram_free_bytes':ram,
                              'battery_level_raw':7,'battery_status_raw':0,
                              'charging_status_raw':0},
                             '2026-10-10T18:00:00+00:00',
                             '2026-10-10T18:00:05+00:00',label)


def tiny_rom(entries):
    encoded = 'RPK2'.encode('utf-32le') + struct.pack('<IIII',0,len(entries),0,0)
    for name, data in entries:
        encoded += b'\x00'*16 + struct.pack('<Q',len(name)) + name.encode('utf-16le')
        encoded += struct.pack('<Q',len(data)) + data
    return encoded


class ServiceTriageTests(unittest.TestCase):
    def setUp(self):
        self.idle = snapshot('idle', ['iaupdatebgchecker[200211f4]0001',
                      'symc_AV.exe[20006d8d]0001','!MsvServer[1000484b]0001',
                      'emailservermonitor.exe[20025fad]0001','mpxplaybackserver.exe[101ffc00]0001'])
        self.music = snapshot('music',self.idle['processes']+['mpx.exe[102072c3]0001',
                        '!SensorServer[1020507e]0001'],ram=108578688)

    def test_observation_has_independent_package_and_process_leads(self):
        data = triage.evidence(self.idle,self.music)
        self.assertEqual(data['format'],triage.FORMAT)
        self.assertEqual(data['changes']['processes_appeared'],
                         ['!SensorServer[1020507e]0001','mpx.exe[102072c3]0001'])
        self.assertEqual(data['changes']['ram_free_delta_bytes'],-1421312)
        self.assertEqual(len(data['groups']),5)
        updater=next(g for g in data['groups'] if g['id']=='updater')
        self.assertEqual(len(updater['packages']),2)
        self.assertEqual(next(p for p in updater['process_name_leads'] if p['candidate_name']=='iaupdatebgchecker')['active_instances'], ['iaupdatebgchecker[200211f4]0001'])
        self.assertTrue(any(g['id']=='patching' and 'Preserve' in g['name'] for g in data['groups']))
        self.assertIn('!msvserver', [p['name'] for p in data['core_processes_to_preserve']])
        report=triage.markdown(data)
        self.assertIn('No service, package, driver or patch is cleared for removal',report)
        self.assertIn('NokiaAnalyticsCollector',report)
        self.assertIn('iaupdatebgchecker',report)
        self.assertIn('ROM-dump / Norton / RomPatcher',report)
        self.assertNotIn('safe to remove',report)

    def test_process_suffix_and_case_variants(self):
        self.assertEqual(triage.basename_of_process('!MsvServer[1000484b]0001'),'!msvserver')
        self.assertEqual(triage.basename_of_process('Z:\\sys\\bin\\iaupdatedaemon.exe[200211f4]0002'),'iaupdatedaemon.exe')
        self.assertEqual(triage.basename_of_process('mpx.exe'),'mpx.exe')

    def test_exact_rom_binary_and_startup_reference_observations(self):
        rom=tiny_rom([
            (r'Z:\sys\bin\iaupdatedaemon.exe',b'AB'),
            (r'Z:\sys\bin\analyticscollector.dll',b'C'),
            (r'Z:\private\2000d75b\startup\0\uiservicescmdlist_ext.rsc',
             b'xyz iaupdatedaemon.exe\x00 never_infer_boot_execution'),
        ])
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'demo.RPKG';path.write_bytes(rom)
            out=triage.inspect_rom_archive(path,triage.requested_binaries())
        self.assertEqual(out['entry_count'],3)
        self.assertEqual(out['startup_resource_count'],1)
        self.assertEqual(out['z_binaries']['iaupdatedaemon.exe'], [r'Z:\sys\bin\iaupdatedaemon.exe'])
        self.assertEqual(out['startup_string_refs']['iaupdatedaemon.exe'],['uiservicescmdlist_ext.rsc'])
        self.assertEqual(out['z_binaries']['analyticscollector.dll'],[r'Z:\sys\bin\analyticscollector.dll'])
        item=next(g for g in triage.evidence(self.idle,self.music,out)['groups'] if g['id']=='updater')
        self.assertIn('startup string',triage.markdown(triage.evidence(self.idle,self.music,out)).lower())
        self.assertTrue(item['rom_evidence'])

    def test_absence_from_Z_never_implies_package_unused(self):
        rom=tiny_rom([(r'Z:\sys\bin\mpx.exe',b'X')])
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'short.RPKG';path.write_bytes(rom)
            result=triage.inspect_rom_archive(path,triage.requested_binaries())
        self.assertEqual(result['z_binaries']['symc_av.exe'],[])
        details=triage.evidence(self.idle,self.music,result)
        self.assertTrue(any('Missing ROM Z: files may exist on writable C:' in s for s in details['limitations']))

    def test_bad_rom_and_symlink_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            file=Path(temp)/'rom';file.write_bytes(b'F'*100)
            with self.assertRaises(ValueError):
                triage.inspect_rom_archive(file,triage.requested_binaries())
            file.write_bytes(tiny_rom([(r'Z:\sys\bin\example.exe',b'hello')])[:-2])
            with self.assertRaises(ValueError):
                triage.inspect_rom_archive(file,triage.requested_binaries())
            link=Path(temp)/'alias';link.symlink_to(file)
            with self.assertRaisesRegex(ValueError,'symlink'):
                triage.inspect_rom_archive(link,triage.requested_binaries())

    def test_extra_bytes_and_duplicate_names_refused(self):
        entries=[(r'Z:\sys\bin\example.exe',b'a')]
        with tempfile.TemporaryDirectory() as temp:
            file=Path(temp)/'rom';file.write_bytes(tiny_rom(entries)+b'extra')
            with self.assertRaisesRegex(ValueError,'Unexpected bytes'):
                triage.inspect_rom_archive(file,triage.requested_binaries())
            file.write_bytes(tiny_rom(entries+entries))
            with self.assertRaisesRegex(ValueError,'duplicate'):
                triage.inspect_rom_archive(file,triage.requested_binaries())

    def test_private_output_is_owner_only_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'secret'
            data=triage.evidence(self.idle,self.music)
            dir_path=inventory.private_directory(root)
            jsonfile=inventory.private_write(dir_path/'service.json',json.dumps(data))
            mdfile=inventory.private_write(dir_path/'service.md',triage.markdown(data))
            self.assertEqual(stat.S_IMODE(dir_path.stat().st_mode),0o700)
            self.assertEqual(stat.S_IMODE(jsonfile.stat().st_mode),0o600)
            self.assertEqual(stat.S_IMODE(mdfile.stat().st_mode),0o600)
            with self.assertRaises(FileExistsError):
                inventory.private_write(jsonfile,'oops')
            wide=Path(temp)/'wide';wide.mkdir(mode=0o755);wide.chmod(0o755)
            with self.assertRaises(inventory.InventoryError):
                inventory.private_directory(wide)

    def test_device_mismatch_prevents_comparison(self):
        data=json.loads(json.dumps(self.music));data['device_info']='Not the same device'
        with self.assertRaisesRegex(ValueError,'different device'):
            triage.evidence(self.idle,data)

    def test_no_network_and_no_mutation_codepaths(self):
        source=(ROOT/'tools'/'service_triage.py').read_text()
        for dangerous in ('socket.', 'subprocess.', 'urllib.', 'requests.',
                          'RProperty::Set', 'os.system(', 'shutil.rmtree('):
            self.assertNotIn(dangerous,source)
        self.assertTrue(all('package_uids' in g and 'process_names' in g for g in triage.GROUPS))

    def test_cli_creates_report_and_fails_closed_on_repeat(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);out=root/'private'
            f1,f2=root/'idle.json',root/'music.json'
            f1.write_text(json.dumps(self.idle));f2.write_text(json.dumps(self.music))
            self.assertEqual(triage.main(['--idle',str(f1),'--active',str(f2),'--out',str(out)]),0)
            self.assertEqual(len(list(out.glob('*.md'))),1)
            self.assertEqual(len(list(out.glob('*.json'))),1)
            with self.assertRaises(SystemExit) as failed:
                triage.main(['--idle',str(f1),'--active',str(f2),'--out',str(out)])
            self.assertEqual(failed.exception.code,2)


if __name__=='__main__':
    unittest.main()
