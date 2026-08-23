#!/usr/bin/env bash
# Nokia E7 Suite-mode capability probe, version 1.
# Sends a fixed set of status/test/read commands to the live Nokia interface 01.
# It does not read contact or message contents and has no set/control commands.

set -u
set -o pipefail

export LC_ALL=C
export LANG=C
umask 077

readonly SCRIPT_VERSION="1"

say() {
    printf '%s\n' "$*"
}

have() {
    command -v "$1" >/dev/null 2>&1
}

property() {
    local key="$1"
    awk -F= -v key="$key" '$1 == key { sub(/^[^=]*=/, ""); print; exit }'
}

readonly START_DIR="$(pwd -P)"
case "$START_DIR/" in
    /media/*|/run/media/*|/mnt/*)
        say "REFUSED: run from host storage, not $START_DIR"
        exit 2
        ;;
esac

readonly STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
readonly RUN_NAME="nokia-e7-suite-capabilities-${STAMP}"
readonly RUN_DIR="${START_DIR}/${RUN_NAME}"
readonly REPORT="${RUN_DIR}/suite-capabilities.txt"
readonly NEXT_FILE="${RUN_DIR}/NEXT.txt"
readonly BUNDLE="${START_DIR}/${RUN_NAME}.tar.gz"
readonly BUNDLE_SUM="${BUNDLE}.sha256"

mkdir -m 700 -- "$RUN_DIR" || exit 1

run_status=0
target_port=""

{
    say "NOKIA E7 SUITE CAPABILITY PROBE"
    say "Script version: $SCRIPT_VERSION"
    say "UTC start: $(date -u --iso-8601=seconds 2>/dev/null || date -u)"
    say "Policy: fixed status and capability queries only"
    say "Content boundary: no contact records and no message records"

    if ! have udevadm || ! have python3; then
        say "REFUSED: udevadm and python3 are required."
        run_status=2
    else
        shopt -s nullglob
        matches=()
        for port in /dev/ttyACM*; do
            props="$(udevadm info --query=property --name="$port" 2>/dev/null || true)"
            vendor="$(printf '%s\n' "$props" | property ID_VENDOR_ID)"
            product="$(printf '%s\n' "$props" | property ID_MODEL_ID)"
            model="$(printf '%s\n' "$props" | property ID_MODEL)"
            interface="$(printf '%s\n' "$props" | property ID_USB_INTERFACE_NUM)"
            driver="$(printf '%s\n' "$props" | property ID_USB_DRIVER)"
            if [[ "$vendor" == "0421" && "$product" == "0335" && "$model" == "E7-00" && "$interface" == "01" && "$driver" == "cdc_acm" ]]; then
                matches+=("$port")
            fi
        done

        say "Proven Nokia interface-01 port count: ${#matches[@]}"
        if ((${#matches[@]} != 1)); then
            say "REFUSED: expected exactly one live Nokia E7 interface-01 ACM port."
            run_status=3
        else
            target_port="${matches[0]}"
            say "target=$target_port interface=01 vendor=0421 product=0335 driver=cdc_acm"
        fi
    fi

    if ((run_status == 0)) && have fuser; then
        owners="$(fuser "$target_port" 2>/dev/null || true)"
        if [[ -n "$owners" ]]; then
            say "REFUSED: $target_port is already open by process(es): $owners"
            run_status=4
        fi
    fi

    if ((run_status == 0)); then
        if have systemctl; then
            mm_state="$(systemctl is-active ModemManager.service 2>/dev/null || true)"
            say "ModemManager state: ${mm_state:-unavailable}"
        fi

        runner=(python3)
        if [[ ! -r "$target_port" || ! -w "$target_port" ]]; then
            say "Port ACL does not grant access; requesting sudo for the serial child only."
            if sudo -v; then
                runner=(sudo -- python3)
            else
                say "REFUSED: serial access was not granted."
                run_status=5
            fi
        fi
    fi

    if ((run_status == 0)); then
        "${runner[@]}" - "$target_port" <<'PY'
import fcntl
import os
import re
import select
import subprocess
import sys
import termios
import time

QUERIES = (
    ("AT", 2.0),
    ("AT+CPAS", 2.0),
    ("AT+CBC", 2.0),
    ("AT+CFUN?", 2.0),
    ("AT+CPIN?", 2.0),
    ("AT+CSQ", 2.0),
    ("AT+CREG?", 2.0),
    ("AT+COPS?", 3.0),
    ("AT+CCLK?", 2.0),
    ("AT+CSCS?", 2.0),
    ("AT+CLAC", 10.0),
    ("AT+CPBS=?", 2.0),
    ("AT+CPBS?", 2.0),
    ("AT+CPBR=?", 2.0),
    ("AT+CMGF=?", 2.0),
    ("AT+CMGF?", 2.0),
    ("AT+CPMS=?", 2.0),
    ("AT+CPMS?", 2.0),
    ("AT+CKPD=?", 2.0),
    ("AT+CBKLT=?", 2.0),
    ("AT+CKPD?", 2.0),
    ("AT+CBKLT?", 2.0),
    ("AT+CMEC=?", 2.0),
    ("AT+CMEC?", 2.0),
)
ALLOWLIST = frozenset(command for command, _ in QUERIES)


def live_properties(port: str) -> dict[str, str]:
    result = subprocess.run(
        ["udevadm", "info", "--query=property", f"--name={port}"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    props = {}
    for line in result.stdout.splitlines():
        key, separator, value = line.partition("=")
        if separator:
            props[key] = value
    return props


def redact(text: str) -> str:
    return re.sub(r"(?<!\d)\d{15}(?!\d)", "[15-digit-id-redacted]", text)


def open_port(port: str) -> int:
    props = live_properties(port)
    expected = {
        "ID_VENDOR_ID": "0421",
        "ID_MODEL_ID": "0335",
        "ID_MODEL": "E7-00",
        "ID_USB_DRIVER": "cdc_acm",
        "ID_USB_INTERFACE_NUM": "01",
    }
    for key, value in expected.items():
        if props.get(key) != value:
            raise RuntimeError(f"live ownership check failed: {key}={props.get(key)!r}")

    fd = os.open(port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
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
    except Exception:
        os.close(fd)
        raise


def exchange(fd: int, command: str, timeout: float) -> str:
    if command not in ALLOWLIST:
        raise RuntimeError(f"command escaped allowlist: {command!r}")
    termios.tcflush(fd, termios.TCIOFLUSH)
    os.write(fd, (command + "\r").encode("ascii"))
    deadline = time.monotonic() + timeout
    response = bytearray()
    while time.monotonic() < deadline:
        ready, _, _ = select.select([fd], [], [], min(0.2, deadline - time.monotonic()))
        if ready:
            chunk = os.read(fd, 65536)
            if chunk:
                response.extend(chunk)
                upper = bytes(response).upper()
                if b"\r\nOK\r\n" in upper or b"\r\nERROR\r\n" in upper:
                    break
    decoded = response.decode("utf-8", "replace").replace("\x00", "").strip()
    return redact(decoded)


port = sys.argv[1]
fd = None
try:
    fd = open_port(port)
    successful_exchange = False
    for command, timeout in QUERIES:
        answer = exchange(fd, command, timeout)
        print(f"\n{command}")
        print(answer or "[no response]")
        if answer:
            successful_exchange = True
finally:
    if fd is not None:
        os.close(fd)

raise SystemExit(0 if successful_exchange else 6)
PY
        python_status=$?
        if ((python_status != 0)); then
            say "PARTIAL: capability query child exited $python_status."
            run_status=$python_status
        else
            say "PASS: Nokia interface 01 returned capability evidence."
        fi
    fi

    say "UTC finish: $(date -u --iso-8601=seconds 2>/dev/null || date -u)"
} >"$REPORT" 2>&1

cat >"$NEXT_FILE" <<EOF
Nokia E7 Suite capability probe finished with status ${run_status}.

Expected shareable files:
  ${RUN_NAME}.tar.gz
  ${RUN_NAME}.tar.gz.sha256
EOF

if ! have tar || ! have gzip || ! have sha256sum; then
    say "PARTIAL: report created, but packaging tools are unavailable."
    say "Report: $REPORT"
    exit 7
fi

tar -czf "$BUNDLE" -C "$START_DIR" "$RUN_NAME" || exit 8
(
    cd "$START_DIR" || exit 1
    sha256sum "$(basename "$BUNDLE")" >"$(basename "$BUNDLE_SUM")"
) || exit 9

if ((run_status == 0)); then
    say "PASS: Nokia E7 Suite capability probe complete."
else
    say "PARTIAL: Nokia E7 Suite capability probe status $run_status."
fi
say "Bundle:   $BUNDLE"
say "Checksum: $BUNDLE_SUM"
say "Only fixed status/test/read AT commands were transmitted."

exit "$run_status"

