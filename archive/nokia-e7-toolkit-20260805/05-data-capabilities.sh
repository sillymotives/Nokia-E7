#!/usr/bin/env bash
set -euo pipefail
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
sudo env "E7_PORT=${E7_PORT:-}" python3 "$script_dir/lib/e7_at.py" --timeout 8 \
    --banner "Nokia E7 data-interface capabilities" \
    AT AT+CLAC 'AT+CPBS=?' 'AT+CPBS?' 'AT+CPBR=?' 'AT+CMGF=?' 'AT+CMGF?' 'AT+CPMS=?' 'AT+CPMS?'
