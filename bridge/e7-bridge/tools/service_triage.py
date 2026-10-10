#!/usr/bin/env python3
"""Read-only E7 service triage using two inventory captures and optional ROM metadata.

This is a research aid, not a removal or package-to-process dependency tool.
It never communicates with the phone, edits the ROM, or runs OS commands.
"""

import argparse
import json
import os
from pathlib import Path
import re
import stat
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'host'))
import inventory
from audit_boot import read_exact, u32, u64, refs_for_blob, STARTUP_PREFIX

FORMAT = 'e7-service-triage-v1'
ROM_MAX_BYTES = 1024 * 1024 * 1024
MAX_BOOT_RSC_BYTES = 8 * 1024 * 1024
PROCESS_FORMAT = re.compile(r'^(.*?)\[([0-9a-fA-F]{8})\]([0-9a-fA-F]{4})$')

# IDs and process labels are deliberately independent lists: a shared group is
# a human investigation topic and does NOT assert installed-package ownership.
GROUPS = (
    {
        'id': 'updater', 'name': 'Legacy updater / device-management investigation',
        'package_uids': ('0x2000F85A', '0x2000F85D'),
        'process_names': ('iaupdatebgchecker', 'iaupdatedaemon.exe',
                          'spwatchdog', 'omserver.exe', 'dmutilserver.exe'),
        'rom_hints': ('fotacustcmds.dll',),
        'interpretation': 'Update, FOTA and management clues; do not assume the installer or device-management stack is optional.'
    },
    {
        'id': 'online', 'name': 'Ovi / Store / analytics / notification investigation',
        'package_uids': ('0x2001E2A9', '0x200261C5', '0x2002D07F',
                         '0x2002EAB4', '0x20031573'),
        'process_names': ('nokiastoreclient.exe', 'ovistore_2002d07f.exe'),
        'rom_hints': ('analyticscollector.dll', 'analyticsservice.dll', 'analytics_plugin.dll'),
        'interpretation': 'The Analytics Collector is a package and DLL integration; lack of a same-named .exe proves nothing about collection or network traffic.'
    },
    {
        'id': 'messaging', 'name': 'Legacy mail / XMPP / online-message investigation',
        'package_uids': ('0x2001E277', '0x200269AE'),
        'process_names': ('emailservermonitor.exe', 'ozemailserver.exe',
                          'ozmonitor.exe', 'fsmailserver.exe', 'neasstartup.exe',
                          'neasserver.exe', 'xmppservice.exe', 'ombengine.exe',
                          'alwaysonlinestarter.exe'),
        'rom_hints': (),
        'interpretation': 'These process names are separate leads, not proof they belong to the listed SIS packages. Keep core messaging intact.'
    },
    {
        'id': 'patching', 'name': 'Preserve: ROM-dump / Norton / RomPatcher provenance',
        'package_uids': ('0x20006D88', '0x20006D89', '0x200080A6',
                         '0xE0050C10', '0xE3CA2DE5', '0xEFFF0D0E', '0xEFFFD0D0'),
        'process_names': ('symc_av.exe', 'symc_lm.exe'),
        'rom_hints': (),
        'interpretation': 'Norton was the quarantine-restore bootstrap for patcherS3.ldd. Its current dependency status is unknown; preserve the working chain.'
    },
    {
        'id': 'music', 'name': 'Preserve: native music controls',
        'package_uids': ('0x101FFB51', '0x101FFC62', '0x101FFC63'),
        'process_names': ('mpx.exe', 'mpxcollectionserver.exe',
                          'mpxplaybackserver.exe', 'mpxharvesterserver.exe'),
        'rom_hints': (),
        'interpretation': 'Music playback is known to work. Treat MPX executables and any Ovi Music integration as preserved until actual feature dependencies are measured.'
    },
)

CORE_PRESERVE = (
    'swidaemon.exe', '!msvserver', 'messagestoreexe.exe', 'mce.exe',
    'phoneserver.exe', 'sysap.exe', 'ewsrv.exe', 'ecomserver.exe',
    'wlmserverexe.exe', 'dhcpserv', 'sisregistryserver.exe',
)


def basename_of_process(full_name):
    """Normalize a Symbian process label, without assuming its SIS ownership."""
    match = PROCESS_FORMAT.fullmatch(full_name)
    base = match.group(1) if match else full_name
    return base.replace('\\', '/').split('/')[-1].lower()


def names_with_instances(snapshot):
    result = {}
    for name in snapshot['processes']:
        result.setdefault(basename_of_process(name), []).append(name)
    return result


def normalise_rom_basename(value):
    return value.replace('/', '\\').rsplit('\\', 1)[-1].lower()


def inspect_rom_archive(path, requested):
    """Inspect RPK2 names and selected startup .rsc blobs; never extract files.

    Avoid allocating full ROM contents. Skipped payloads are length-checked,
    but no all-file checksum is claimed. Treat missing Z: entries as unknown C:.
    """
    source = Path(path).expanduser()
    if source.is_symlink():
        raise ValueError('Refusing symlinked ROM archive')
    st = source.stat()
    if not stat.S_ISREG(st.st_mode) or not 32 <= st.st_size <= ROM_MAX_BYTES:
        raise ValueError('ROM archive is not a supported regular file')
    found = {name: [] for name in requested}
    startup = {}
    seen = set()
    with source.open('rb') as f:
        try:
            magic = read_exact(f, 16).decode('utf-32le')
            version, count, reserved0, reserved1 = u32(f), u32(f), u32(f), u32(f)
        except (UnicodeError, EOFError, ValueError) as exc:
            raise ValueError('Bad ROM header: {}'.format(exc))
        if magic != 'RPK2' or version != 0 or not 1 <= count <= 100000:
            raise ValueError('Unsupported Dumberdore RPK2 archive')
        for _ in range(count):
            read_exact(f, 16)  # attributes and creation timestamp
            length = u64(f)
            if not 1 <= length <= 1024:
                raise ValueError('Invalid archive pathname length')
            name = read_exact(f, length * 2).decode('utf-16le')
            key = name.lower()
            if not key.startswith('z:\\') or '\x00' in name or key in seen:
                raise ValueError('Invalid or duplicate archived pathname')
            seen.add(key)
            size = u64(f)
            if size > st.st_size or f.tell() + size > st.st_size:
                raise ValueError('Invalid ROM entry size')
            if key.startswith('z:\\sys\\bin\\'):
                basename = normalise_rom_basename(key)
                if basename in found:
                    found[basename].append(name)
            if key.startswith(STARTUP_PREFIX) and key.endswith('.rsc'):
                if size > MAX_BOOT_RSC_BYTES:
                    raise ValueError('Oversized ROM startup resource')
                startup[name] = read_exact(f, size)
            else:
                f.seek(size, os.SEEK_CUR)
        if f.read(1):
            raise ValueError('Unexpected bytes after last ROM entry')
    refs = {}
    for resource, blob in startup.items():
        for ref in refs_for_blob(blob):
            basename = normalise_rom_basename(ref)
            if basename in found:
                refs.setdefault(basename, []).append(resource.split('\\')[-1])
    return {
        'entry_count': count,
        'startup_resource_count': len(startup),
        'z_binaries': {k: sorted(v) for k, v in found.items()},
        'startup_string_refs': {k: sorted(set(refs.get(k, []))) for k in found},
    }


def requested_binaries():
    requested = set()
    for spec in GROUPS:
        for name in spec['process_names'] + spec['rom_hints']:
            name = name.lower()
            if name.startswith('!'):
                name = name[1:]
            requested.add(name if '.' in name else name + '.exe')
    return requested


def evidence(idle, active, rom=None):
    inventory.validate(idle)
    inventory.validate(active)
    if idle['device_info'] != active['device_info']:
        raise ValueError('Inventories report different device information')
    packages = {row['uid']: row for row in active['packages']}
    initial_procs, final_procs = names_with_instances(idle), names_with_instances(active)
    output = []
    for spec in GROUPS:
        entries = []
        for uid in spec['package_uids']:
            item = packages.get(uid)
            if item:
                entries.append(item)
        names = []
        for name in spec['process_names']:
            key = name.lower()
            names.append({'candidate_name': name, 'idle_instances': sorted(initial_procs.get(key, [])),
                          'active_instances': sorted(final_procs.get(key, []))})
        refs = []
        if rom is not None:
            for name in dict.fromkeys(spec['process_names'] + spec['rom_hints']):
                key = name.lower().lstrip('!')
                if '.' not in key:
                    key += '.exe'
                refs.append({'filename': key,
                             'rom_z_paths': rom['z_binaries'].get(key, []),
                             'startup_resource_string_refs': rom['startup_string_refs'].get(key, [])})
        output.append({'id': spec['id'], 'name': spec['name'], 'packages': entries,
                       'process_name_leads': names, 'rom_evidence': refs,
                       'interpretation': spec['interpretation']})
    diff = inventory.compare(idle, active)
    return {'format': FORMAT,
            'captures': {'idle_label': idle.get('label'), 'active_label': active.get('label'),
                         'idle_utc': idle['started_utc'], 'active_utc': active['started_utc'],
                         'package_count_idle': idle['package_count'],
                         'package_count_active': active['package_count'],
                         'process_count_idle': idle['process_count'],
                         'process_count_active': active['process_count']},
            'changes': {'packages_added': len(diff['packages_added']),
                        'packages_removed': len(diff['packages_removed']),
                        'packages_modified': len(diff['packages_modified']),
                        'processes_appeared': diff['processes_appeared'],
                        'processes_disappeared': diff['processes_disappeared'],
                        'ram_free_delta_bytes': diff['raw_metric_deltas']['ram_free_bytes']},
            'rom_archive': {'supplied': rom is not None,
                            'archive_entry_count': rom['entry_count'] if rom else None,
                            'startup_resources_scanned': rom['startup_resource_count'] if rom else None},
            'groups': output,
            'core_processes_to_preserve': [
                {'name': key, 'idle_instances': initial_procs.get(key, []),
                 'active_instances': final_procs.get(key, [])}
                for key in CORE_PRESERVE],
            'limitations': [
                'No package-to-process ownership is established by category membership.',
                'ROM file presence does not prove execution; a startup string is not a decoded SSM command.',
                'Missing ROM Z: files may exist on writable C: or other drives.',
                'No network destination, resource consumption per process, or service dependency is measured.',
                'Both captures contain non-atomic successive queries; absence in a sample is not safe-removal evidence.',
                'All groups are INVESTIGATION ONLY. No deletion, disabling, installation, or system modification is proposed.'
            ]}


def markdown(data):
    lines = ['# Nokia E7 read-only service triage', '',
             '**Investigation only. No service, package, driver or patch is cleared for removal.**', '',
             '## Recorded changes', '',
             '- SIS base packages: {} → {}'.format(data['captures']['package_count_idle'],
                                                 data['captures']['package_count_active']),
             '- Running process instances: {} → {}'.format(data['captures']['process_count_idle'],
                                                           data['captures']['process_count_active']),
             '- Packages added/removed/modified: {}/{}/{}'.format(
                 data['changes']['packages_added'], data['changes']['packages_removed'],
                 data['changes']['packages_modified']),
             '- Process entries appeared: {}'.format(', '.join('`'+x+'`' for x in data['changes']['processes_appeared']) or 'none'),
             '- Process entries disappeared: {}'.format(', '.join('`'+x+'`' for x in data['changes']['processes_disappeared']) or 'none'),
             '- Free RAM delta (raw bytes): {}'.format(data['changes']['ram_free_delta_bytes']),
             '- ROM manifest inspected: {}'.format('yes, {} entries and {} startup resource files'.format(
                 data['rom_archive']['archive_entry_count'], data['rom_archive']['startup_resources_scanned'])
                 if data['rom_archive']['supplied'] else 'no'), '']
    for group in data['groups']:
        lines.extend(['## '+group['name'], '', group['interpretation'], '',
                      '**Installed SIS package leads (exact UID):**'])
        if group['packages']:
            for row in group['packages']:
                lines.append('- `{}` `{}` ({})'.format(row['uid'], row['name'].replace('`', "'"), row['version']))
        else:
            lines.append('- No matching named UID in this snapshot; this is not proof of absence of related code.')
        lines.extend(['', '**Process-name leads (NOT validated package ownership):**'])
        for candidate in group['process_name_leads']:
            lines.append('- `{}`: idle {}, active {}'.format(candidate['candidate_name'],
                len(candidate['idle_instances']), len(candidate['active_instances'])))
        if group['rom_evidence']:
            lines.extend(['', '**Z: archive / embedded SSM-resource string leads:**'])
            for row in group['rom_evidence']:
                if row['rom_z_paths'] or row['startup_resource_string_refs']:
                    lines.append('- `{}`: Z: file {}; startup string references {}'.format(
                        row['filename'], 'present' if row['rom_z_paths'] else 'not present in this archive',
                        ', '.join('`'+name+'`' for name in row['startup_resource_string_refs']) or 'none'))
        lines.append('')
    lines.extend(['## Preserve core processes', '',
                 'Core names are retained as a precaution, not as a complete dependency model.', ''])
    for row in data['core_processes_to_preserve']:
        lines.append('- `{}`: idle {}, active {}'.format(row['name'],len(row['idle_instances']),len(row['active_instances'])))
    lines.extend(['', '## Evidence limitations', ''])
    lines.extend('- '+reason for reason in data['limitations'])
    lines.extend(['', '## Next reversible experiments', '',
                  '1. Capture reboot-idle and extended-idle baselines, then compare process deltas without changing startup configuration.',
                  '2. Compare Wi-Fi connected/disconnected snapshots; do not infer network transmission without network telemetry.',
                  '3. Compare native Mail opened/closed snapshots before changing any email or messaging service.',
                  '4. Obtain SIS entry file/SID ownership and genuine startup conditions before considering service controls.',
                  '5. Preserve Norton/patcherS3.ldd/RomPatcher+ and the Dumberdore archive until a full writable-C: and recovery route is validated.', ''])
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--idle', required=True, help='Existing E7 v0.9 inventory JSON (read only)')
    parser.add_argument('--active', required=True, help='Second E7 v0.9 inventory JSON (read only)')
    parser.add_argument('--archive', help='Optional Dumberdore RPK2 ROM dump, streamed read-only')
    parser.add_argument('--out', default='~/.local/share/e7-bridge/service-audits',
                        help='Owner-only output directory (default private Sanctuary directory)')
    args = parser.parse_args(argv)
    try:
        idle, active = inventory.read_snapshot(args.idle), inventory.read_snapshot(args.active)
        rom = inspect_rom_archive(args.archive, requested_binaries()) if args.archive else None
        result = evidence(idle, active, rom)
        dest = inventory.private_directory(args.out)
        stem = 'e7-service-triage-{}-{}'.format(idle['started_utc'][:10],active['started_utc'][:19].replace(':', '-'))
        target_json, target_md = dest/(stem+'.json'), dest/(stem+'.md')
        # Do not overwrite existing artifacts. In-progress partial output is
        # never used for subsequent operations; no phone mutation is possible.
        inventory.private_write(target_json, json.dumps(result, indent=2, ensure_ascii=False)+'\n')
        try:
            inventory.private_write(target_md, markdown(result))
        except BaseException:
            target_json.unlink()
            raise
        print('Saved JSON:', target_json)
        print('Saved review:', target_md)
        print('Review groups:',len(result['groups']))
        return 0
    except (ValueError, OSError, inventory.InventoryError) as exc:
        parser.exit(2,'Audit refused: {}\n'.format(exc))


if __name__ == '__main__':
    sys.exit(main())
