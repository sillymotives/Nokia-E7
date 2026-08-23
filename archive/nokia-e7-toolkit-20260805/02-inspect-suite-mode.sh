#!/usr/bin/env bash
set -euo pipefail

echo "=== Nokia in Suite mode ==="
lsusb | sed -E 's/(E7-00).*/\1 [unique details redacted]/'

echo
echo "=== USB interface map (unique serial removed) ==="
usb-devices |
sed -n '/Vendor=0421/,/^$/p' |
sed -E 's/(SerialNumber=).*/\1[redacted]/'

echo
echo "=== Serial interfaces ==="
shopt -s nullglob
ports=(/dev/ttyACM* /dev/ttyUSB*)
if ((${#ports[@]})); then
    ls -l "${ports[@]}"
else
    echo "No serial interfaces"
fi

echo
echo "=== Network interfaces ==="
ip -brief link

echo
echo "=== Native Nokia tooling ==="
for tool in gammu wammu gnokii obexftp obexctl mtp-detect gio bluetoothctl; do
    if command -v "$tool" >/dev/null 2>&1; then
        printf '%-14s %s\n' "$tool" "$(command -v "$tool")"
    else
        printf '%-14s unavailable\n' "$tool"
    fi
done

echo
echo "=== Phonet interface ==="
ip -details link show usbpn0 2>/dev/null || echo "usbpn0 is not currently present"

