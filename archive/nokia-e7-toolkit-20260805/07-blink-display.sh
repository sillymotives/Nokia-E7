#!/usr/bin/env bash
set -euo pipefail
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
export E7_TOOLKIT_LIB="$script_dir/lib"

sudo --preserve-env=E7_PORT,E7_TOOLKIT_LIB python3 - <<'PY'
import os
import re
import sys
import time

sys.path.insert(0, os.environ["E7_TOOLKIT_LIB"])
from e7_at import available_ports, exchange, open_port

ports = available_ports()
if not ports:
    raise SystemExit("ERROR: no ttyACM port found; select Nokia Suite USB mode")

port = ports[0]
fd = open_port(port)
try:
    print(f"=== Nokia E7 display blink on {port} ===")
    before = exchange(fd, "AT+CBKLT?")
    match = re.search(r"\+CBKLT:\s*([012])", before)
    original = match.group(1) if match else "2"
    print("Original state:", before or "[no response]")
    print("Off:", exchange(fd, "AT+CBKLT=0") or "[no response]")
    time.sleep(2)
    print("Restore:", exchange(fd, f"AT+CBKLT={original}") or "[no response]")
    print("Final state:", exchange(fd, "AT+CBKLT?") or "[no response]")
finally:
    os.close(fd)
PY

