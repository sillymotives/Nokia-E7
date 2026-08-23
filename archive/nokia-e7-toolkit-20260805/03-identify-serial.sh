#!/usr/bin/env bash
set -euo pipefail
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
sudo env "E7_PORT=${E7_PORT:-}" python3 "$script_dir/lib/e7_at.py" --all-ports --timeout 1.5 \
    --banner "Nokia E7 serial identification" \
    AT ATI AT+CGMI AT+CGMM AT+CGMR
