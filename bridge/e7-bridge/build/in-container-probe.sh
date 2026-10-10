#!/usr/bin/env bash
# Disposable data-only SIS. Runs inside an existing pinned PocketJS toolchain.
set -euo pipefail
: "${E7_SIGNING_CERT:?required}"
: "${E7_SIGNING_KEY:?required}"
toolchain=/toolchain/current
certificate="/signing/$E7_SIGNING_CERT"
private_key="/signing/$E7_SIGNING_KEY"
output=/out/E7DeployProbe-v0.1.0.sis
for path in "$toolchain/bin/makesis" "$toolchain/bin/signsis" "$certificate" "$private_key"; do
    test -f "$path" || { echo "Missing toolchain file: $path" >&2; exit 1; }
done
build=$(mktemp -d /tmp/e7-deploy-probe.XXXXXX)
stage=$(mktemp -d /out/.e7-deploy-probe.XXXXXX)
trap 'rm -rf "$build" "$stage"' EXIT
export PATH="$toolchain/sdk/bin:$toolchain/bin:$PATH"
export EPOCROOT="$toolchain/sdk/"
printf '%s\n' 'E7 installer pilot: installed by the native Symbian package manager.' > "$build/probe.txt"
cat > "$build/deploy-probe.pkg" <<EOF_PKG
; Disposable data-only package with its own non-system UID
&EN
#{"E7 Deployment Probe"},(0xE94B7002),0,1,0
%{"E7 Deployment Probe"}
:"E7 Deployment Probe"
"$build/probe.txt"-"C:\\data\\E7DeployProbe\\probe.txt"
EOF_PKG
# The historical MakeSIS parser treats absolute /tmp paths as -t options.
# Invoke it with relative positional paths from the temporary build directory.
( cd "$build" && "$toolchain/bin/makesis" deploy-probe.pkg probe-unsigned.sis )
"$toolchain/bin/signsis" "$build/probe-unsigned.sis" "$stage/E7DeployProbe-v0.1.0.sis" \
    "$certificate" "$private_key"
test -s "$stage/E7DeployProbe-v0.1.0.sis"
file "$stage/E7DeployProbe-v0.1.0.sis" | grep -Fq 'Symbian installation file'
"$toolchain/bin/signsis" -o "$stage/E7DeployProbe-v0.1.0.sis" > "$build/signing.txt"
grep -Fq 'Issued to:' "$build/signing.txt"
mv -- "$stage/E7DeployProbe-v0.1.0.sis" "$output"
file "$output"
sha256sum "$output"
