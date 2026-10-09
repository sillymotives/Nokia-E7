#!/usr/bin/env python3
"""Read-only Nokia Dumberdore RPK2 boot-resource audit.

Never changes the archive or writes any file to the phone. The .rsc format is
compiled binary: printable references are clues, NOT a decoded dependency graph.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import struct

STARTUP_PREFIX = "z:\\private\\2000d75b\\startup\\0\\"
EXE_RE = re.compile(
    rb'(?i)(?<![a-z0-9._-])(?:[a-z]:\\sys\\bin\\)?[a-z0-9._-]{2,100}\.(?:exe|dll|ldd)(?![a-z0-9._-])'
)
MAX_NAME_CHARS = 1024


def read_exact(handle, count):
    data = handle.read(count)
    if len(data) != count:
        raise ValueError('Truncated RPKG near byte {}'.format(handle.tell()))
    return data


def u32(handle):
    return struct.unpack('<I', read_exact(handle, 4))[0]


def u64(handle):
    return struct.unpack('<Q', read_exact(handle, 8))[0]


def load_inventory(path):
    if not path:
        return None
    with Path(path).open(encoding='utf-8', newline='') as f:
        rows = list(csv.DictReader(f))
    inventory = {}
    for row in rows:
        key = row['z_drive_path'].lower()
        if key in inventory:
            raise ValueError('Duplicate inventory path: ' + key)
        inventory[key] = (int(row['bytes']), row['sha256'].lower())
    return inventory


def scan_archive(path, inventory=None):
    """Scan and validate every entry, retaining ONLY boot resources in memory."""
    path = Path(path)
    boot = {}
    entries = 0
    content_bytes = 0
    with path.open('rb') as f:
        magic = read_exact(f, 16).decode('utf-32le')
        version = u32(f)
        count = u32(f)
        extra0 = u32(f)
        extra1 = u32(f)
        if magic != 'RPK2' or version != 0 or not (1 <= count <= 100000):
            raise ValueError('Not a supported Dumberdore RPK2 archive')
        # The final two header fields are archived verbatim as metadata.
        seen = set()
        for _ in range(count):
            attributes = read_exact(f, 8)
            timestamp = read_exact(f, 8)
            chars = u64(f)
            if not 1 <= chars <= MAX_NAME_CHARS:
                raise ValueError('Invalid path-length field')
            name = read_exact(f, chars * 2).decode('utf-16le')
            if not name.lower().startswith('z:\\') or '\x00' in name:
                raise ValueError('Unexpected or malformed volume path')
            key = name.lower()
            if key in seen:
                raise ValueError('Duplicate archive path: ' + name)
            seen.add(key)
            size = u64(f)
            if size > path.stat().st_size:
                raise ValueError('Bad entry size: ' + name)
            is_boot = key.startswith(STARTUP_PREFIX) and key.endswith('.rsc')
            retained = bytearray() if is_boot else None
            remaining = size
            checksum = hashlib.sha256()
            while remaining:
                chunk = read_exact(f, min(1024*1024, remaining))
                checksum.update(chunk)
                if is_boot:
                    if size > 8*1024*1024:
                        raise ValueError('Unexpected large startup resource')
                    retained.extend(chunk)
                remaining -= len(chunk)
            digest = checksum.hexdigest()
            if inventory is not None:
                actual = inventory.get(key)
                if actual != (size, digest):
                    raise ValueError('Inventory disagreement for ' + name)
            if is_boot:
                boot[name] = bytes(retained)
            entries += 1
            content_bytes += size
        if f.read(1):
            raise ValueError('Trailing bytes after last archive entry')
        if inventory is not None and len(seen) != len(inventory):
            raise ValueError('Inventory/archive path-count mismatch')
    return {
        'archive_path': str(path.resolve()), 'bytes': path.stat().st_size,
        'entry_count': entries, 'declared_count': count,
        'payload_bytes': content_bytes,
        'checked_against_inventory': inventory is not None,
        'header_extra': [extra0, extra1], 'boot_resources': boot,
    }


def refs_for_blob(blob):
    """Return sorted de-duplicated printable executable/DLL *references*."""
    refs = set()
    for match in EXE_RE.finditer(blob):
        raw = match.group().decode('ascii', 'replace')
        refs.add(raw.replace('/', '\\'))
    return sorted(refs, key=str.lower)


def normalise_executable(name):
    name = name.lower().replace('/', '\\').split('\\')[-1]
    match = re.search(r'[a-z0-9_.-]+\.(?:exe|dll|ldd)', name)
    return match.group() if match else name


def process_names(path):
    if not path:
        return None
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    if payload.get('format') != 'e7-bridge-process-snapshot-v1':
        raise ValueError('Not an E7 Bridge process snapshot')
    names = payload['processes']
    if not isinstance(names, list) or any(not isinstance(n, str) for n in names):
        raise ValueError('Invalid E7 process snapshot')
    return set(normalise_executable(n) for n in names)


def make_report(result, process_set=None):
    resources = []
    for name, data in sorted(result['boot_resources'].items(), key=lambda pair: pair[0].lower()):
        raw = refs_for_blob(data)
        references = []
        for ref in raw:
            executable = normalise_executable(ref)
            references.append({
                'reference': ref,
                'basename': executable,
                'running_observed': (executable in process_set) if process_set is not None else None,
            })
        resources.append({'resource_path': name, 'size': len(data), 'references': references})
    return {
        'archive': {k: result[k] for k in ('archive_path', 'bytes', 'entry_count', 'declared_count', 'payload_bytes', 'checked_against_inventory')},
        'caution': 'Embedded printable strings are references, NOT proof of invocation, liveness, or safe removability.',
        'processes_supplied': process_set is not None,
        'startup_resources': resources,
    }


def report_markdown(report):
    info = report['archive']
    lines = [
        '# Nokia E7 Belle Refresh: boot-resource reconnaissance',
        '',
        'Read-only report from Dumberdore `SYM.RPKG`. No device settings were changed.',
        '',
        f"Archive: `{Path(info['archive_path']).name}` | {info['entry_count']:,} entries | {info['bytes']:,} bytes.",
        '',
        '**Method:** Extract ASCII-like `.exe`, `.dll`, and `.ldd` references embedded in the compiled `.rsc` startup resources. These are *clues*, not a decoded SSM command list or verified dependency graph.',
        '',
        '## Priorities',
        '',
        '1. **Inspect:** `iaupdatedaemon.exe` in `uiservicescmdlist_ext.rsc` (legacy update daemon reference).',
        '2. **Inspect:** `fotacustcmds.dll` and `dmutilserver.exe` in `noncriticalcmdlist_ext.rsc` (firmware-update / device-management hints).',
        '3. **Preserve:** `sysap.exe`, `sysmon.exe`, `hwrmserver.exe`, `ewsrv.exe`, `accserver.exe` and other boot / UI infrastructure until dependencies are understood.',
        '4. **Never assume:** absence from a single `ps` snapshot means a component is safe to disable.',
        '',
    ]
    if report['processes_supplied']:
        lines.append('Live process-list comparison supplied: **yes**, but it is only a point-in-time observation.')
    else:
        lines.append('Live process-list comparison supplied: **no**. Install E7-Bridge v0.3 and run `ps save` to obtain one.')
    lines.extend(['', '## Startup resources and embedded references', ''])
    for item in report['startup_resources']:
        lines.append('### ' + Path(item['resource_path'].replace('\\', '/')).name)
        lines.append('')
        lines.append('`' + item['resource_path'] + '` | {} bytes'.format(item['size']))
        lines.append('')
        if item['references']:
            for ref in item['references']:
                observation = ''
                if ref['running_observed'] is True:
                    observation = ' | process name observed'
                elif ref['running_observed'] is False:
                    observation = ' | not observed in snapshot'
                lines.append('- `' + ref['reference'] + '`' + observation)
        else:
            lines.append('No printable executable/DLL references located.')
        lines.append('')
    lines.append('## Interpretation rules')
    lines.append('')
    lines.append('- These resources live on the read-only `Z:` firmware image. Do not try deleting their `Z:` copies.')
    lines.append('- A resource can reference a conditional, inactive, or DLL-backed operation, not necessarily a running process.')
    lines.append('- Runtime behavior depends on writable `C:` configuration, patches, provisioning, and current state. This report cannot establish those.')
    lines.append('- Preserve ROM, Dumberdore dump, and writable-state backups before any changes. No change is proposed here.')
    lines.append('')
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True, help='Path to SYM.RPKG (no extraction or writes)')
    parser.add_argument('--inventory', help='Optional precomputed z_drive_inventory.csv for SHA-256 cross-check')
    parser.add_argument('--processes', help='Optional live E7 Bridge v0.3 ps-save JSON snapshot')
    parser.add_argument('--out', default='boot-audit-output', help='Directory for local Markdown and JSON reports')
    args = parser.parse_args(argv)
    scanned = scan_archive(args.archive, load_inventory(args.inventory))
    report = make_report(scanned, process_names(args.processes))
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / 'e7-boot-map.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (outdir / 'e7-boot-map.md').write_text(report_markdown(report), encoding='utf-8')
    print('Verified {} entries; found {} boot resources'.format(scanned['entry_count'], len(scanned['boot_resources'])))
    print('Reports:', outdir / 'e7-boot-map.md', 'and', outdir / 'e7-boot-map.json')


if __name__ == '__main__':
    main()
