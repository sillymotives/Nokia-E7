#!/usr/bin/env bash
set -euo pipefail
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)

echo "This sends one emulated Menu keypress to the Nokia E7."
read -r -p "Press Enter to continue, or Ctrl-C to cancel... "

sudo env "E7_PORT=${E7_PORT:-}" python3 "$script_dir/lib/e7_at.py" --timeout 3 \
    --banner "Nokia E7 Menu keypress" 'AT+CKPD="M"'
