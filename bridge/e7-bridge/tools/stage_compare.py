#!/usr/bin/env python3
"""Compare E7 Bridge process/telemetry snapshots entirely offline on Debian.

No network access, handset access, or firmware writes. Use two .json snapshots
or one .jsonl recording (first sample versus last sample).
"""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

MAX_BYTES = 1_000_000
MAX_ENTRIES = 2000
SNAPSHOT_FORMATS = {
    'e7-bridge-process-snapshot-v1',
    'e7-bridge-diagnostic-snapshot-v1',
    'e7-bridge-recording-sample-v1',
}


class SnapshotError(ValueError):
    """Invalid or unsupported snapshot; no data is modified."""


def validate_sample(payload, label):
    if not isinstance(payload, dict) or payload.get('format') not in SNAPSHOT_FORMATS:
        raise SnapshotError('{}: unsupported snapshot format'.format(label))
    processes = payload.get('processes')
    if not isinstance(processes, list) or len(processes) > MAX_ENTRIES:
        raise SnapshotError('{}: invalid or excessive process entries'.format(label))
    if not all(isinstance(p, str) and 0 < len(p) <= 150 and '\n' not in p and '\r' not in p for p in processes):
        raise SnapshotError('{}: invalid process name'.format(label))
    declared = payload.get('count', payload.get('process_count'))
    if type(declared) is not int or declared != len(processes):
        raise SnapshotError('{}: declared process count disagrees with entries'.format(label))
    stamp = payload.get('timestamp_utc')
    if not isinstance(stamp, str) or not stamp:
        raise SnapshotError('{}: missing timestamp'.format(label))
    metrics = payload.get('metrics')
    if metrics is not None and not isinstance(metrics, dict):
        raise SnapshotError('{}: invalid metrics'.format(label))
    return {'label': str(label), 'timestamp_utc': stamp, 'processes': processes,
            'metrics': metrics or {}}


def read_file(path):
    path = Path(path)
    try:
        if path.stat().st_size > MAX_BYTES:
            raise SnapshotError('{}: file exceeds 1 MiB safety limit'.format(path))
        content = path.read_text(encoding='utf-8')
    except (OSError, UnicodeError) as exc:
        raise SnapshotError('{}: cannot read: {}'.format(path, exc))
    if path.suffix == '.json':
        try:
            return [validate_sample(json.loads(content), path.name)]
        except json.JSONDecodeError as exc:
            raise SnapshotError('{}: malformed JSON: {}'.format(path, exc))
    if path.suffix == '.jsonl':
        lines = [line for line in content.splitlines() if line.strip()]
        if not 2 <= len(lines) <= 100:
            raise SnapshotError('{}: need 2-100 recording samples'.format(path))
        result = []
        for index, line in enumerate(lines, start=1):
            try:
                data = json.loads(line)
            except json.JSONDecodeError as exc:
                raise SnapshotError('{} sample {}: malformed JSON: {}'.format(path, index, exc))
            if not isinstance(data, dict) or data.get('format') != 'e7-bridge-recording-sample-v1':
                raise SnapshotError('{}: not an E7 recording'.format(path))
            result.append(validate_sample(data, '{} sample {}'.format(path.name, index)))
        return result
    raise SnapshotError('{}: expected .json or .jsonl'.format(path))


def compare(before, after):
    """Counter differences preserve repeated instance names, unlike set diffs."""
    first, last = Counter(before['processes']), Counter(after['processes'])
    appear = sorted((last - first).elements())
    disappear = sorted((first - last).elements())
    def ram(snapshot, field):
        value = snapshot['metrics'].get(field)
        return value if type(value) is int and value >= 0 else None
    start_ram, end_ram = ram(before, 'ram_free_bytes'), ram(after, 'ram_free_bytes')
    change = end_ram - start_ram if start_ram is not None and end_ram is not None else None
    return {'before': before['label'], 'after': after['label'],
            'before_utc': before['timestamp_utc'], 'after_utc': after['timestamp_utc'],
            'before_count': len(before['processes']), 'after_count': len(after['processes']),
            'appeared': appear, 'disappeared': disappear,
            'free_ram_before_bytes': start_ram, 'free_ram_after_bytes': end_ram,
            'free_ram_delta_bytes': change}


def print_result(data):
    print('EARLIER: {} ({})'.format(data['before'], data['before_utc']))
    print('LATER:   {} ({})'.format(data['after'], data['after_utc']))
    print('Process entries: {} -> {}'.format(data['before_count'], data['after_count']))
    print('Appeared ({}):'.format(len(data['appeared'])))
    for p in data['appeared']:
        print('  + ' + p)
    print('Disappeared ({}):'.format(len(data['disappeared'])))
    for p in data['disappeared']:
        print('  - ' + p)
    for label, field in [('Earlier', 'free_ram_before_bytes'), ('Later', 'free_ram_after_bytes')]:
        x = data[field]
        print('{} free RAM: {}'.format(label, 'unavailable' if x is None else '{:.2f} MiB'.format(x / 1048576)))
    delta = data['free_ram_delta_bytes']
    print('Free RAM change: {}'.format('unavailable' if delta is None else '{:+.2f} MiB'.format(delta / 1048576)))
    print('Caution: these are non-atomic snapshots taken after bridge launch; not a boot trace or dependency map.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('files', nargs='+', help='Two snapshot .json files, or one .jsonl recording')
    parser.add_argument('--json', action='store_true', help='Emit machine-readable comparison summary to stdout')
    args = parser.parse_args(argv)
    try:
        if len(args.files) == 1 and args.files[0].endswith('.jsonl'):
            samples = read_file(args.files[0])
            before, after = samples[0], samples[-1]
        elif len(args.files) == 2 and all(p.endswith('.json') for p in args.files):
            before, after = read_file(args.files[0])[0], read_file(args.files[1])[0]
        else:
            parser.error('provide exactly two .json snapshots or one .jsonl recording')
        result = compare(before, after)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print_result(result)
        return 0
    except SnapshotError as exc:
        print('error: {}'.format(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
