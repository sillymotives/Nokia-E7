#!/usr/bin/env python3
"""E7 Bridge v0.7.0: Linux host for a user-operated Symbian diagnostic and admin agent.

Requires Python 3.8+. No nonstandard Python packages.
Protocol v1 uses HMAC-SHA256 to authenticate a device over a locally trusted
network. Transport is NOT encrypted. Do not use on untrusted networks.
"""

import argparse
import base64
import hashlib
import hmac
import os
from pathlib import Path
import secrets
import socket
import sys
import datetime
import json
import re
import shlex
import stat
import time
from collections import Counter

PORT = 46270
MAX_LINE = 4096
PROTO = 'E7B1'
SECRET_PATH = Path.home() / '.config' / 'e7-bridge' / 'pairing-key'
SNAPSHOT_DIR = Path.home() / '.local' / 'share' / 'e7-bridge' / 'snapshots'
PROBE_PATH = 'E:/KAI/INDEX.HTM'  # Exactly one nonprivate fixture on the E7.
PROBE_CHUNK = 1024
PROBE_MAX_BYTES = 65536
ADMIN_MAX_BYTES = 8388608
ADMIN_CHUNK = 2048
ADMIN_NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z')
RECEIVE_DIR = Path.home() / '.local' / 'share' / 'e7-bridge' / 'received'
METRIC_FIELDS = ('ram_total_bytes', 'ram_free_bytes', 'battery_level_raw', 'battery_status_raw', 'charging_status_raw')


class BridgeError(Exception):
    pass


def recv_line(sock):
    """Receive one bounded ASCII envelope with LF terminator."""
    buf = bytearray()
    while len(buf) < MAX_LINE:
        char = sock.recv(1)
        if not char:
            raise BridgeError('Connection closed')
        if char == b'\n':
            return bytes(buf).rstrip(b'\r').decode('ascii', 'strict')
        buf.extend(char)
    raise BridgeError('Protocol line too long')


def send_line(sock, line):
    if '\n' in line or '\r' in line:
        raise BridgeError('Invalid protocol line')
    encoded = line.encode('utf-8')  # supports non-ASCII Nokia file paths
    if len(encoded) > MAX_LINE - 2:
        raise BridgeError('Protocol line too long')
    sock.sendall(encoded + b'\n')


def generate_key(path=SECRET_PATH):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.exists():
        raise BridgeError('Pairing key already exists: {}'.format(path))
    key = secrets.token_hex(8)  # 64 random bits, typed manually on the E7
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    fd = os.open(str(path), flags, 0o600)
    with os.fdopen(fd, 'w', encoding='ascii') as f:
        f.write(key + '\n')
    return key


def load_key(path=SECRET_PATH):
    try:
        key = path.read_text(encoding='ascii').strip().lower()
    except FileNotFoundError:
        raise BridgeError('No pairing key; run: python3 e7_bridge.py init')
    if len(key) != 16 or any(c not in '0123456789abcdef' for c in key):
        raise BridgeError('Pairing key must be exactly 16 hexadecimal characters')
    return key


def expected_auth(key, nonce):
    return hmac.new(key.encode('ascii'), nonce.encode('ascii'), hashlib.sha256).hexdigest()


def authenticate(sock, key):
    nonce = secrets.token_hex(16)
    send_line(sock, '{} CHALLENGE {}'.format(PROTO, nonce))
    line = recv_line(sock)
    bits = line.split(' ')
    if len(bits) != 3 or bits[:2] != [PROTO, 'AUTH']:
        raise BridgeError('Unexpected authentication response')
    if not hmac.compare_digest(bits[2], expected_auth(key, 'device:' + nonce)):
        raise BridgeError('Device authentication failed')
    send_line(sock, PROTO + ' READY ' + expected_auth(key, 'host:' + nonce))
    return nonce


def request(sock, command):
    send_line(sock, command)
    reply = recv_line(sock)
    if reply == 'OK':
        return ''
    if reply.startswith('OK '):
        return reply[3:]
    if reply.startswith('B64 '):
        encoded = reply[4:]
        try:
            data = base64.b64decode(encoded, validate=True)
            return data.decode('utf-8', 'replace')
        except (ValueError, UnicodeError) as exc:
            raise BridgeError('Invalid base64 response: {}'.format(exc))
    if reply.startswith('ERR '):
        raise BridgeError('E7: ' + reply[4:])
    raise BridgeError('Unexpected response from E7: {}'.format(reply[:70]))


def normalize_command(text):
    text = text.strip()
    if not text:
        return None
    if text.lower() in ('help', '?'):
        return 'HELP'
    if text.lower() in ('exit', 'quit'):
        return 'QUIT'
    parts = text.split(None, 1)
    verb = parts[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ''
    if verb == 'ping' and not arg:
        return 'PING'
    if verb == 'info' and not arg:
        return 'INFO'
    if verb == 'drives' and not arg:
        return 'DRIVES'
    if verb == 'metrics' and not arg:
        return 'METRICS'
    if verb == 'pull' and arg.lower() == 'probe':
        return 'PULL_PROBE'
    if verb in ('push', 'deploy') and arg:
        if '\r' in arg or '\n' in arg:
            raise BridgeError('Invalid transfer path')
        return verb.upper() + ' ' + arg
    if verb in ('capture', 'diff') and not arg:
        return verb.upper()
    if verb == 'record':
        pieces = arg.split()
        if len(pieces) not in (0, 2):
            raise BridgeError('record expects COUNT INTERVAL_SECONDS (or no arguments)')
        if not pieces:
            return 'RECORD 3 10'
        if not all(re.fullmatch(r'[0-9]{1,3}', p) for p in pieces):
            raise BridgeError('record arguments must be decimal integers')
        count, interval = (int(p) for p in pieces)
        if not (2 <= count <= 12 and 5 <= interval <= 120 and (count-1)*interval <= 600):
            raise BridgeError('record requires 2-12 samples, 5-120s spacing, <=600s total')
        return 'RECORD {} {}'.format(count, interval)
    if verb in ('ps', 'processes'):
        if arg in ('all', 'save'):
            return 'PS_' + arg.upper()
        if arg and (not arg.isascii() or not arg.isdigit() or int(arg) > 2000):
            raise BridgeError('ps offset must be an integer from 0 to 2000')
        return 'PROCS ' + (arg or '0')
    if verb in ('ls', 'list', 'stat'):
        if any(c in arg for c in ('\r', '\n')):
            raise BridgeError('Invalid path')
        if verb == 'stat':
            if not arg:
                raise BridgeError('stat needs a path')
            return 'STAT ' + arg
        return 'LIST ' + (arg or 'E:/')
    raise BridgeError('Supported: ping, info, drives, ls, stat, ps, metrics, capture, diff, record, pull probe, push LOCAL [inbox|installs], deploy FILE.sis, help, exit')


def parse_probe_info(reply):
    """Validate exact metadata for the fixed, 64 KiB non-private E7 fixture."""
    match = re.fullmatch(r'size=([0-9]{1,5})\nsha256=([0-9a-f]{64})', reply)
    if match is None:
        raise BridgeError('Invalid probe metadata')
    size = int(match.group(1))
    if size > PROBE_MAX_BYTES:
        raise BridgeError('Probe exceeds 64 KiB limit')
    return size, match.group(2)


def request_probe_chunk(sock, offset, expected_length):
    """Read one binary chunk in the pre-existing bounded text frame protocol."""
    if not (0 <= offset < PROBE_MAX_BYTES and offset % PROBE_CHUNK == 0 and
            1 <= expected_length <= PROBE_CHUNK):
        raise BridgeError('Invalid local chunk request')
    send_line(sock, 'FILECHUNK {}'.format(offset))
    reply = recv_line(sock)
    if reply.startswith('ERR '):
        raise BridgeError('E7: ' + reply[4:])
    if not reply.startswith('B64 '):
        raise BridgeError('Unexpected binary chunk response')
    try:
        data = base64.b64decode(reply[4:], validate=True)
    except (ValueError, UnicodeError) as exc:
        raise BridgeError('Invalid binary chunk base64: {}'.format(exc))
    if len(data) != expected_length:
        raise BridgeError('Wrong chunk length: expected {}, received {}'.format(
            expected_length, len(data)))
    return data


def pull_probe(sock, directory=None):
    """Pull only the fixed Field Deck fixture into private Debian storage.

    Remote source is hard-coded on the Nokia. Phone-side SHA-256 allows
    consistency checking; without transport encryption/authenticated frames
    this DOES NOT protect against an active network attacker.
    """
    size, remote_sha = parse_probe_info(request(sock, 'FILEINFO'))
    directory = Path(directory) if directory is not None else RECEIVE_DIR
    if directory.is_symlink():
        raise BridgeError('Refusing symlinked receive directory')
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not directory.is_dir() or (directory.stat().st_mode & 0o077):
        raise BridgeError('Receive directory must be private (mode 0700)')
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    basename = 'e7-fielddeck-' + stamp + '.htm'
    output = directory / basename
    temporary = directory / ('.' + basename + '.part')
    digest = hashlib.sha256()
    fd = os.open(str(temporary), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    offset = 0
    try:
        with os.fdopen(fd, 'wb') as stream:
            while offset < size:
                expected = min(PROBE_CHUNK, size - offset)
                chunk = request_probe_chunk(sock, offset, expected)
                stream.write(chunk)
                digest.update(chunk)
                offset += len(chunk)
            stream.flush()
            os.fsync(stream.fileno())
        if offset != size or digest.hexdigest() != remote_sha:
            raise BridgeError('Transferred bytes failed size/SHA-256 validation')
        # A link, unlike rename, fails if an existing destination has the name.
        os.link(str(temporary), str(output))
        return output, size, remote_sha
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


class AdminSession:
    """Per-command request/reply HMAC tied to the session nonce and sequence.

    This is authenticated integrity, NOT payload confidentiality.
    No side effect occurs unless the Nokia has explicitly connected first.
    """

    def __init__(self, sock, key, nonce):
        if not re.fullmatch(r'[0-9a-f]{16}', key) or not re.fullmatch(r'[0-9a-f]{32}', nonce):
            raise BridgeError('Invalid authenticated session material')
        self.sock = sock
        self.key = key
        self.nonce = nonce
        self.seq = 0

    def _mac(self, direction, seq, body):
        message = '{}:{}:{}:{}'.format(direction, self.nonce, seq, body).encode('ascii')
        return hmac.new(self.key.encode('ascii'), message, hashlib.sha256).hexdigest()

    def send(self, command):
        if not command or not command.isascii() or '\n' in command or '\r' in command:
            raise BridgeError('Invalid admin command')
        self.seq += 1
        seq = self.seq
        mac = self._mac('admin', seq, command)
        send_line(self.sock, 'ADM {} {} {}'.format(seq, command, mac))
        answer = recv_line(self.sock)
        parts = answer.split(' ')
        if len(parts) < 5 or parts[0] != 'ADMREPLY' or parts[1] != str(seq):
            raise BridgeError('Invalid or unauthenticated admin reply')
        body = ' '.join(parts[2:-1])
        tag = parts[-1]
        if not re.fullmatch(r'[0-9a-f]{64}', tag) or not hmac.compare_digest(
                tag, self._mac('reply', seq, body)):
            raise BridgeError('Invalid admin reply HMAC')
        if body == 'OK':
            return ''
        if body.startswith('OK '):
            return body[3:]
        if body.startswith('ERR '):
            raise BridgeError('E7 admin: ' + body[4:])
        raise BridgeError('Unknown admin reply')


def validate_push_name(path, bucket):
    name = Path(path).name
    if not ADMIN_NAME.fullmatch(name) or '..' in name or name.endswith('.'):
        raise BridgeError('Use a simple ASCII filename (1-64 chars, no traversal)')
    if bucket not in ('inbox', 'installs'):
        raise BridgeError('Destination must be inbox or installs')
    if bucket == 'installs' and not name.lower().endswith(('.sis', '.sisx')):
        raise BridgeError('Only .sis or .sisx packages can enter installs')
    return name


def push_file(admin, source, bucket='inbox'):
    """Atomically stage one file on E:, with no phone-side install/unlock.

    All write commands have session-bound request AND response HMACs. The phone
    rejects existing destinations, protected folders and invalid manifest data.
    """
    name = validate_push_name(source, bucket)
    path = Path(source)
    if path.is_symlink() or not path.is_file():
        raise BridgeError('Push source must be an existing regular non-symlink file')
    with path.open('rb') as stream:
        details = os.fstat(stream.fileno())
        if not stat.S_ISREG(details.st_mode) or not 0 <= details.st_size <= ADMIN_MAX_BYTES:
            raise BridgeError('Push source must be a regular file <=8 MiB')
        digest = hashlib.sha256()
        while True:
            block = stream.read(65536)
            if not block:
                break
            digest.update(block)
        expected = digest.hexdigest()
        size = details.st_size
        stream.seek(0)
        begun = True  # Cancel even if BEGIN's response is lost after staging.
        try:
            ready = admin.send('BEGIN {} {} {} {}'.format(bucket, name, size, expected))
            if ready != 'READY':
                raise BridgeError('Phone refused staging manifest')
            sent = 0
            while sent < size:
                block = stream.read(min(ADMIN_CHUNK, size - sent))
                if not block:
                    raise BridgeError('Local file changed during upload')
                data = base64.b64encode(block).decode('ascii')
                reply = admin.send('CHUNK {} {}'.format(sent, data))
                if reply != 'CHUNK':
                    raise BridgeError('Bad chunk acknowledgement')
                sent += len(block)
            reply = admin.send('FINISH')
            if reply != 'STORED {} {}'.format(size, expected):
                raise BridgeError('Final remote receipt mismatch')
            begun = False
            return 'E:/Installs/' + name if bucket == 'installs' else 'E:/KAI/INBOX/' + name, size, expected
        except (OSError, BridgeError):
            if begun:
                try:
                    admin.send('CANCEL')
                except (OSError, BridgeError):
                    pass
            raise


def deploy_package(admin, source):
    """Stage a signed SIS candidate, then request Belle's installer UI.

    Return value means only that AppArc accepted the file-open request,
    never that Symbian's installer completed or the app runs correctly.
    Do not use this pilot to upgrade the currently running E7 Bridge.
    """
    name = validate_push_name(source, 'installs')
    if name.lower().startswith('e7bridge'):
        raise BridgeError('Pilot deploy refuses an E7 Bridge self-upgrade')
    source_path = Path(source)
    if source_path.is_symlink() or not source_path.is_file():
        raise BridgeError('Deploy source must be a regular non-symlink SIS')
    if not (0 < source_path.stat().st_size <= ADMIN_MAX_BYTES):
        raise BridgeError('Deploy package must be 1 byte to 8 MiB')
    remote, size, digest = push_file(admin, source, 'installs')
    response = admin.send('LAUNCH {} {} {}'.format(name, size, digest))
    if response != 'LAUNCH_REQUESTED':
        raise BridgeError('Unexpected installer-launch acknowledgement')
    return remote, size, digest


def collect_processes(sock, max_entries=2000):
    """Fetch bounded pages, without controlling processes or remote files."""
    offset = 0
    found = []
    while offset <= max_entries:
        result = request(sock, 'PROCS {}'.format(offset))
        lines = result.split('\n')
        if not lines:
            raise BridgeError('Missing process list marker')
        tail = lines.pop()
        if not lines and not (tail == '[END]' or tail.startswith('[NEXT] ')):
            raise BridgeError('Invalid process list')
        if any(not line or len(line) > 150 for line in lines):
            raise BridgeError('Invalid process names in reply')
        found.extend(lines)
        if len(found) > max_entries:
            raise BridgeError('Process list exceeded safety limit')
        if tail == '[END]':
            return found
        match = re.fullmatch(r'\[NEXT\] (\d{1,4})', tail)
        if not match:
            raise BridgeError('Invalid process list pagination marker')
        next_offset = int(match.group(1))
        if next_offset != offset + len(lines) or next_offset <= offset:
            raise BridgeError('Non-progressing process list pagination')
        offset = next_offset
    raise BridgeError('Process list exceeded safety limit')


def save_process_snapshot(processes, directory=None):
    """Write to Linux only. Does not modify any file on the Nokia."""
    directory = Path(directory) if directory else SNAPSHOT_DIR
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    now = datetime.datetime.now(datetime.timezone.utc)
    stamp = now.strftime('%Y%m%dT%H%M%S%fZ')
    payload = {
        'format': 'e7-bridge-process-snapshot-v1',
        'timestamp_utc': now.isoformat(),
        'count': len(processes),
        'processes': processes,
        'note': 'Read-only TFindProcess names, not a service-dependency graph.',
    }
    path = directory / ('e7-processes-' + stamp + '.json')
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    fd = os.open(str(path), flags, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as output:
        json.dump(payload, output, ensure_ascii=False, indent=2)
        output.write('\n')
    return path



def parse_metrics(text):
    """Decode a tiny, fixed-schema set of raw Symbian read-only readings.

    'unavailable' must remain null; never fabricate battery percent or RAM.
    """
    found = {}
    for line in text.splitlines():
        match = re.fullmatch(r'([a-z_]+)=(unavailable|-?[0-9]{1,12})', line)
        if not match:
            raise BridgeError('Invalid telemetry field')
        field, value = match.groups()
        if field not in METRIC_FIELDS or field in found:
            raise BridgeError('Unknown or repeated telemetry field')
        parsed = None if value == 'unavailable' else int(value)
        if parsed is not None:
            if field.startswith('ram_') and not 0 <= parsed <= 2**32:
                raise BridgeError('RAM telemetry outside permitted range')
            if not field.startswith('ram_') and not -10000 <= parsed <= 10000:
                raise BridgeError('Battery telemetry outside permitted range')
        found[field] = parsed
    if set(found) != set(METRIC_FIELDS):
        raise BridgeError('Incomplete telemetry reply')
    return {name: found[name] for name in METRIC_FIELDS}


def collect_diagnostics(sock):
    """Queries only METRICS and bounded PROCS; results are not atomic."""
    start = datetime.datetime.now(datetime.timezone.utc)
    metrics = parse_metrics(request(sock, 'METRICS'))
    processes = collect_processes(sock)
    end = datetime.datetime.now(datetime.timezone.utc)
    return {
        'timestamp_utc': start.isoformat(),
        'finished_utc': end.isoformat(),
        'process_count': len(processes),
        'processes': processes,
        'metrics': metrics,
    }


def snapshot_directory(directory=None):
    path = Path(directory) if directory is not None else SNAPSHOT_DIR
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    return path


def private_json_file(directory, prefix, suffix, payload):
    """Create a host-only, owner-readable report without overwriting files."""
    directory = snapshot_directory(directory)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    path = directory / (prefix + stamp + suffix)
    fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as output:
        json.dump(payload, output, ensure_ascii=False, indent=2)
        output.write('\n')
    return path


def save_diagnostic_snapshot(sample, directory=None):
    payload = {
        'format': 'e7-bridge-diagnostic-snapshot-v1',
        'note': 'RAM in bytes; battery readings are raw vendor values, not percent. Process list is not atomic.',
        **sample,
    }
    return private_json_file(directory, 'e7-diagnostic-', '.json', payload)


def process_deltas(before, after):
    """Counter-based comparison preserves duplicate process-instance names."""
    a = Counter(before)
    b = Counter(after)
    return {
        'before_count': len(before),
        'after_count': len(after),
        'started': sorted((b - a).elements()),
        'stopped': sorted((a - b).elements()),
    }


def load_snapshot_processes(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if data.get('format') not in (
        'e7-bridge-process-snapshot-v1', 'e7-bridge-diagnostic-snapshot-v1'
    ):
        raise BridgeError('Unsupported snapshot format: {}'.format(path))
    names = data.get('processes')
    if not isinstance(names, list) or len(names) > 2000 or any(
        not isinstance(name, str) or not name or len(name) > 150 for name in names
    ):
        raise BridgeError('Invalid process names in snapshot: {}'.format(path))
    return names


def latest_snapshot_diff(directory=None):
    directory = snapshot_directory(directory)
    files = sorted(list(directory.glob('e7-processes-*.json')) +
                   list(directory.glob('e7-diagnostic-*.json')),
                   key=lambda path: path.name.rsplit('-', 1)[-1])
    if len(files) < 2:
        raise BridgeError('Need two saved snapshots (ps save or capture) before diff')
    earlier, later = files[-2:]
    changes = process_deltas(load_snapshot_processes(earlier), load_snapshot_processes(later))
    return earlier, later, changes


def record_diagnostics(sock, count=3, interval=10, directory=None, sleeper=time.sleep):
    """Foreground recorder: bounded sampling, host-only JSONL, no phone writes.

    Entries are flushed individually, so earlier samples survive interruption.
    """
    if not (2 <= count <= 12 and 5 <= interval <= 120 and (count-1)*interval <= 600):
        raise BridgeError('Recording limits exceeded')
    directory = snapshot_directory(directory)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    path = directory / ('e7-recording-' + stamp + '.jsonl')
    captures = []
    fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as output:
            for idx in range(count):
                if idx:
                    sleeper(interval)
                sample = collect_diagnostics(sock)
                sample['format'] = 'e7-bridge-recording-sample-v1'
                sample['index'] = idx + 1
                sample['requested_interval_seconds'] = interval
                json.dump(sample, output, ensure_ascii=False)
                output.write('\n')
                output.flush()
                captures.append(sample)
                print('Captured sample {}/{} ({} processes)'.format(
                    idx+1, count, sample['process_count']))
    except (KeyboardInterrupt, OSError, BridgeError):
        print('Recording stopped; completed samples retained at:', path)
        raise
    return path, captures


def print_process_diff(changes):
    print('Process entries: {} -> {}'.format(
        changes['before_count'], changes['after_count']))
    print('Appeared ({}):'.format(len(changes['started'])))
    for name in changes['started']:
        print('  +', name)
    print('Disappeared ({}):'.format(len(changes['stopped'])))
    for name in changes['stopped']:
        print('  -', name)
    if not changes['started'] and not changes['stopped']:
        print('No differences in this pair of non-atomic snapshots.')


def repl(sock, admin=None):
    print('E7 authenticated. Commands: ping, info, drives, ls, stat, ps, metrics, capture, diff, record, pull probe, push LOCAL [inbox|installs], deploy FILE.sis, help, exit')
    while True:
        try:
            typed = input('e7> ')
        except (KeyboardInterrupt, EOFError):
            typed = 'exit'
            print()
        try:
            cmd = normalize_command(typed)
            if cmd is None:
                continue
            if cmd == 'HELP':
                print('ping          Check agent connection')
                print('info          Print basic device/app information')
                print('drives        Show permitted storage roots')
                print('ls [path]     List files (E:/ or C:/Data, protected directories excluded)')
                print('stat PATH     Inspect file or directory metadata (read-only)')
                print('ps [offset]   List 20 running Symbian processes from an offset')
                print('ps all        Fetch the full bounded process-name inventory')
                print('ps save       Save process-name inventory to a local JSON file')
                print('metrics       RAM in bytes and raw power-state readings (if available)')
                print('capture       Save telemetry and processes as local JSON (non-atomic)')
                print('diff          Compare the two latest saved process snapshots (host only)')
                print('record [N S]  Capture 2-12 samples, every 5-120 seconds (default 3 10)')
                print('pull probe    Receive only E:/KAI/INDEX.HTM (max 64 KiB; unencrypted LAN)')
                print('push FILE [inbox|installs]  Transfer <=8 MiB to E:/KAI/INBOX or E:/Installs (no overwrite)')
                print('deploy FILE.sis  Stage <=8 MiB SIS then ask Belle to launch installer (not confirmation)')
                print('exit          Close connection and stop bridge')
                continue
            if cmd == 'QUIT':
                try:
                    request(sock, 'QUIT')
                except (BridgeError, OSError):
                    pass
                return
            if cmd.startswith('PUSH '):
                if admin is None:
                    raise BridgeError('Push requires an authenticated administrative session')
                try:
                    args = shlex.split(cmd[5:])
                except ValueError as exc:
                    raise BridgeError('Invalid file quoting: {}'.format(exc))
                if len(args) not in (1, 2):
                    raise BridgeError('Usage: push LOCALFILE [inbox|installs]')
                remote, count, digest = push_file(admin, args[0], args[1].lower() if len(args) == 2 else 'inbox')
                print('Stored on Nokia:', remote)
                print('Verified remote receipt: {} bytes; SHA-256 {}'.format(count, digest))
                continue
            if cmd.startswith('DEPLOY '):
                if admin is None:
                    raise BridgeError('Deploy requires an authenticated administrative session')
                try:
                    args = shlex.split(cmd[7:])
                except ValueError as exc:
                    raise BridgeError('Invalid package path quoting: {}'.format(exc))
                if len(args) != 1:
                    raise BridgeError('Usage: deploy LOCALFILE.sis')
                remote, count, digest = deploy_package(admin, args[0])
                print('Staged on Nokia:', remote)
                print('Verified {} bytes; SHA-256 {}'.format(count, digest))
                print('Belle installer launch requested. THIS DOES NOT CONFIRM INSTALLATION.')
                print('Check installer UI, signing result, and a post-install file/version separately.')
                continue
            if cmd == 'PULL_PROBE':
                path, count, digest = pull_probe(sock)
                print('Saved read-only E7 fixture:', path)
                print('Validated: {} bytes; SHA-256 {}'.format(count, digest))
                print('Warning: HMAC authenticates the connection but does not encrypt its traffic.')
                continue
            if cmd == 'METRICS':
                values = parse_metrics(request(sock, 'METRICS'))
                for name, value in values.items():
                    print('{}: {}'.format(name, value if value is not None else 'unavailable'))
                continue
            if cmd == 'CAPTURE':
                sample = collect_diagnostics(sock)
                path = save_diagnostic_snapshot(sample)
                print('Saved read-only diagnostics:', path)
                print('{} process entries; battery values are raw, not percent'.format(sample['process_count']))
                continue
            if cmd == 'DIFF':
                old, new, changes = latest_snapshot_diff()
                print('From:', old.name)
                print('To:  ', new.name)
                print_process_diff(changes)
                continue
            if cmd.startswith('RECORD '):
                _, count, interval = cmd.split()
                try:
                    path, captures = record_diagnostics(sock, int(count), int(interval))
                except KeyboardInterrupt:
                    print('Recording interrupted. Bridge remains open.')
                    continue
                print('Recording saved:', path)
                if len(captures) >= 2:
                    print_process_diff(process_deltas(captures[0]['processes'], captures[-1]['processes']))
                continue
            if cmd in ('PS_ALL', 'PS_SAVE'):
                processes = collect_processes(sock)
                for name in processes:
                    print(name)
                print('{} process names'.format(len(processes)))
                if cmd == 'PS_SAVE':
                    print('Saved locally to:', save_process_snapshot(processes))
                continue
            reply = request(sock, cmd)
            print(reply if reply else '(OK)')
        except (BridgeError, UnicodeError) as exc:
            print('error:', exc)
        except OSError as exc:
            print('connection error:', exc)
            return


def run_server(bind, port, key):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((bind, port))
        server.listen(1)
        print('Listening on {}:{}'.format(bind, port))
        print('On the E7, open E7 Bridge and enter the Linux IP + pairing key.')
        print('Use only on a trusted local network; commands are not encrypted.')
        while True:
            connection, peer = server.accept()
            with connection:
                print('Incoming connection from {}:{}'.format(*peer))
                connection.settimeout(10.0)
                try:
                    nonce = authenticate(connection, key)
                except (BridgeError, OSError, UnicodeError) as exc:
                    print('Rejected:', exc)
                    continue
                connection.settimeout(15.0)
                repl(connection, AdminSession(connection, key, nonce))
                return


def main(argv=None):
    parser = argparse.ArgumentParser(description='E7 Bridge: minimal Symbian terminal link')
    sub = parser.add_subparsers(dest='mode', required=True)
    sub.add_parser('init', help='Create and show a local pairing key (one-time)')
    sub.add_parser('show-key', help='Print existing pairing key for typing into E7')
    serving = sub.add_parser('serve', help='Wait for a connection from E7')
    serving.add_argument('--bind', required=True, help='Your Debian LAN IPv4 address, e.g. 192.168.1.20')
    serving.add_argument('--port', type=int, default=PORT)
    opts = parser.parse_args(argv)
    try:
        if opts.mode == 'init':
            key = generate_key()
            print('Pairing key (type on E7):', key)
            print('Stored with mode 0600 at', SECRET_PATH)
        elif opts.mode == 'show-key':
            print(load_key())
        elif opts.mode == 'serve':
            if not 1024 <= opts.port <= 65535:
                parser.error('Port must be 1024-65535')
            run_server(opts.bind, opts.port, load_key())
        return 0
    except (BridgeError, OSError) as exc:
        print('error:', exc, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
