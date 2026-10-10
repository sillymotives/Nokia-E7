#!/usr/bin/env python3
"""E7 Bridge v0.8.1: Linux host for a user-operated Symbian diagnostic and admin agent.

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
BATCH_JOURNAL_DIR = Path.home() / '.local' / 'share' / 'e7-bridge' / 'batches'
BATCH_ADMIN_MAX_FILE = 8192
BATCH_ADMIN_MAX_STEPS = 40
BATCH_ADMIN_TOTAL_BYTES = 32 * 1024 * 1024
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


def normalize_uid(raw):
    """Canonical SIS package UID (not executable/SID), exactly 32 bits."""
    match = re.fullmatch(r'(?:0[xX])?([0-9a-fA-F]{8})', raw.strip())
    if not match:
        raise BridgeError('Package UID must be eight hexadecimal digits, optionally 0x-prefixed')
    return match.group(1).upper()


def parse_package_detail(response, expected_uid):
    """Strictly parse one native SIS registry entry; no menu-icon heuristics."""
    uid = normalize_uid(expected_uid)
    lines = response.split('\n')
    if len(lines) < 2 or lines[0] != 'uid=0x' + uid:
        raise BridgeError('Invalid package registry UID in reply')
    if lines[1] == 'installed=no' and len(lines) == 2:
        return {'uid': '0x' + uid, 'installed': False}
    if len(lines) != 4 or lines[1] != 'installed=yes':
        raise BridgeError('Invalid package registry status')
    version = lines[2]
    name = lines[3]
    if not version.startswith('version=') or re.fullmatch(r'[0-9]{1,5}(?:\.[0-9]{1,5}){2}', version[8:]) is None:
        raise BridgeError('Invalid package registry version')
    if not name.startswith('name=') or not (1 <= len(name[5:]) <= 100):
        raise BridgeError('Invalid package registry name')
    if any(ord(c) < 32 or ord(c) > 126 for c in name[5:]):
        raise BridgeError('Unexpected package registry name characters')
    return {'uid': '0x' + uid, 'installed': True, 'version': version[8:], 'name': name[5:]}


def package_detail(sock, uid):
    uid = normalize_uid(uid)
    return parse_package_detail(request(sock, 'PKG ' + uid), uid)


def verify_package(sock, uid, version):
    if re.fullmatch(r'[0-9]{1,5}(?:\.[0-9]{1,5}){2}', version) is None:
        raise BridgeError('Expected version must be MAJOR.MINOR.BUILD')
    detail = package_detail(sock, uid)
    return detail, detail['installed'] and detail['version'] == version


def parse_package_page(reply, offset):
    """Decode bounded native list pages, reject malformed or stalled paging."""
    lines = reply.split('\n')
    if len(lines) < 2 or not re.fullmatch(r'total=[0-9]{1,4}', lines[0]):
        raise BridgeError('Invalid package-page header')
    total = int(lines[0][6:])
    if total > 2000:
        raise BridgeError('Package registry exceeds 2000-entry limit')
    marker = lines[-1]
    if marker == '[END]':
        following = None
    elif re.fullmatch(r'\[NEXT\] [0-9]{1,4}', marker):
        following = int(marker[7:])
    else:
        raise BridgeError('Invalid package-page continuation')
    rows = []
    for row in lines[1:-1]:
        bits = row.split('|', 2)
        if len(bits) != 3 or not re.fullmatch(r'0x[0-9A-F]{8}', bits[0]):
            raise BridgeError('Invalid package-list UID')
        if re.fullmatch(r'[0-9]{1,5}(?:\.[0-9]{1,5}){2}', bits[1]) is None:
            raise BridgeError('Invalid package-list version')
        if not (1 <= len(bits[2]) <= 100) or any(ord(x) < 32 or ord(x) > 126 for x in bits[2]):
            raise BridgeError('Invalid package-list name')
        rows.append({'uid': bits[0], 'version': bits[1], 'name': bits[2]})
    if len(rows) > 12 or (offset < total and len(rows) == 0):
        raise BridgeError('Invalid package page length')
    if following is not None and (following <= offset or following != offset + len(rows) or following >= total):
        raise BridgeError('Invalid package continuation offset')
    if following is None and offset + len(rows) < total:
        raise BridgeError('Package page ended before all packages')
    if following is not None and len(rows) != 12:
        raise BridgeError('Non-final package page is incomplete')
    return total, rows, following


def collect_packages(sock, limit=2000):
    """Read read-only inventory, max 2000 entries / 167 fixed pages."""
    offset, found, total = 0, [], None
    while True:
        next_total, page, following = parse_package_page(request(sock, 'PKGS {}'.format(offset)), offset)
        if total is not None and next_total != total:
            raise BridgeError('Package registry changed during listing; retry')
        total = next_total
        found.extend(page)
        if len(found) > limit:
            raise BridgeError('Package listing exceeds configured limit')
        # Race/malformed response detection: native side sorts UID pages.
        uids = [row['uid'] for row in found]
        if any(uids[i] >= uids[i+1] for i in range(len(uids)-1)):
            raise BridgeError('Package registry changed or repeated an entry during listing')
        if following is None:
            if len(found) != total:
                raise BridgeError('Incomplete package listing')
            return found
        offset = following


BATCH_SAFE = frozenset(('PING', 'INFO', 'DRIVES', 'METRICS'))


def read_batch_file(source):
    """Explicit bounded command file: read-only to avoid paste-triggered writes."""
    path = Path(source)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 8192:
        raise BridgeError('Batch must be a regular non-symlink UTF-8 text file <=8 KiB')
    try:
        content = path.read_text(encoding='utf-8')
    except UnicodeError:
        raise BridgeError('Batch file must be UTF-8')
    commands = []
    for line in content.splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        command = normalize_command(line)
        if not (command in BATCH_SAFE or command.startswith(('LIST ', 'STAT ', 'PKGS ', 'PKG ', 'VERIFY '))):
            raise BridgeError('Batch permits only read-only device inspections (no push/deploy/exit)')
        commands.append((line.strip(), command))
        if len(commands) > 40:
            raise BridgeError('Batch permits a maximum of 40 commands')
    if not commands:
        raise BridgeError('Batch file has no commands')
    return commands


def normalize_command(text):
    # A pasted multi-command blob must not become an accidental device path.
    # Use the explicit read-only `batch FILE` mode for multiple commands.
    if any(c in text for c in ('\r', '\n', '\x00', '\x1b')):
        raise BridgeError('Paste one command at a time, or use batch FILE')
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
    if verb in ('packages', 'pkgs'):
        if not arg:
            return 'PKGS 0'
        if arg.lower() == 'all':
            return 'PKGS_ALL'
        if not arg.isascii() or not arg.isdecimal() or int(arg) > 2000:
            raise BridgeError('packages offset must be between 0 and 2000')
        return 'PKGS {}'.format(int(arg))
    if verb == 'pkg':
        return 'PKG ' + normalize_uid(arg)
    if verb == 'verify':
        items = arg.split()
        if len(items) != 2 or re.fullmatch(r'[0-9]{1,5}(?:\.[0-9]{1,5}){2}', items[1]) is None:
            raise BridgeError('Usage: verify UID MAJOR.MINOR.BUILD')
        return 'VERIFY {} {}'.format(normalize_uid(items[0]), items[1])
    if verb == 'batch' and arg:
        if arg.startswith('--write '):
            return 'BATCH_WRITE ' + arg[8:]
        if arg.startswith('--plan '):
            return 'BATCH_PLAN ' + arg[7:]
        if arg.startswith('--resume '):
            return 'BATCH_RESUME ' + arg[9:]
        if arg in ('--write', '--plan', '--resume'):
            raise BridgeError('batch option needs a manifest (and resume journal when applicable)')
        return 'BATCH ' + arg
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
    raise BridgeError('Supported: ping, info, drives, ls, stat, ps, metrics, packages [offset|all], pkg UID, verify UID VERSION, batch FILE, batch --plan FILE, batch --write FILE, batch --resume JOURNAL FILE, capture, diff, record, pull probe, push LOCAL [inbox|installs], deploy FILE.sis, help, exit')


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


def push_file(admin, source, bucket='inbox', expected_digest=None, expected_size=None):
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
        if (expected_digest is not None and expected != expected_digest) or (
                expected_size is not None and size != expected_size):
            raise BridgeError('Local source changed since batch preflight; not uploading')
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


def deploy_package(admin, source, expected_digest=None, expected_size=None):
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
    remote, size, digest = push_file(admin, source, 'installs',
                                      expected_digest=expected_digest, expected_size=expected_size)
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


def run_batch_read_step(sock, command, assert_verify=False):
    """Display one permitted read-only step; assert registry checks in write jobs."""
    if command.startswith('VERIFY '):
        _, uid, version = command.split()
        detail, good = verify_package(sock, uid, version)
        message = ('VERIFIED ' if good else 'NOT VERIFIED ') + \
                  '{} version={} found={}'.format(detail['uid'], version, detail.get('version', 'not installed'))
        print(message)
        if assert_verify and not good:
            raise BridgeError('Batch verification failed; stopping before subsequent writes')
    elif command.startswith('PKG '):
        print(package_detail(sock, command[4:]))
    elif command.startswith('PKGS '):
        total, rows, following = parse_package_page(request(sock, command), int(command[5:]))
        for row in rows:
            print('{uid}  {version}  {name}'.format(**row))
        print('{} packages total; {}'.format(total, '[END]' if following is None else
                                              'next offset {}'.format(following)))
    elif command == 'PKGS_ALL':
        rows = collect_packages(sock)
        for row in rows:
            print('{uid}  {version}  {name}'.format(**row))
        print('{} packages total'.format(len(rows)))
    elif command == 'METRICS':
        for field, value in parse_metrics(request(sock, 'METRICS')).items():
            print('{}: {}'.format(field, value if value is not None else 'unavailable'))
    else:
        print(request(sock, command) or '(OK)')


def _read_admin_manifest(source):
    path = Path(source).expanduser().absolute()
    if path.is_symlink() or not path.is_file() or path.stat().st_size > BATCH_ADMIN_MAX_FILE:
        raise BridgeError('Write batch must be a regular non-symlink UTF-8 file <=8 KiB')
    try:
        data = path.read_bytes()
        source_text = data.decode('utf-8', 'strict')
    except UnicodeError:
        raise BridgeError('Write batch must contain valid UTF-8')
    if len(data) > BATCH_ADMIN_MAX_FILE:
        raise BridgeError('Write batch exceeds the 8 KiB limit')
    return path, data, source_text


def _preflight_upload(source, bucket):
    """Capture a source fingerprint without sending a single byte to the phone."""
    name = validate_push_name(str(source), bucket)
    if source.is_symlink() or not source.is_file():
        raise BridgeError('Write batch source must be a regular non-symlink file: {}'.format(source))
    with source.open('rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > ADMIN_MAX_BYTES:
            raise BridgeError('Write batch source must be a regular file <=8 MiB')
        if bucket == 'installs' and before.st_size == 0:
            raise BridgeError('Cannot deploy an empty SIS')
        digest = hashlib.sha256()
        while True:
            chunk = stream.read(65536)
            if not chunk:
                break
            digest.update(chunk)
        after = os.fstat(stream.fileno())
        if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
            raise BridgeError('Local file changed during preflight')
    return {'source': str(source), 'bucket': bucket, 'name': name, 'size': before.st_size,
            'sha256': digest.hexdigest(),
            'remote': 'E:/Installs/' + name if bucket == 'installs' else 'E:/KAI/INBOX/' + name}


def prepare_write_batch(source):
    """Validate an entire explicit write job before any on-device action.

    A single signed admin session authenticates each write, but the job itself is
    NOT transactional. Local files are resolved relative to the manifest folder.
    """
    manifest, content, text = _read_admin_manifest(source)
    entries, targets, transfer_bytes = [], set(), 0
    for lineno, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        cmd = normalize_command(line)
        record = {'line': lineno, 'text': line.strip(), 'command': cmd, 'type': 'read'}
        if cmd.startswith(('PUSH ', 'DEPLOY ')):
            verb = 'deploy' if cmd.startswith('DEPLOY ') else 'push'
            try:
                args = shlex.split(cmd.split(' ', 1)[1])
            except ValueError as exc:
                raise BridgeError('Line {}: invalid shell-style path quoting: {}'.format(lineno, exc))
            if (verb == 'deploy' and len(args) != 1) or (verb == 'push' and len(args) not in (1, 2)):
                raise BridgeError('Line {}: bad push/deploy arguments'.format(lineno))
            bucket = 'installs' if verb == 'deploy' else (args[1].lower() if len(args) == 2 else 'inbox')
            local = Path(args[0]).expanduser()
            if not local.is_absolute():
                local = manifest.parent / local
            if verb == 'deploy' and local.name.lower().startswith('e7bridge'):
                raise BridgeError('Batch refuses self-upgrading the running E7 Bridge')
            transfer = _preflight_upload(local, bucket)
            if transfer['remote'].casefold() in targets:
                raise BridgeError('Batch repeats a destination: {}'.format(transfer['remote']))
            targets.add(transfer['remote'].casefold())
            transfer_bytes += transfer['size']
            if transfer_bytes > BATCH_ADMIN_TOTAL_BYTES:
                raise BridgeError('Write batch total uploads exceed 32 MiB')
            record.update(transfer)
            record['type'] = verb
        elif not (cmd in BATCH_SAFE or cmd == 'PKGS_ALL' or
                  cmd.startswith(('LIST ', 'STAT ', 'PKGS ', 'PKG ', 'VERIFY '))):
            raise BridgeError('Line {}: unsupported write-batch operation: {}'.format(lineno, line.strip()))
        if entries and entries[-1]['type'] == 'deploy':
            raise BridgeError('Installer launch must be the last batch step; verify after installing in a later job')
        entries.append(record)
        if len(entries) > BATCH_ADMIN_MAX_STEPS:
            raise BridgeError('Write batch permits at most 40 steps')
    if not entries:
        raise BridgeError('Write batch is empty')
    if not any(step['type'] != 'read' for step in entries):
        raise BridgeError('Write batch has no writes: use ordinary batch FILE')
    # Include all transfer fingerprints so resume cannot silently use changed data.
    serial = json.dumps({'manifest_sha256': hashlib.sha256(content).hexdigest(),
                         'steps': entries}, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return {'path': str(manifest), 'sha256': hashlib.sha256(serial).hexdigest(),
            'steps': entries, 'upload_bytes': transfer_bytes}


def _batch_record(stream, data):
    stream.write(json.dumps(data, sort_keys=True, separators=(',', ':')) + '\n')
    stream.flush()
    os.fsync(stream.fileno())


def _new_batch_journal(plan, directory):
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(str(directory), 0o700)
    for attempt in range(5):
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        p = directory / ('e7-batch-' + stamp + '-' + secrets.token_hex(4) + '.jsonl')
        try:
            fd = os.open(str(p), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            continue
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            _batch_record(stream, {'event': 'plan', 'sha256': plan['sha256'],
                                   'manifest': plan['path'], 'count': len(plan['steps']),
                                   'upload_bytes': plan['upload_bytes']})
        return p
    raise BridgeError('Unable to allocate a unique batch receipt')


def _resume_batch_journal(plan, receipt, directory):
    directory = directory.resolve()
    path = Path(receipt).expanduser().absolute()
    if (path.is_symlink() or not path.is_file() or path.parent.resolve() != directory or
            path.stat().st_size > 65536 or path.stat().st_mode & 0o077):
        raise BridgeError('Resume requires an owner-only batch receipt from the bridge journal directory')
    try:
        entries = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
    except (UnicodeError, ValueError):
        raise BridgeError('Invalid journal syntax')
    if not entries or entries[0].get('event') != 'plan' or entries[0].get('sha256') != plan['sha256']:
        raise BridgeError('Batch plan/files changed; cannot resume this journal')
    status = {}
    for event in entries[1:]:
        index = event.get('step')
        if not isinstance(index, int) or not 0 <= index < len(plan['steps']):
            raise BridgeError('Invalid batch journal step number')
        if event.get('event') not in ('started', 'done', 'failed'):
            raise BridgeError('Invalid journal step event')
        status[index] = event['event']
    for index, state in status.items():
        if plan['steps'][index]['type'] != 'read' and state != 'done':
            raise BridgeError('Ambiguous interrupted write at step {}: inspect the E7 before creating a new job'.format(index+1))
    return path, status


def _confirm_prior_upload(sock, step):
    # Authenticated receipt from the previous run was recorded on disk; STAT
    # confirms only size/presence today, not cryptographic integrity today.
    response = request(sock, 'STAT ' + step['remote'])
    expected = 'file | bytes={} | path={}'.format(step['size'], step['remote'])
    if response != expected:
        raise BridgeError('Previously staged file no longer matches its recorded size/path')


def run_write_batch(sock, admin, plan, receipt=None, journal_dir=None):
    """Execute a preflighted job, log each step, fail closed on ambiguity.

    Per-file transfers are atomic. Whole jobs are not atomic and deployment is
    only a launch request. Resume validates the manifest and local SHA hashes.
    """
    if admin is None:
        raise BridgeError('Write batch requires an authenticated admin session')
    directory = Path(journal_dir) if journal_dir is not None else BATCH_JOURNAL_DIR
    if receipt is None:
        journal = _new_batch_journal(plan, directory)
        status = {}
    else:
        journal, status = _resume_batch_journal(plan, receipt, directory)
    print('Batch receipt:', journal)
    with journal.open('a', encoding='utf-8') as log:
        for i, step in enumerate(plan['steps']):
            print('[{}/{}] e7> {}'.format(i+1, len(plan['steps']), step['text']))
            if status.get(i) == 'done' and step['type'] != 'read':
                if step['type'] == 'push':
                    _confirm_prior_upload(sock, step)
                    print('Already staged; previous authenticated receipt and current size verified.')
                elif step['type'] == 'deploy':
                    print('Installer launch was previously requested; no duplicate launch.')
                continue
            _batch_record(log, {'event': 'started', 'step': i, 'kind': step['type']})
            try:
                if step['type'] == 'push':
                    remote, size, digest = push_file(admin, step['source'], step['bucket'],
                                                     expected_digest=step['sha256'], expected_size=step['size'])
                    if (remote, size, digest) != (step['remote'], step['size'], step['sha256']):
                        raise BridgeError('Upload receipt differed from the preflighted plan')
                    _confirm_prior_upload(sock, step)
                    print('Staged:', remote, '|', size, 'bytes | SHA-256', digest)
                elif step['type'] == 'deploy':
                    remote, size, digest = deploy_package(admin, step['source'],
                                                          expected_digest=step['sha256'], expected_size=step['size'])
                    if (remote, size, digest) != (step['remote'], step['size'], step['sha256']):
                        raise BridgeError('Deployment receipt differed from the preflighted plan')
                    print('Installer launch requested for', remote, '(not installation confirmation)')
                else:
                    run_batch_read_step(sock, step['command'], assert_verify=True)
            except (BridgeError, OSError, UnicodeError) as exc:
                _batch_record(log, {'event': 'failed', 'step': i, 'reason': str(exc)[:300]})
                print('Batch stopped at step {}. Receipt: {}'.format(i+1, journal))
                raise
            _batch_record(log, {'event': 'done', 'step': i})
    print('Batch finished. Receipt:', journal)
    if plan['steps'][-1]['type'] == 'deploy':
        print('Installer only LAUNCHED; confirm installation through Belle and a separate registry check.')
    return journal


def describe_write_batch(plan):
    print('Preflight OK: {} steps, {} upload bytes'.format(len(plan['steps']), plan['upload_bytes']))
    print('Plan SHA-256:', plan['sha256'])
    for i, step in enumerate(plan['steps']):
        if step['type'] == 'read':
            print(' {:02d} READ   {}'.format(i+1, step['text']))
        else:
            print(' {:02d} {:6s} {} -> {} ({} bytes, SHA-256 {})'.format(
                i+1, step['type'].upper(), step['source'], step['remote'], step['size'], step['sha256']))
    print('Each file commit is atomic; THE WHOLE BATCH IS NOT TRANSACTIONAL.')
    print('An interrupted write requires manual investigation, not blind retry.')


def repl(sock, admin=None):
    print('E7 authenticated. Commands: ping, info, drives, ls, stat, ps, metrics, packages, pkg, verify, batch, batch --plan, batch --write, batch --resume, capture, diff, record, pull probe, push, deploy, help, exit')
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
                print('packages [offset|all] List native installed SIS package UIDs/versions')
                print('pkg UID       Inspect a SIS package by 32-bit UID')
                print('verify UID VERSION  Confirm registry has exact MAJOR.MINOR.BUILD')
                print('batch FILE    Run up to 40 read-only terminal commands without multiline paste')
                print('batch --plan FILE    Preflight up to 40 steps including writes, no device changes')
                print('batch --write FILE   Execute read/write manifest, journal every step, no extra approvals')
                print('batch --resume JOURNAL FILE   Resume completed stages, never blindly retry uncertain writes')
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
            if cmd.startswith(('BATCH_PLAN ', 'BATCH_WRITE ', 'BATCH_RESUME ')):
                mode, value = cmd.split(' ', 1)
                try:
                    args = shlex.split(value)
                except ValueError as exc:
                    raise BridgeError('Bad batch argument quoting: {}'.format(exc))
                if (mode == 'BATCH_RESUME' and len(args) != 2) or (mode != 'BATCH_RESUME' and len(args) != 1):
                    raise BridgeError('Usage: batch --plan FILE | batch --write FILE | batch --resume JOURNAL FILE')
                plan = prepare_write_batch(args[-1])
                if mode == 'BATCH_PLAN':
                    describe_write_batch(plan)
                else:
                    if mode == 'BATCH_WRITE':
                        describe_write_batch(plan)
                    run_write_batch(sock, admin, plan, receipt=args[0] if mode == 'BATCH_RESUME' else None)
                continue
            if cmd.startswith('BATCH '):
                try:
                    parts = shlex.split(cmd[6:])
                except ValueError as exc:
                    raise BridgeError('Invalid batch-file quoting: {}'.format(exc))
                if len(parts) != 1:
                    raise BridgeError('Usage: batch LOCALFILE')
                for original, command in read_batch_file(parts[0]):
                    print('e7> {}'.format(original))
                    run_batch_read_step(sock, command)
                continue
            if cmd == 'PKGS_ALL':
                records = collect_packages(sock)
                for row in records:
                    print('{uid}  {version}  {name}'.format(**row))
                print('{} packages total'.format(len(records)))
                continue
            if cmd.startswith('PKGS '):
                offset = int(cmd[5:])
                total, rows, next_offset = parse_package_page(request(sock, cmd), offset)
                for row in rows:
                    print('{uid}  {version}  {name}'.format(**row))
                print('{} packages total; {}'.format(total, '[END]' if next_offset is None else 'next: packages {}'.format(next_offset)))
                continue
            if cmd.startswith('PKG '):
                detail = package_detail(sock, cmd[4:])
                print('Package {}: {}'.format(detail['uid'], 'not installed' if not detail['installed'] else
                                              '{} ({})'.format(detail['name'], detail['version'])))
                continue
            if cmd.startswith('VERIFY '):
                _, uid, version = cmd.split()
                detail, verified = verify_package(sock, uid, version)
                print(('VERIFIED: ' if verified else 'NOT VERIFIED: ') + '{} expected={} found={}'.format(
                    detail['uid'], version, detail.get('version', 'not installed')))
                continue
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
