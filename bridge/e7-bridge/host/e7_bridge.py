#!/usr/bin/env python3
"""E7 Bridge v0.3.0: Linux host for a user-operated, read-only Symbian agent.

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

PORT = 46270
MAX_LINE = 4096
PROTO = 'E7B1'
SECRET_PATH = Path.home() / '.config' / 'e7-bridge' / 'pairing-key'


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
    raise BridgeError('Supported: ping, info, drives, ls [E:/path], stat PATH, ps [offset|all|save], help, exit')


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
    directory = Path(directory) if directory else Path.home() / '.local' / 'share' / 'e7-bridge' / 'snapshots'
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


def repl(sock):
    print('E7 authenticated. Commands: ping, info, drives, ls, stat, ps, help, exit')
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
                print('exit          Close connection and stop bridge')
                continue
            if cmd == 'QUIT':
                try:
                    request(sock, 'QUIT')
                except (BridgeError, OSError):
                    pass
                return
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
                    authenticate(connection, key)
                except (BridgeError, OSError, UnicodeError) as exc:
                    print('Rejected:', exc)
                    continue
                connection.settimeout(15.0)
                repl(connection)
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
