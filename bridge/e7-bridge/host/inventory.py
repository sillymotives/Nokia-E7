"""Read-only, offline E7 SIS/process inventory validation and comparison.

No network API, phone write, package removal, or privileged operations here.
The connected host controller supplies data only after normal bridge authentication.
"""

import datetime
import json
import os
from pathlib import Path
import re
import stat
from collections import Counter

FORMAT = 'e7-inventory-v1'
MAX_BYTES = 1_000_000
MAX_PACKAGES = 2000
MAX_PROCESSES = 2000
METRICS = ('ram_total_bytes', 'ram_free_bytes', 'battery_level_raw',
           'battery_status_raw', 'charging_status_raw')
LABEL = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,31}\Z')
VERSION = re.compile(r'[0-9]{1,5}(?:\.[0-9]{1,5}){2}\Z')
UID = re.compile(r'0x[0-9A-F]{8}\Z')

# These *anchored, narrow* patterns are review leads, not claims a service
# is dead or removable. A substring search for 'ovi' wrongly flagged
# ordinary words such as 'provider' and 'provisioning' on the physical E7.
# The device's working music, Wi-Fi and core services are never classified as
# safe to disable by these heuristics.
REVIEW_TERMS = (
    (r'(?<![a-z0-9])ovi', 'Historical Ovi-branded integration'),
    (r'\bnokia[\s_-]*store', 'Store-related integration to investigate'),
    (r'\bnokia[\s_-]*account', 'Online account integration to investigate'),
    (r'\bnokia[\s_-]*social', 'Social service integration to investigate'),
    (r'\bnokia[\s_-]*messaging', 'Messaging service integration to investigate'),
    (r'\bnokia[\s_-]*chat', 'Chat service integration to investigate'),
    (r'\bnokia[\s_-]*notifications', 'Online notification service to investigate'),
    (r'\bnokia[\s_-]*analytics', 'Analytics component to investigate'),
    (r'(?<![a-z0-9])(?:norton|symantec)',
     'Norton/Symantec package: verify active components and dependencies'),
)

class InventoryError(ValueError):
    pass


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def safe_line(value, max_length):
    return (isinstance(value, str) and 1 <= len(value) <= max_length and
            all(32 <= ord(ch) <= 126 for ch in value))


def safe_process_name(value):
    # Native process names may be Unicode; forbid control/bidi formatting text.
    return (isinstance(value, str) and 1 <= len(value) <= 150 and
            all(ch.isprintable() for ch in value))


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InventoryError('Duplicate JSON key: {}'.format(key))
        result[key] = value
    return result


def validate(snapshot):
    if not isinstance(snapshot, dict) or snapshot.get('format') != FORMAT:
        raise InventoryError('Not an E7 v0.9 inventory snapshot')
    for field in ('started_utc', 'finished_utc'):
        value = snapshot.get(field)
        if not isinstance(value, str) or len(value) > 40:
            raise InventoryError('Invalid capture timestamp')
        try:
            parsed = datetime.datetime.fromisoformat(value)
        except ValueError:
            raise InventoryError('Invalid capture timestamp')
        if parsed.tzinfo is None:
            raise InventoryError('Timestamps must include a timezone')
    if datetime.datetime.fromisoformat(snapshot['started_utc']) > datetime.datetime.fromisoformat(snapshot['finished_utc']):
        raise InventoryError('Capture finished before it started')
    if not safe_line(snapshot.get('device_info'), 300):
        raise InventoryError('Invalid device information')
    label = snapshot.get('label')
    if label is not None and (not isinstance(label, str) or not LABEL.fullmatch(label)):
        raise InventoryError('Invalid capture label')
    packages = snapshot.get('packages')
    if not isinstance(packages, list) or len(packages) > MAX_PACKAGES or snapshot.get('package_count') != len(packages):
        raise InventoryError('Invalid package count')
    prev = ''
    for package in packages:
        if not isinstance(package, dict) or set(package) != {'uid', 'name', 'version'}:
            raise InventoryError('Invalid package record')
        uid, name, version = package['uid'], package['name'], package['version']
        if not isinstance(uid, str) or not UID.fullmatch(uid) or uid <= prev:
            raise InventoryError('Unsorted, repeated or invalid package UID')
        if not safe_line(name, 100) or not isinstance(version, str) or not VERSION.fullmatch(version):
            raise InventoryError('Invalid package name or version')
        prev = uid
    processes = snapshot.get('processes')
    if not isinstance(processes, list) or len(processes) > MAX_PROCESSES or snapshot.get('process_count') != len(processes):
        raise InventoryError('Invalid process count')
    if any(not safe_process_name(name) for name in processes):
        raise InventoryError('Invalid process name')
    metrics = snapshot.get('metrics')
    if not isinstance(metrics, dict) or set(metrics) != set(METRICS):
        raise InventoryError('Invalid metrics fields')
    for key, value in metrics.items():
        if value is not None and (type(value) is not int or
                                  not (-10000 <= value <= 10000 if not key.startswith('ram_') else 0 <= value <= 2**32)):
            raise InventoryError('Invalid metric: {}'.format(key))
    return snapshot


def compose(info, packages, processes, metrics, started, finished, label=None):
    result = {'format': FORMAT, 'started_utc': started, 'finished_utc': finished,
              'label': label, 'device_info': info, 'package_count': len(packages),
              'packages': packages, 'process_count': len(processes),
              'processes': processes, 'metrics': metrics,
              'limitations': [
                  'Package list covers base SIS registry entries, not all menu icons or augmentations.',
                  'Package/process/metrics queries are sequential, not one atomic device snapshot.',
                  'A process being absent or sharing a name does not establish package dependency or removal safety.',
                  'Battery values are raw platform readings, not percentages.'
              ]}
    return validate(result)


def read_snapshot(path):
    path = Path(path).expanduser()
    if path.is_symlink():
        raise InventoryError('Refusing symlinked inventory file')
    try:
        st = path.stat()
        if not stat.S_ISREG(st.st_mode) or st.st_size > MAX_BYTES:
            raise InventoryError('Inventory file must be regular and <=1 MB')
        text = path.read_text(encoding='utf-8')
        return validate(json.loads(text, object_pairs_hook=_unique_object))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise InventoryError('Cannot read valid inventory: {}'.format(exc))


def private_directory(directory):
    dest = Path(directory).expanduser()
    if dest.is_symlink():
        raise InventoryError('Refusing symlinked inventory directory')
    dest.mkdir(mode=0o700, parents=True, exist_ok=True)
    st = dest.stat()
    if not stat.S_ISDIR(st.st_mode) or st.st_uid != os.getuid() or (st.st_mode & 0o077):
        raise InventoryError('Inventory directory must be owner-only (0700)')
    return dest


def private_write(path, contents):
    path = Path(path)
    payload = contents.encode('utf-8')
    if len(payload) > MAX_BYTES:
        raise InventoryError('Inventory output exceeds 1 MB')
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    if hasattr(os, 'O_NOFOLLOW'):
        flags |= os.O_NOFOLLOW
    fd = os.open(str(path), flags, 0o600)
    try:
        with os.fdopen(fd, 'wb') as target:
            target.write(payload)
            target.flush()
            os.fsync(target.fileno())
    except BaseException:
        try:
            path.unlink()
        except OSError:
            pass
        raise
    return path


def save(snapshot, directory):
    """Create a unique immutable JSON baseline, then a companion Markdown review."""
    validate(snapshot)
    dest = private_directory(directory)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    label = snapshot.get('label')
    stem = 'e7-inventory-' + stamp + (('-' + label) if label else '')
    json_path = dest / (stem + '.json')
    md_path = dest / (stem + '.md')
    serialized = json.dumps(snapshot, ensure_ascii=True, indent=2) + '\n'
    private_write(json_path, serialized)
    private_write(md_path, report(snapshot))
    return json_path, md_path


def _fold(name):
    return ''.join(ch for ch in name.casefold() if ch.isalnum() and ch.isascii())


def _display(text):
    """Encode supplied names as non-executable, Markdown-safe inline code."""
    return '`' + text.replace('`', "'").replace('|', '/').replace('\\', '/') + '`'


def leads(snapshot):
    """Purely textual review clues. Never infer obsolete, unused or removable."""
    validate(snapshot)
    procs = [(_fold(process), process) for process in snapshot['processes']]
    out = []
    for row in snapshot['packages']:
        low = row['name'].casefold()
        match = next(((needle, reason) for needle, reason in REVIEW_TERMS
                      if re.search(needle, low)), None)
        if not match:
            continue
        stem = _fold(row['name'])
        possible = sorted(set(original for folded, original in procs if len(stem) >= 6 and
                              (stem in folded or (len(folded) >= 8 and folded in stem))))
        out.append({'uid': row['uid'], 'name': row['name'], 'version': row['version'],
                    'indicator': match[0], 'reason': match[1],
                    'possible_process_name_overlaps': possible[:12]})
    return out


def report(snapshot):
    validate(snapshot)
    items = leads(snapshot)
    lines = ['# Nokia E7 software baseline', '',
             'Captured: ' + snapshot['started_utc'],
             'Device: ' + _display(snapshot['device_info']),
             'Installed base SIS packages: **{}**'.format(snapshot['package_count']),
             'Running process entries: **{}**'.format(snapshot['process_count']),
             '', '## Review leads, not removal recommendations', '']
    if not items:
        lines.append('No preset historical-service naming indicators matched. This does not prove all services are useful.')
    else:
        for item in items:
            lines.append('- {} {} ({}) : {}.'.format(_display(item['uid']), _display(item['name']),
                         item['version'], item['reason']))
            if item['possible_process_name_overlaps']:
                names = ', '.join(_display(x) for x in item['possible_process_name_overlaps'])
                lines.append('  - Name overlaps among sampled processes: {}. Not proof of ownership.'.format(names))
    lines.extend(['', '## Important limits', '',
        '- The registry includes system packages; never delete or disable packages based on this report.',
        '- The package and process inventories were collected in separate queries, not atomically.',
        '- A name overlap is not a verified package-to-process dependency.',
        '- Absence from one running-process sample is not evidence a package is unused.',
        '- The Nokia music player and Wi-Fi must remain operational; no changes are made by this report.',
        '- Battery fields are raw values, never inferred percentages.',
        '', 'Original raw records remain in the adjacent private JSON file.', ''])
    return '\n'.join(lines)


def compare(old, new):
    validate(old)
    validate(new)
    a = {row['uid']: row for row in old['packages']}
    b = {row['uid']: row for row in new['packages']}
    shared = sorted(a.keys() & b.keys())
    changes = [{'uid': uid, 'before': a[uid], 'after': b[uid]} for uid in shared
               if (a[uid]['version'], a[uid]['name']) != (b[uid]['version'], b[uid]['name'])]
    process_a, process_b = Counter(old['processes']), Counter(new['processes'])
    metrics = {key: new['metrics'][key] - old['metrics'][key]
               if old['metrics'][key] is not None and new['metrics'][key] is not None else None
               for key in METRICS}
    return {'format': 'e7-inventory-diff-v1',
            'before_utc': old['started_utc'], 'after_utc': new['started_utc'],
            'device_info_changed': old['device_info'] != new['device_info'],
            'before_package_count': len(a), 'after_package_count': len(b),
            'packages_added': [b[uid] for uid in sorted(b.keys() - a.keys())],
            'packages_removed': [a[uid] for uid in sorted(a.keys() - b.keys())],
            'packages_modified': changes,
            'before_process_count': len(old['processes']),
            'after_process_count': len(new['processes']),
            'processes_appeared': sorted((process_b - process_a).elements()),
            'processes_disappeared': sorted((process_a - process_b).elements()),
            'raw_metric_deltas': metrics}


def diff_report(d):
    lines = ['# E7 baseline comparison', '',
             '{} → {}'.format(d['before_utc'], d['after_utc']), '',
             '- Packages: {} → {}'.format(d['before_package_count'], d['after_package_count']),
             '- Added: {}. Removed: {}. Changed name/version: {}.'.format(
                 len(d['packages_added']),len(d['packages_removed']),len(d['packages_modified'])),
             '- Process entries: {} → {}.'.format(d['before_process_count'],d['after_process_count']),
             '- Process entries appeared: {}; disappeared: {}.'.format(
                 len(d['processes_appeared']),len(d['processes_disappeared'])), '']
    for heading, items in [('Added packages', d['packages_added']),('Removed packages', d['packages_removed'])]:
        lines.extend(['## ' + heading, ''])
        if not items:
            lines.append('None.')
        else:
            for row in items:
                lines.append('- {} {} {}'.format(_display(row['uid']),_display(row['name']),row['version']))
        lines.append('')
    lines.extend(['## Updated packages', ''])
    if not d['packages_modified']:
        lines.append('None.')
    for row in d['packages_modified']:
        a,b=row['before'],row['after']
        lines.append('- {}: {} ({}) → {} ({})'.format(_display(row['uid']),
              _display(a['name']),a['version'],_display(b['name']),b['version']))
    for heading, key in [('New process entries', 'processes_appeared'),('Disappeared process entries','processes_disappeared')]:
        lines.extend(['','## '+heading,''])
        lines.extend('- '+_display(x) for x in d[key])
        if not d[key]:
            lines.append('None.')
    lines.extend(['','## Cautions','',
                  '- These observations cannot establish package-to-process ownership or safe removability.',
                  '- Device process lists are non-atomic and vary with normal activity.',
                  '- Raw RAM and power values are not interpreted as percentages.',
                  '- This tool cannot modify the phone.', ''])
    return '\n'.join(lines)


def save_diff(d, directory):
    folder = private_directory(directory)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    stem = 'e7-comparison-' + stamp
    return (private_write(folder / (stem + '.json'), json.dumps(d, ensure_ascii=True, indent=2)+'\n'),
            private_write(folder / (stem + '.md'), diff_report(d)))


def most_recent(directory):
    folder=private_directory(directory)
    paths=sorted(folder.glob('e7-inventory-*.json'))
    if len(paths)<2:
        raise InventoryError('Need two captured baselines; run baseline capture twice')
    return paths[-2], paths[-1]
