#!/usr/bin/env python3
"""A fake E7 for exercising the host terminal on Linux without a phone.
Not an installer and never touches the real device.
"""
import argparse
from pathlib import Path
import base64
import importlib.util
import socket

PATH = Path(__file__).resolve().parents[1] / 'host' / 'e7_bridge.py'
spec = importlib.util.spec_from_file_location('e7_bridge', PATH)
e7 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e7)


def main():
    parser = argparse.ArgumentParser(description='Fake E7 for local protocol testing')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=e7.PORT)
    args = parser.parse_args()
    key = e7.load_key()
    with socket.create_connection((args.host, args.port), timeout=5) as conn:
        conn.settimeout(30)
        header = e7.recv_line(conn)
        prefix, challenge, nonce = header.split(' ')
        assert (prefix, challenge) == ('E7B1', 'CHALLENGE')
        e7.send_line(conn, 'E7B1 AUTH ' + e7.expected_auth(key, 'device:' + nonce))
        expected = 'E7B1 READY ' + e7.expected_auth(key, 'host:' + nonce)
        assert e7.recv_line(conn) == expected, 'Host did not authenticate'
        print('Mock E7 authenticated; exercise the Linux terminal now.')
        while True:
            command = e7.recv_line(conn)
            if command == 'PING':
                e7.send_line(conn, 'OK PONG (SIMULATOR)')
            elif command == 'INFO':
                e7.send_line(conn, 'OK SIMULATED Nokia E7 / Symbian Belle')
            elif command.startswith('PROCS '):
                import base64
                offset = int(command.split()[1])
                names = ['sysmon.exe[0]', 'sysap.exe[3]', 'hwrmserver.exe[1]',
                         'iaupdatedaemon.exe[4]', 'E7Bridge.exe[5]']
                page = names[offset:offset+20]
                marker = '[NEXT] ' + str(offset+len(page)) if offset+len(page)<len(names) else '[END]'
                text = '\n'.join(page+[marker])
                e7.send_line(conn, 'B64 ' + base64.b64encode(text.encode('ascii')).decode('ascii'))
            elif command == 'DRIVES':
                data = '[D] E:/\n[D] C:/Data'
                e7.send_line(conn, 'B64 ' + base64.b64encode(data.encode('utf-8')).decode('ascii'))
            elif command.startswith('STAT '):
                data = 'directory | path=E:/Images'
                e7.send_line(conn, 'B64 ' + base64.b64encode(data.encode('utf-8')).decode('ascii'))
            elif command.startswith('LIST '):
                data = '[D] Images\n[D] Installs\n[F] E7-bridge-test.txt'
                e7.send_line(conn, 'B64 ' + base64.b64encode(data.encode('utf-8')).decode('ascii'))
            elif command == 'QUIT':
                e7.send_line(conn, 'OK BYE')
                break
            else:
                e7.send_line(conn, 'ERR UNKNOWN_COMMAND')


if __name__ == '__main__':
    main()
