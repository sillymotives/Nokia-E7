#!/usr/bin/env bash
# Nokia E7 MTP device-information probe, version 1.
# Uses mtp-detect only after proving one live Nokia Suite USB device. It does
# not enumerate file objects, transfer files, set properties, or delete data.

set -u
set -o pipefail

export LC_ALL=C
export LANG=C
umask 077

readonly SCRIPT_VERSION="1"

say() {
    printf '%s\n' "$*"
}

have() {
    command -v "$1" >/dev/null 2>&1
}

read_one_line() {
    local file="$1"
    if [[ -r "$file" ]]; then
        tr -d '\000\r\n' <"$file"
    fi
}

readonly START_DIR="$(pwd -P)"
case "$START_DIR/" in
    /media/*|/run/media/*|/mnt/*)
        say "REFUSED: run from host storage, not $START_DIR"
        exit 2
        ;;
esac

readonly STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
readonly RUN_NAME="nokia-e7-mtp-detect-${STAMP}"
readonly RUN_DIR="${START_DIR}/${RUN_NAME}"
readonly REPORT="${RUN_DIR}/mtp-detect.txt"
readonly NEXT_FILE="${RUN_DIR}/NEXT.txt"
readonly BUNDLE="${START_DIR}/${RUN_NAME}.tar.gz"
readonly BUNDLE_SUM="${BUNDLE}.sha256"

mkdir -m 700 -- "$RUN_DIR" || exit 1
run_status=0
usb_node=""

{
    say "NOKIA E7 MTP DEVICE-INFORMATION PROBE"
    say "Script version: $SCRIPT_VERSION"
    say "UTC start: $(date -u --iso-8601=seconds 2>/dev/null || date -u)"
    say "Policy: MTP device/storage information only; no object enumeration"

    for required in lsusb udevadm mtp-detect timeout find grep sed tr tar gzip sha256sum; do
        if ! have "$required"; then
            say "REFUSED: required command is absent: $required"
            run_status=2
        fi
    done

    if ((run_status == 0)); then
        mapfile -t matches < <(lsusb -d 0421:0335 2>/dev/null)
        say "Matching Nokia Suite USB count: ${#matches[@]}"
        if ((${#matches[@]} != 1)) || [[ "${matches[0]}" != *E7-00* ]]; then
            say "REFUSED: expected exactly one Nokia E7-00 with USB ID 0421:0335."
            run_status=3
        else
            say "${matches[0]}"
        fi
    fi

    if ((run_status == 0)); then
        sysfs_matches=()
        for device in /sys/bus/usb/devices/*; do
            [[ -d "$device" ]] || continue
            if [[ "$(read_one_line "$device/idVendor")" == "0421" && "$(read_one_line "$device/idProduct")" == "0335" ]]; then
                sysfs_matches+=("$device")
            fi
        done

        say "Matching Nokia Suite sysfs count: ${#sysfs_matches[@]}"
        if ((${#sysfs_matches[@]} != 1)); then
            say "REFUSED: sysfs did not contain exactly one matching device."
            run_status=4
        else
            busnum="$(read_one_line "${sysfs_matches[0]}/busnum")"
            devnum="$(read_one_line "${sysfs_matches[0]}/devnum")"
            if [[ "$busnum" =~ ^[0-9]+$ && "$devnum" =~ ^[0-9]+$ ]]; then
                printf -v usb_node '/dev/bus/usb/%03d/%03d' "$((10#$busnum))" "$((10#$devnum))"
                say "Proven USB node: $usb_node"
            else
                say "REFUSED: invalid bus or device number from sysfs."
                run_status=5
            fi
        fi
    fi

    if ((run_status == 0)); then
        mtp_candidates=()
        for device in /sys/bus/usb/devices/*; do
            # Count physical USB devices only. Interface nodes inherit their
            # parent's ID_MTP_DEVICE property and would otherwise be counted
            # as additional candidates.
            [[ -r "$device/idVendor" && -r "$device/idProduct" ]] || continue
            if udevadm info --query=property --path="$device" 2>/dev/null |
                grep -qx 'ID_MTP_DEVICE=1'; then
                mtp_candidates+=("$device")
            fi
        done
        say "Host MTP-candidate USB count: ${#mtp_candidates[@]}"
        if ((${#mtp_candidates[@]} != 1)) || [[ "${mtp_candidates[0]}" != "${sysfs_matches[0]}" ]]; then
            say "REFUSED: the Nokia is not the host's sole MTP candidate."
            run_status=6
        fi
    fi

    if ((run_status == 0)); then
        gvfs_dir="/run/user/$(id -u)/gvfs"
        if [[ -d "$gvfs_dir" ]] && find "$gvfs_dir" -mindepth 1 -maxdepth 1 -name 'mtp:*' -print -quit | grep -q .; then
            say "REFUSED: an MTP GVFS mount is already active."
            run_status=7
        fi
    fi

    if ((run_status == 0)) && have fuser; then
        owners="$(fuser "$usb_node" 2>/dev/null || true)"
        if [[ -n "$owners" ]]; then
            say "REFUSED: the Nokia USB node is open by process(es): $owners"
            run_status=8
        fi
    fi

    if have dpkg-query; then
        printf '\n=== Installed MTP packages ===\n'
        dpkg-query -W -f='${binary:Package}\t${Version}\n' \
            mtp-tools libmtp-runtime libmtp9t64 libmtp-common 2>/dev/null || true
    fi

    if ((run_status == 0)); then
        printf '\n=== Redacted mtp-detect output ===\n'
        timeout --signal=TERM --kill-after=5s 45s mtp-detect 2>&1 |
            sed -E 's/[0-9]{15}/[15-digit-id-redacted]/g'
        probe_status=${PIPESTATUS[0]}
        if ((probe_status == 0)); then
            say "PASS: mtp-detect completed."
        else
            say "PARTIAL: mtp-detect exited $probe_status."
            run_status=9
        fi
    fi

    say "UTC finish: $(date -u --iso-8601=seconds 2>/dev/null || date -u)"
} >"$REPORT" 2>&1

cat >"$NEXT_FILE" <<EOF
Nokia E7 MTP device-information probe finished with status ${run_status}.

Expected shareable files:
  ${RUN_NAME}.tar.gz
  ${RUN_NAME}.tar.gz.sha256
EOF

if ! have tar || ! have gzip || ! have sha256sum; then
    say "PARTIAL: report created, but packaging tools are unavailable."
    say "Report: $REPORT"
    exit 10
fi

tar -czf "$BUNDLE" -C "$START_DIR" "$RUN_NAME" || exit 11
(
    cd "$START_DIR" || exit 1
    sha256sum "$(basename "$BUNDLE")" >"$(basename "$BUNDLE_SUM")"
) || exit 12

if ((run_status == 0)); then
    say "PASS: Nokia E7 MTP device-information probe complete."
else
    say "PARTIAL: Nokia E7 MTP probe status $run_status."
fi
say "Bundle:   $BUNDLE"
say "Checksum: $BUNDLE_SUM"
say "No MTP file-object listing or transfer command was issued."

exit "$run_status"
