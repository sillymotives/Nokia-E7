"""v0.4 offline behaviour tests; no physical phone or Symbian SDK needed."""
import importlib.util
import json
from pathlib import Path
import socket
import tempfile
import threading
import unittest
from unittest import mock

SOURCE = Path(__file__).resolve().parents[1] / 'host' / 'e7_bridge.py'
spec = importlib.util.spec_from_file_location('e7_bridge_v04', SOURCE)
e7 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e7)

TELEMETRY = ('ram_total_bytes=268435456\nram_free_bytes=67108864\n'
             'battery_level_raw=5\nbattery_status_raw=1\ncharging_status_raw=0')


class BlackBoxTests(unittest.TestCase):
    def test_normalize_commands_and_limits(self):
        self.assertEqual(e7.normalize_command('metrics'), 'METRICS')
        self.assertEqual(e7.normalize_command('capture'), 'CAPTURE')
        self.assertEqual(e7.normalize_command('diff'), 'DIFF')
        self.assertEqual(e7.normalize_command('record'), 'RECORD 3 10')
        self.assertEqual(e7.normalize_command('record 4 15'), 'RECORD 4 15')
        for bad in ('record 1 10', 'record 4 1', 'record 12 120',
                    'record 3 10 20', 'record 999 10', 'record -1 10',
                    'metrics X', 'diff X', 'capture X', 'record 3 1.5'):
            with self.subTest(command=bad), self.assertRaises(e7.BridgeError):
                e7.normalize_command(bad)
        with self.assertRaises(e7.BridgeError):
            e7.normalize_command('kill sysap.exe')

    def test_metric_parser_keeps_raw_and_missing_values(self):
        values = e7.parse_metrics(TELEMETRY)
        self.assertEqual(values['ram_total_bytes'], 268435456)
        self.assertEqual(values['battery_level_raw'], 5)
        self.assertEqual(values['charging_status_raw'], 0)
        self.assertIsNone(e7.parse_metrics(TELEMETRY.replace('=5', '=unavailable'))['battery_level_raw'])

    def test_reject_bad_metrics(self):
        for bad in ('', TELEMETRY + '\nfoo=1',
                    TELEMETRY.replace('battery_level_raw=5', 'battery_level_raw=NaN'),
                    TELEMETRY.replace('battery_level_raw=5', 'battery_level_raw=-99999'),
                    TELEMETRY + '\ncharging_status_raw=1',
                    TELEMETRY.replace('ram_total_bytes=268435456', 'ram_total_bytes=-1')):
            with self.subTest(value=bad[:40]), self.assertRaises(e7.BridgeError):
                e7.parse_metrics(bad)

    def test_collect_diagnostics_and_private_file(self):
        left, right = socket.socketpair()
        self.addCleanup(left.close)
        self.addCleanup(right.close)
        left.settimeout(1)
        right.settimeout(1)
        def phone():
            import base64
            self.assertEqual(e7.recv_line(right), 'METRICS')
            e7.send_line(right, 'B64 ' + base64.b64encode(TELEMETRY.encode()).decode())
            self.assertEqual(e7.recv_line(right), 'PROCS 0')
            e7.send_line(right, 'B64 ' + base64.b64encode(b'sysap.exe[1]\n[END]').decode())
        thread = threading.Thread(target=phone)
        thread.start()
        sample = e7.collect_diagnostics(left)
        thread.join(1)
        self.assertFalse(thread.is_alive())
        self.assertEqual(sample['process_count'], 1)
        with tempfile.TemporaryDirectory() as tmp:
            path = e7.save_diagnostic_snapshot(sample, tmp)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            data = json.loads(path.read_text())
            self.assertEqual(data['format'], 'e7-bridge-diagnostic-snapshot-v1')
            self.assertEqual(data['processes'], ['sysap.exe[1]'])
            self.assertIn('raw', data['note'])

    def test_compare_saved_snapshot_formats(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder/'e7-processes-20261001T000000000000Z.json').write_text(json.dumps({
                'format': 'e7-bridge-process-snapshot-v1',
                'processes': ['sysap', 'camera', 'camera']}))
            (folder/'e7-diagnostic-20261002T000000000000Z.json').write_text(json.dumps({
                'format': 'e7-bridge-diagnostic-snapshot-v1',
                'processes': ['sysap', 'camera', 'updater']}))
            old, new, changes = e7.latest_snapshot_diff(folder)
            self.assertEqual(changes['started'], ['updater'])
            self.assertEqual(changes['stopped'], ['camera'])
            self.assertLess(old.name.rsplit('-',1)[-1], new.name.rsplit('-',1)[-1])

    def test_recording_is_bounded_and_private(self):
        metrics = e7.parse_metrics(TELEMETRY)
        observations = iter([{'timestamp_utc': 't1', 'finished_utc': 't1', 'process_count': 1,
                              'processes': ['sysap'], 'metrics': metrics},
                             {'timestamp_utc': 't2', 'finished_utc': 't2', 'process_count': 2,
                              'processes': ['sysap', 'updater'], 'metrics': metrics}])
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(e7, 'collect_diagnostics', side_effect=lambda s: next(observations)):
            slept = []
            path, values = e7.record_diagnostics(object(), count=2, interval=5,
                                                 directory=tmp, sleeper=slept.append)
            self.assertEqual(slept, [5])
            self.assertEqual(len(values), 2)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            rows = [json.loads(row) for row in path.read_text().splitlines()]
            self.assertEqual([row['index'] for row in rows], [1, 2])
            self.assertEqual(e7.process_deltas(rows[0]['processes'], rows[1]['processes'])['started'], ['updater'])

    def test_partial_recorder_is_durable(self):
        metric = e7.parse_metrics(TELEMETRY)
        first = {'timestamp_utc':'t', 'finished_utc':'t', 'process_count':1,
                 'processes':['sysap'], 'metrics':metric}
        def read_sample(_):
            if read_sample.calls:
                raise e7.BridgeError('connection lost')
            read_sample.calls += 1
            return first
        read_sample.calls = 0
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(e7, 'collect_diagnostics', side_effect=read_sample):
            with self.assertRaises(e7.BridgeError):
                e7.record_diagnostics(object(), 2, 5, tmp, sleeper=lambda x: None)
            files = list(Path(tmp).glob('e7-recording-*.jsonl'))
            self.assertEqual(len(files), 1)
            self.assertEqual(len(files[0].read_text().splitlines()), 1)

if __name__ == '__main__':
    unittest.main()
