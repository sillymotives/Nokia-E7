#!/usr/bin/env bash
# Nokia E7 host-side baseline capture, version 2.
# Read-only with respect to connected devices: no mount, unmount, install,
# repair, unlock, flash, or device write operations are performed.

set -u
set -o pipefail

export LC_ALL=C
export LANG=C
umask 077

readonly SCRIPT_VERSION="2"

say() {
    printf '%s\n' "$*"
}

section() {
    printf '\n=== %s ===\n' "$*"
}

have() {
    command -v "$1" >/dev/null 2>&1
}

read_one_line() {
    local file="$1"
    if [[ -r "$file" ]]; then
        tr -d '\000\r\n' < "$file"
    fi
}

safe_command() {
    local label="$1"
    shift
    printf '\n--- %s ---\n' "$label"
    if have "$1"; then
        "$@" 2>&1 || printf '[command exited %s]\n' "$?"
    else
        printf '[not installed: %s]\n' "$1"
    fi
}

readonly START_DIR="$(pwd -P)"
case "$START_DIR/" in
    /media/*|/run/media/*|/mnt/*)
        say "REFUSED: run this script from host storage, not $START_DIR"
        exit 2
        ;;
esac

readonly STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
readonly RUN_NAME="nokia-e7-baseline-${STAMP}"
readonly RUN_DIR="${START_DIR}/${RUN_NAME}"
readonly REPORT="${RUN_DIR}/host-baseline.txt"
readonly NEXT_FILE="${RUN_DIR}/NEXT.txt"
readonly BUNDLE="${START_DIR}/${RUN_NAME}.tar.gz"
readonly BUNDLE_SUM="${BUNDLE}.sha256"

mkdir -m 700 -- "$RUN_DIR" || {
    say "FAIL: could not create $RUN_DIR"
    exit 1
}

{
    say "NOKIA E7 HOST BASELINE"
    say "Script version: $SCRIPT_VERSION"
    say "UTC start: $(date -u --iso-8601=seconds 2>/dev/null || date -u)"
    say "Host output directory: $RUN_DIR"
    say "Policy: observation only; no connected-device writes"

    section "Host identity"
    safe_command "Kernel" uname -a
    safe_command "User identity" id
    if [[ -r /etc/os-release ]]; then
        printf '\n--- Operating system ---\n'
        sed -n '1,40p' /etc/os-release
    fi

    section "USB inventory"
    safe_command "USB devices" lsusb
    safe_command "USB topology" lsusb -t

    printf '\n--- Nokia-like USB sysfs devices ---\n'
    nokia_count=0
    for dev in /sys/bus/usb/devices/*; do
        [[ -d "$dev" ]] || continue
        vendor="$(read_one_line "$dev/idVendor")"
        manufacturer="$(read_one_line "$dev/manufacturer")"
        product="$(read_one_line "$dev/product")"
        if [[ "$vendor" == "0421" || "$manufacturer" =~ [Nn][Oo][Kk][Ii][Aa] || "$product" =~ [Nn][Oo][Kk][Ii][Aa] ]]; then
            nokia_count=$((nokia_count + 1))
            say "sysfs_path=$dev"
            say "idVendor=${vendor:-unknown}"
            say "idProduct=$(read_one_line "$dev/idProduct")"
            say "manufacturer=${manufacturer:-unknown}"
            say "product=${product:-unknown}"
            serial="$(read_one_line "$dev/serial")"
            if [[ -n "$serial" ]] && have sha256sum; then
                say "serial_sha256=$(printf '%s' "$serial" | sha256sum | awk '{print $1}')"
            elif [[ -n "$serial" ]]; then
                say "serial_present=yes (hash unavailable)"
            else
                say "serial_present=no"
            fi
            say "busnum=$(read_one_line "$dev/busnum")"
            say "devnum=$(read_one_line "$dev/devnum")"
            say "speed=$(read_one_line "$dev/speed")"
            say "authorized=$(read_one_line "$dev/authorized")"
            if have udevadm; then
                udevadm info --query=property --path="$dev" 2>&1 |
                    sed -E '/^(ID_SERIAL|ID_SERIAL_SHORT|ID_USB_SERIAL|ID_USB_SERIAL_SHORT)=/d' |
                    sed -n '1,160p'
            fi
            say "--"
        fi
    done
    say "Nokia-like sysfs device count: $nokia_count"

    if have usb-devices; then
        printf '\n--- usb-devices Nokia blocks ---\n'
        usb-devices 2>&1 | awk '
            BEGIN { RS=""; IGNORECASE=1 }
            /Vendor=0421|Nokia/ { print $0 "\n" }
        ' | sed -E 's/(SerialNumber=).*/\1[redacted]/'
    fi

    section "Block and filesystem view"
    if have lsblk; then
        printf '\n--- Detailed block inventory ---\n'
        lsblk -e 7 -o NAME,KNAME,PATH,TYPE,TRAN,HOTPLUG,RM,RO,SIZE,FSTYPE,LABEL,PARTLABEL,UUID,MOUNTPOINTS,MODEL,VENDOR 2>&1 ||
            lsblk -e 7 -o NAME,KNAME,PATH,TYPE,RM,RO,SIZE,FSTYPE,LABEL,UUID,MOUNTPOINT 2>&1 || true
    else
        say "[not installed: lsblk]"
    fi
    safe_command "Mounted filesystems" findmnt -rn -o SOURCE,TARGET,FSTYPE,OPTIONS

    printf '\n--- USB/Nokia persistent block links ---\n'
    if [[ -d /dev/disk/by-id ]]; then
        find /dev/disk/by-id -maxdepth 1 -type l \
            \( -iname '*usb*' -o -iname '*nokia*' \) -printf '%f -> %l\n' 2>&1 |
            sed -E 's/(usb-Nokia_[^ ]*_)[^- ]+(-0:0)/\1[redacted]\2/' |
            sort
    else
        say "[/dev/disk/by-id absent]"
    fi

    section "Userspace device views"
    safe_command "GIO volumes and mounts" gio mount --list
    printf '\n--- GVFS mount directory ---\n'
    gvfs_dir="/run/user/$(id -u)/gvfs"
    if [[ -d "$gvfs_dir" ]]; then
        find "$gvfs_dir" -mindepth 1 -maxdepth 2 -printf '%y %p\n' 2>&1 | sed -n '1,240p'
    else
        say "[$gvfs_dir absent]"
    fi

    section "Serial-style interfaces"
    found_tty=0
    for tty in /dev/ttyACM* /dev/ttyUSB*; do
        [[ -e "$tty" ]] || continue
        found_tty=1
        ls -l -- "$tty"
        if have udevadm; then
            udevadm info --query=property --name="$tty" 2>&1 |
                sed -E '/^(ID_SERIAL|ID_SERIAL_SHORT|ID_USB_SERIAL|ID_USB_SERIAL_SHORT)=/d' |
                sed -n '1,140p'
        fi
        say "--"
    done
    [[ "$found_tty" -eq 1 ]] || say "No ttyACM or ttyUSB interfaces present."

    section "Recent kernel observations"
    if have journalctl; then
        journalctl -k -b --no-pager 2>&1 |
            grep -Ei 'usb|0421|nokia|mtp|cdc|acm|mass storage|scsi' |
            sed -E 's/[0-9]{15}/[15-digit-id-redacted]/g' |
            tail -n 320 || true
    elif have dmesg; then
        dmesg 2>&1 |
            grep -Ei 'usb|0421|nokia|mtp|cdc|acm|mass storage|scsi' |
            sed -E 's/[0-9]{15}/[15-digit-id-redacted]/g' |
            tail -n 320 || true
    else
        say "No journalctl or dmesg command available."
    fi

    section "Relevant host tools"
    for tool in \
        udevadm lsusb usb-devices lsblk findmnt gio \
        mtp-detect mtp-files jmtpfs simple-mtpfs \
        obexftp bluetoothctl gammu gnokii socat minicom picocom \
        openssl curl wget python3 perl git tar gzip sha256sum; do
        if path="$(command -v "$tool" 2>/dev/null)"; then
            printf '%-16s %s\n' "$tool" "$path"
        else
            printf '%-16s %s\n' "$tool" "[absent]"
        fi
    done

    section "Network device status"
    printf '\n--- NetworkManager devices ---\n'
    if have nmcli; then
        nmcli --terse --fields DEVICE,TYPE,STATE device status 2>&1 |
            sed -E 's/(p2p-dev-)?wlx[[:xdigit:]]+/\1wlx[redacted]/g' || true
    else
        say "[not installed: nmcli]"
    fi

    section "Completion"
    say "UTC finish: $(date -u --iso-8601=seconds 2>/dev/null || date -u)"
    say "PASS: host-side observation completed."
    say "No mount, unmount, install, repair, unlock, flash, or device write command was issued."
} >"$REPORT" 2>&1

cat >"$NEXT_FILE" <<EOF
Nokia E7 baseline capture completed.

Review host-baseline.txt for identifiers or personal paths before sharing.
Do not commit this raw capture to the public repository.

Expected shareable files:
  ${RUN_NAME}.tar.gz
  ${RUN_NAME}.tar.gz.sha256
EOF

if ! have tar || ! have gzip || ! have sha256sum; then
    say "PARTIAL: report created, but tar/gzip/sha256sum is unavailable."
    say "Report: $REPORT"
    exit 3
fi

tar -czf "$BUNDLE" -C "$START_DIR" "$RUN_NAME" || {
    say "FAIL: report exists, but bundle creation failed."
    say "Report: $REPORT"
    exit 4
}

(
    cd "$START_DIR" || exit 1
    sha256sum "$(basename "$BUNDLE")" >"$(basename "$BUNDLE_SUM")"
) || {
    say "FAIL: bundle exists, but checksum creation failed."
    say "Bundle: $BUNDLE"
    exit 5
}

say "PASS: Nokia E7 read-only host baseline complete."
say "Bundle:   $BUNDLE"
say "Checksum: $BUNDLE_SUM"
say "No write was made to the phone."
