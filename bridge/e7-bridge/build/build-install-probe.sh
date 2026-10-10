#!/usr/bin/env bash
# Build a disposable data-only Symbian SIS using an installed PocketJS toolchain.
# This is NOT an E7Bridge app or firmware update.
set -euo pipefail

here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
project=$(cd -- "$here/.." && pwd)
usage() {
    cat <<'USAGE'
Usage:
  build/build-install-probe.sh --pocketjs /path/to/pocketjs [--out /path/to/output]

Prerequisite (run yourself in the PocketJS checkout):
  bun tools/symbian.ts setup --yes
  bun tools/symbian.ts doctor

This command builds our independent Qt app with the *installed* pinned
Symbian SDK/GCCE toolchain. It does not change your PocketJS checkout,
flash the E7, install anything onto the E7, or use network inside Docker.
USAGE
}
repo=""
out="$project/dist"
while (($#)); do
    case "$1" in
        --pocketjs) [[ $# -ge 2 ]] || { usage >&2; exit 2; }; repo="$2"; shift 2 ;;
        --out) [[ $# -ge 2 ]] || { usage >&2; exit 2; }; out="$2"; shift 2 ;;
        --help|-h) usage; exit 0 ;;
        *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
    esac
done
if [[ -z "$repo" ]]; then
    echo "Missing --pocketjs path to an initialized PocketJS checkout." >&2
    usage >&2
    exit 2
fi
command -v docker >/dev/null || { echo 'Missing Docker CLI.' >&2; exit 1; }
command -v python3 >/dev/null || { echo 'Missing Python 3.' >&2; exit 1; }
repo=$(cd -- "$repo" && pwd)
manifest="$repo/tools/cli/symbian-toolchain.json"
[[ -f "$manifest" ]] || { echo "Not a compatible PocketJS checkout: $manifest" >&2; exit 1; }

# Read the exact volumes/image names from the checked-out toolchain manifest.
mapfile -t config < <(python3 - "$manifest" <<'PY'
import json, sys
m=json.load(open(sys.argv[1], encoding='utf-8'))
assert m['container']['platform']=='linux/amd64'
for k in ('image','volume','signingVolume'):
    print(m['container'][k])
print(m['signing']['certificate'])
print(m['signing']['privateKey'])
print(m['toolchainVersion'])
PY
)
[[ ${#config[@]} -eq 6 ]] || { echo 'Invalid toolchain manifest.' >&2; exit 1; }
image=${config[0]}
toolchain=${config[1]}
signing=${config[2]}
certificate=${config[3]}
private_key=${config[4]}
version=${config[5]}
[[ "$version" == "sr1-qt474-v1" ]] || { echo "Unsupported PocketJS toolchain: $version" >&2; exit 1; }

for volume in "$toolchain" "$signing"; do
    if ! docker volume inspect "$volume" >/dev/null 2>&1; then
        echo "Docker volume '$volume' is missing. Run PocketJS symbian setup --yes." >&2
        exit 1
    fi
done
if ! docker image inspect "$image" >/dev/null 2>&1; then
    echo "Image '$image' is missing. Run PocketJS symbian setup --yes." >&2
    exit 1
fi
actual=$(docker image inspect --format '{{index .Config.Labels "org.pocketjs.symbian.toolchain"}}' "$image")
if [[ "$actual" != "$version" ]]; then
    echo "Unexpected toolchain image label: '$actual' (expected '$version')." >&2
    exit 1
fi
mkdir -p -- "$out"
out=$(cd -- "$out" && pwd)
echo "Building disposable E7 deployment probe using pinned $version image."
echo 'Data-only probe; no Docker network or phone access.'

docker run --rm --platform linux/amd64 --network none \
    --mount "type=volume,src=$toolchain,dst=/toolchain,readonly" \
    --mount "type=volume,src=$signing,dst=/signing,readonly" \
    --mount "type=bind,src=$here,dst=/bridge-scripts,readonly" \
    --mount "type=bind,src=$out,dst=/out" \
    --env "E7_SIGNING_CERT=$certificate" \
    --env "E7_SIGNING_KEY=$private_key" \
    --entrypoint /bin/bash "$image" \
    /bridge-scripts/in-container-probe.sh

printf '\nBuild output: %s/E7DeployProbe-v0.1.0.sis\n' "$out"
echo 'Only the disposable marker file will be installed when Belle accepts this SIS.'
