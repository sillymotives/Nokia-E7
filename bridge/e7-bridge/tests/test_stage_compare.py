"""Tests for read-only offline comparisons, using generated fixtures only."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import stage_compare as stages


def snap(processes, free=None, fmt='e7-bridge-diagnostic-snapshot-v1'):
    data = {'format': fmt, 'timestamp_utc': '2026-10-10T15:00:00+00:00',
            'processes': processes, 'process_count': len(processes)}
    if fmt == 'e7-bridge-process-snapshot-v1':
        data['count'] = data.pop('process_count')
    if free is not None:
        data['metrics'] = {'ram_free_bytes': free}
    return data


class StageComparisonTests(unittest.TestCase):
    def test_counter_preserves_duplicate_process_instances(self):
        a = stages.validate_sample(snap(['a', 'a', 'b'], 1024), 'early')
        b = stages.validate_sample(snap(['a', 'b', 'b'], 2048), 'settled')
        d = stages.compare(a, b)
        self.assertEqual(d['appeared'], ['b'])
        self.assertEqual(d['disappeared'], ['a'])
        self.assertEqual(d['free_ram_delta_bytes'], 1024)

    def test_two_json_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / 'early.json').write_text(json.dumps(snap(['a', 'b'], 100)))
            (p / 'settled.json').write_text(json.dumps(snap(['a', 'b', 'c'], 120)))
            self.assertEqual(stages.main([str(p / 'early.json'), str(p / 'settled.json'), '--json']), 0)

    def test_jsonl_first_to_last(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'run.jsonl'
            records = [snap(['a'], 100, fmt='e7-bridge-recording-sample-v1'),
                       snap(['a', 'b'], 110, fmt='e7-bridge-recording-sample-v1'),
                       snap(['a', 'c'], 120, fmt='e7-bridge-recording-sample-v1')]
            p.write_text('\n'.join(json.dumps(s) for s in records) + '\n')
            a = stages.read_file(p)
            self.assertEqual(len(a), 3)
            d = stages.compare(a[0], a[-1])
            self.assertEqual(d['appeared'], ['c'])
            self.assertEqual(d['disappeared'], [])

    def test_reject_missing_count_and_unsupported_format(self):
        with self.assertRaises(stages.SnapshotError):
            stages.validate_sample({'format': 'evil', 'processes': [], 'count': 0}, 'bad')
        data = snap(['a'])
        data['process_count'] = 2
        with self.assertRaises(stages.SnapshotError):
            stages.validate_sample(data, 'bad')

    def test_reject_oversized_file_and_invalid_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'big.json'
            p.write_bytes(b' ' * (stages.MAX_BYTES + 1))
            with self.assertRaises(stages.SnapshotError):
                stages.read_file(p)
        with self.assertRaises(stages.SnapshotError):
            stages.validate_sample(snap(['bad\nname']), 'bad')

    def test_ram_not_inferred_for_process_snapshot(self):
        a = stages.validate_sample(snap(['a'], fmt='e7-bridge-process-snapshot-v1'), 'before')
        b = stages.validate_sample(snap(['a'], 100), 'after')
        self.assertIsNone(stages.compare(a, b)['free_ram_delta_bytes'])

    def test_invalid_jsonl_root_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'run.jsonl'
            p.write_text('[]\n[]\n')
            with self.assertRaises(stages.SnapshotError):
                stages.read_file(p)

    def test_privacy_no_network_or_write_to_handset_calls(self):
        source = (Path(__file__).resolve().parents[1] / 'tools' / 'stage_compare.py').read_text()
        for token in ('socket.', 'urllib.', 'requests.', 'RProperty::Set', 'SystemShell'):
            self.assertNotIn(token, source)

if __name__ == '__main__':
    unittest.main()
