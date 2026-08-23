#!/usr/bin/env bash
set -euo pipefail
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
sudo env "E7_PORT=${E7_PORT:-}" python3 "$script_dir/lib/e7_at.py" --timeout 2 \
    --banner "Nokia E7 live status" \
    AT AT+CPAS AT+CBC 'AT+CFUN?' 'AT+CPIN?' AT+CSQ 'AT+CREG?' 'AT+COPS?' 'AT+CCLK?' 'AT+CSCS?'
