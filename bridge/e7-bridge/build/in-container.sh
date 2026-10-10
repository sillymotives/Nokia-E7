#!/usr/bin/env bash
# Runs ONLY inside the pinned PocketJS Symbian toolchain Docker image.
set -euo pipefail
: "${E7_SIGNING_CERT:?required}"
: "${E7_SIGNING_KEY:?required}"

toolchain=/toolchain/current
certificate="/signing/$E7_SIGNING_CERT"
private_key="/signing/$E7_SIGNING_KEY"
uid=0xE94B7001
output=/out/E7Bridge-v0.7.0.sis

for item in "$toolchain/sdk/bin/qmake" "$toolchain/bin/makesis" \
    "$toolchain/bin/signsis" "$toolchain/bin/symbian-gcce-link" \
    "$certificate" "$private_key" \
    /bridge-source/e7bridge.pro /bridge-source/main.cpp /bridge-source/sha256_compat.h; do
    [[ -f "$item" ]] || { echo "Missing build dependency: $item" >&2; exit 1; }
done

build=$(mktemp -d /tmp/e7-bridge-build.XXXXXX)
staging=$(mktemp -d /out/.e7-bridge.XXXXXX)
trap 'rm -rf "$build" "$staging"' EXIT
cp /bridge-source/e7bridge.pro /bridge-source/main.cpp /bridge-source/sha256_compat.h "$build/"
cd "$build"
export EPOCROOT="$toolchain/sdk/"
export PATH="$toolchain/sdk/bin:$toolchain/bin:$toolchain/gcce/arm-2012.03/bin:$PATH"
export QMAKESPEC=symbian-gcce

qmake -spec "$toolchain/sdk/mkspecs/symbian-gcce" e7bridge.pro
make -j2

# Reject malformed build outputs before even attempting to sign.
test -s E7Bridge.exe
test -s E7Bridge.rsc
test -s E7Bridge_reg.rsc
file E7Bridge.exe | grep -Fq 'Psion Series 5 executable'
actual_uid=$(od -An -tx4 -j8 -N4 E7Bridge.exe | tr -d '[:space:]')
expected_uid=$(printf '%s' "${uid#0x}" | tr '[:upper:]' '[:lower:]')
[[ "$actual_uid" == "$expected_uid" ]] || {
    echo "Incorrect E32 UID3: $actual_uid, expected $expected_uid" >&2
    exit 1
}

cat > e7bridge.pkg <<EOF_PKG
; E7 Bridge native Qt 4.7.4 development package
&EN
#{"E7 Bridge"},($uid),0,7,0
%{"E7 Bridge"}
:"E7 Bridge"
(0x2001E61C),4,7,4,{"Qt"}
[0x20022E6D],0,0,0,{"Symbian^3"}
[0x20032DE7],0,0,0,{"Symbian Belle"}
"$build/E7Bridge.exe"-"!:\\sys\\bin\\E7Bridge.exe"
"$build/E7Bridge.rsc"-"!:\\resource\\apps\\E7Bridge.rsc"
"$build/E7Bridge_reg.rsc"-"!:\\private\\10003a3f\\import\\apps\\E7Bridge_reg.rsc"
EOF_PKG
makesis e7bridge.pkg e7bridge-unsigned.sis
signsis e7bridge-unsigned.sis "$staging/E7Bridge-v0.7.0.sis" \
    "$certificate" "$private_key"
test -s "$staging/E7Bridge-v0.7.0.sis"
file "$staging/E7Bridge-v0.7.0.sis" | grep -Fq 'Symbian installation file'
signsis -o "$staging/E7Bridge-v0.7.0.sis" > signing.txt
grep -Fq 'Issued to:' signing.txt

mv -- "$staging/E7Bridge-v0.7.0.sis" "$output"
file E7Bridge.exe "$output"
sha256sum "$output"
