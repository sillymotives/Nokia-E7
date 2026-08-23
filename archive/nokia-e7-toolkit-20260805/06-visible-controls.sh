#!/usr/bin/env bash
set -euo pipefail
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
sudo env "E7_PORT=${E7_PORT:-}" python3 "$script_dir/lib/e7_at.py" --timeout 2 \
    --banner "Nokia E7 visible-control capabilities" \
    'AT+CKPD=?' 'AT+CBKLT=?' 'AT+CKPD?' 'AT+CBKLT?' 'AT+CMEC=?' 'AT+CMEC?'
