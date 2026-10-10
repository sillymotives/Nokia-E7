#!/usr/bin/env bash
# Start host v0.9.0 controller for existing v0.8 phone from ANY working directory.
# Does not change the E7 and does not expose the bridge on 0.0.0.0.
set -euo pipefail

project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
if [[ $# -gt 1 || ${1:-} == --help || ${1:-} == -h ]]; then
    echo "Usage: $0 [SANCTUARY_IPV4]"; exit 0
fi
bind=${1:-}
if [[ -z $bind ]] && command -v ip >/dev/null 2>&1; then
    # Local routing lookup; it doesn't contact the Internet.
    bind=$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{ for (i=1; i<NF; i++) if ($i=="src") { print $(i+1); exit } }' || true)
fi
if [[ -z $bind ]]; then
    echo "Couldn't determine Sanctuary's LAN IP automatically." >&2
    echo "Choose its IPv4 address from: $(hostname -I 2>/dev/null || echo unavailable)" >&2
    echo "Then run: $0 YOUR_SANCTUARY_IPV4" >&2
    exit 1
fi
python3 - "$bind" <<'PY'
import ipaddress,sys
try:
    ip = ipaddress.IPv4Address(sys.argv[1])
    if ip.is_loopback or ip.is_multicast or ip.is_unspecified:
        raise ValueError('Must bind a real unicast interface address')
except ValueError as exc:
    raise SystemExit('Invalid Sanctuary IPv4 address: '+str(exc))
PY
cd -- "$project"
echo "Sanctuary bridge host v0.9.0 for E7 agent v0.8.0 listening on $bind (enter this IPv4 on E7 if different)."
exec python3 host/e7_bridge.py serve --bind "$bind"
