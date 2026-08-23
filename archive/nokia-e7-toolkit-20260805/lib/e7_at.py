#!/usr/bin/env python3
"""Small dependency-free AT transport for the Nokia E7 toolkit."""

from __future__ import annotations

import argparse
import glob
import os
import select
import sys
import termios
import time


def available_ports() -> list[str]:
    override = os.environ.get("E7_PORT")
    if override:
        return [override]
    return sorted(glob.glob("/dev/ttyACM*"))


def open_port(port: str) -> int:
    fd = os.open(port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    attrs = termios.tcgetattr(fd)
    attrs[0] = termios.IGNPAR
    attrs[1] = 0
    attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
    attrs[3] = 0
    attrs[4] = termios.B115200
    attrs[5] = termios.B115200
    attrs[6][termios.VMIN] = 0
    attrs[6][termios.VTIME] = 0
    termios.tcsetattr(fd, termios.TCSANOW, attrs)
    termios.tcflush(fd, termios.TCIOFLUSH)
    return fd


def exchange(fd: int, command: str, timeout: float = 2.0) -> str:
    termios.tcflush(fd, termios.TCIOFLUSH)
    os.write(fd, (command + "\r").encode("ascii"))
    deadline = time.monotonic() + timeout
    response = bytearray()
    while time.monotonic() < deadline:
        ready, _, _ = select.select([fd], [], [], min(0.2, deadline - time.monotonic()))
        if ready:
            chunk = os.read(fd, 16384)
            if chunk:
                response.extend(chunk)
    return response.decode("utf-8", "replace").replace("\x00", "").strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run AT queries against Nokia E7 serial interfaces")
    parser.add_argument("commands", nargs="+", help="AT commands to send")
    parser.add_argument("--all-ports", action="store_true", help="probe every ttyACM port")
    parser.add_argument("--timeout", type=float, default=2.0, help="seconds to wait per command")
    parser.add_argument("--banner", default="Nokia E7 AT probe")
    args = parser.parse_args()

    ports = available_ports()
    if not ports:
        print("ERROR: no /dev/ttyACM devices found; select Nokia Suite USB mode", file=sys.stderr)
        return 2
    if not args.all_ports:
        ports = ports[:1]

    print(f"=== {args.banner} ===")
    for port in ports:
        print(f"\n--- {port} ---")
        fd = None
        try:
            fd = open_port(port)
            for command in args.commands:
                answer = exchange(fd, command, args.timeout)
                print(f"\n{command}")
                print(answer or "[no response]")
        except OSError as exc:
            print(f"Probe error: {exc}")
        finally:
            if fd is not None:
                os.close(fd)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

