#!/usr/bin/env bash
# Nokia E7 bounded MTP write/read/delete round trip, version 1.
# Creates one uniquely named root folder on the proven read/write Mass memory
# store, transfers one tiny text file, verifies it, and removes both objects.

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

set_failure() {
    local code="$1"
    shift
    if ((run_status == 0)); then
        run_status="$code"
    fi
    say "$*"
}

redact() {
    sed -E 's/[0-9]{15}/[15-digit-id-redacted]/g'
}

readonly START_DIR="$(pwd -P)"
case "$START_DIR/" in
    /media/*|/run/media/*|/mnt/*)
        say "REFUSED: run from host storage, not $START_DIR"
        exit 2
        ;;
esac

readonly STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
readonly RUN_NAME="nokia-e7-mtp-roundtrip-${STAMP}"
readonly RUN_DIR="${START_DIR}/${RUN_NAME}"
readonly REPORT="${RUN_DIR}/mtp-roundtrip.txt"
readonly NEXT_FILE="${RUN_DIR}/NEXT.txt"
readonly PAYLOAD="${RUN_DIR}/KAI.TXT"
readonly RETRIEVED="${RUN_DIR}/KAI.RETRIEVED.TXT"
readonly BUNDLE="${START_DIR}/${RUN_NAME}.tar.gz"
readonly BUNDLE_SUM="${BUNDLE}.sha256"
readonly FOLDER_NAME="K$(date -u +%H%M%S)"

mkdir -m 700 -- "$RUN_DIR" || exit 1

run_status=0
usb_node=""
storage_id_hex=""
storage_id_dec=""
folder_id=""
file_id=""
folder_created=0
file_created=0
file_deleted=0
folder_deleted=0
roundtrip_verified=0

{
    say "NOKIA E7 BOUNDED MTP ROUND TRIP"
    say "Script version: $SCRIPT_VERSION"
    say "UTC start: $(date -u --iso-8601=seconds 2>/dev/null || date -u)"
    say "Policy: one unique Mass memory folder and one tiny text file only"
    say "Test folder: $FOLDER_NAME"

    for required in lsusb udevadm mtp-detect mtp-folders mtp-newfolder \
        mtp-sendfile mtp-getfile mtp-delfile timeout find grep sed awk tr \
        cmp wc tar gzip sha256sum; do
        if ! have "$required"; then
            set_failure 2 "REFUSED: required command is absent: $required"
        fi
    done

    if ((run_status == 0)); then
        mapfile -t matches < <(lsusb -d 0421:0335 2>/dev/null)
        say "Matching Nokia Suite USB count: ${#matches[@]}"
        if ((${#matches[@]} != 1)) || [[ "${matches[0]}" != *E7-00* ]]; then
            set_failure 3 "REFUSED: expected exactly one Nokia E7-00 with USB ID 0421:0335."
        else
            say "${matches[0]}"
        fi
    fi

    if ((run_status == 0)); then
        sysfs_matches=()
        for device in /sys/bus/usb/devices/*; do
            [[ -d "$device" ]] || continue
            if [[ "$(read_one_line "$device/idVendor")" == "0421" && \
                  "$(read_one_line "$device/idProduct")" == "0335" ]]; then
                sysfs_matches+=("$device")
            fi
        done

        say "Matching Nokia Suite sysfs count: ${#sysfs_matches[@]}"
        if ((${#sysfs_matches[@]} != 1)); then
            set_failure 4 "REFUSED: sysfs did not contain exactly one matching device."
        else
            busnum="$(read_one_line "${sysfs_matches[0]}/busnum")"
            devnum="$(read_one_line "${sysfs_matches[0]}/devnum")"
            if [[ "$busnum" =~ ^[0-9]+$ && "$devnum" =~ ^[0-9]+$ ]]; then
                printf -v usb_node '/dev/bus/usb/%03d/%03d' \
                    "$((10#$busnum))" "$((10#$devnum))"
                say "Proven USB node: $usb_node"
            else
                set_failure 5 "REFUSED: invalid bus or device number from sysfs."
            fi
        fi
    fi

    if ((run_status == 0)); then
        mtp_candidates=()
        for device in /sys/bus/usb/devices/*; do
            [[ -r "$device/idVendor" && -r "$device/idProduct" ]] || continue
            if udevadm info --query=property --path="$device" 2>/dev/null |
                grep -qx 'ID_MTP_DEVICE=1'; then
                mtp_candidates+=("$device")
            fi
        done
        say "Host MTP-candidate USB count: ${#mtp_candidates[@]}"
        if ((${#mtp_candidates[@]} != 1)) || \
           [[ "${mtp_candidates[0]}" != "${sysfs_matches[0]}" ]]; then
            set_failure 6 "REFUSED: the Nokia is not the host's sole MTP candidate."
        fi
    fi

    if ((run_status == 0)); then
        gvfs_dir="/run/user/$(id -u)/gvfs"
        if [[ -d "$gvfs_dir" ]] && \
           find "$gvfs_dir" -mindepth 1 -maxdepth 1 -name 'mtp:*' \
                -print -quit | grep -q .; then
            set_failure 7 "REFUSED: an MTP GVFS mount is already active."
        fi
    fi

    if ((run_status == 0)) && have fuser; then
        owners="$(fuser "$usb_node" 2>/dev/null || true)"
        if [[ -n "$owners" ]]; then
            set_failure 8 "REFUSED: the Nokia USB node is open by process(es): $owners"
        fi
    fi

    if ((run_status == 0)); then
        detect_output="$(timeout --signal=TERM --kill-after=5s 45s mtp-detect 2>&1)"
        detect_status=$?
        if ((detect_status != 0)); then
            set_failure 9 "REFUSED: mtp-detect exited $detect_status."
        else
            mapfile -t mass_ids < <(
                printf '%s\n' "$detect_output" |
                    awk '
                        /^[[:space:]]*StorageID:/ { id=$2; access="" }
                        /^[[:space:]]*AccessCapability:/ { access=$2 }
                        /^[[:space:]]*StorageDescription:/ {
                            description=$0
                            sub(/^[[:space:]]*StorageDescription:[[:space:]]*/, "", description)
                            if (description == "Mass memory" && access == "0x0000") print id
                        }
                    '
            )
            if ((${#mass_ids[@]} != 1)) || \
               [[ ! "${mass_ids[0]}" =~ ^0x[0-9A-Fa-f]{8}$ ]]; then
                set_failure 10 "REFUSED: did not prove exactly one read/write Mass memory store."
            else
                storage_id_hex="${mass_ids[0]}"
                storage_id_dec="$((storage_id_hex))"
                say "Proven write target: Mass memory $storage_id_hex ($storage_id_dec)"
            fi
        fi
    fi

    if ((run_status == 0)); then
        folders_before="$(timeout --signal=TERM --kill-after=5s 45s mtp-folders 2>&1)"
        folders_before_status=$?
        if ((folders_before_status != 0)); then
            set_failure 11 "REFUSED: preflight folder listing exited $folders_before_status."
        else
            preexisting_count="$(
                printf '%s\n' "$folders_before" |
                    awk -v name="$FOLDER_NAME" '$1 ~ /^[0-9]+$/ && $NF == name { count++ } END { print count+0 }'
            )"
            if [[ "$preexisting_count" != "0" ]]; then
                set_failure 12 "REFUSED: the unique test-folder name already exists."
            else
                say "PASS: test-folder name is absent before creation."
            fi
        fi
    fi

    if ((run_status == 0)); then
        printf 'Nokia E7 MTP round-trip proof\nUTC: %s\n' "$STAMP" >"$PAYLOAD"
        payload_sha="$(sha256sum "$PAYLOAD" | awk '{print $1}')"
        say "Host payload bytes: $(wc -c <"$PAYLOAD")"
        say "Host payload SHA-256: $payload_sha"

        create_output="$(
            timeout --signal=TERM --kill-after=5s 45s \
                mtp-newfolder "$FOLDER_NAME" 0 "$storage_id_dec" 2>&1
        )"
        create_status=$?
        printf '\n=== Folder creation ===\n'
        printf '%s\n' "$create_output" | redact
        mapfile -t folder_ids < <(
            printf '%s\n' "$create_output" |
                sed -n -E 's/^New folder created with ID: ([0-9]+)$/\1/p'
        )
        if ((${#folder_ids[@]} == 1)) && [[ "${folder_ids[0]}" =~ ^[1-9][0-9]*$ ]]; then
            folder_id="${folder_ids[0]}"
            folder_created=1
        fi
        if ((create_status != 0)) || ((folder_created == 0)); then
            set_failure 13 "PARTIAL: folder creation was not cleanly proven."
        else
            say "PASS: created only folder ID $folder_id."
        fi
    fi

    if ((run_status == 0)); then
        send_output="$(
            timeout --signal=TERM --kill-after=5s 45s \
                mtp-sendfile "$PAYLOAD" "/$FOLDER_NAME" 2>&1
        )"
        send_status=$?
        printf '\n=== File upload ===\n'
        printf '%s\n' "$send_output" | redact
        mapfile -t file_ids < <(
            printf '%s\n' "$send_output" |
                sed -n -E 's/^New file ID: ([0-9]+)$/\1/p'
        )
        if ((${#file_ids[@]} == 1)) && [[ "${file_ids[0]}" =~ ^[1-9][0-9]*$ ]]; then
            file_id="${file_ids[0]}"
            file_created=1
        fi
        if ((send_status != 0)) || ((file_created == 0)); then
            set_failure 14 "PARTIAL: file upload was not cleanly proven."
        else
            say "PASS: uploaded only file ID $file_id beneath folder ID $folder_id."
        fi
    fi

    if ((run_status == 0)); then
        get_output="$(
            timeout --signal=TERM --kill-after=5s 45s \
                mtp-getfile "$file_id" "$RETRIEVED" 2>&1
        )"
        get_status=$?
        printf '\n=== File retrieval ===\n'
        printf '%s\n' "$get_output" | redact
        if ((get_status != 0)) || [[ ! -f "$RETRIEVED" ]]; then
            set_failure 15 "PARTIAL: retrieval was not cleanly proven."
        else
            retrieved_sha="$(sha256sum "$RETRIEVED" | awk '{print $1}')"
            say "Retrieved bytes: $(wc -c <"$RETRIEVED")"
            say "Retrieved SHA-256: $retrieved_sha"
            if [[ "$retrieved_sha" != "$payload_sha" ]] || \
               ! cmp -s -- "$PAYLOAD" "$RETRIEVED"; then
                set_failure 16 "FAIL: retrieved payload does not match the host original."
            else
                roundtrip_verified=1
                say "PASS: uploaded and retrieved payloads are byte-identical."
            fi
        fi
    fi

    if ((file_created == 1)); then
        delete_file_output="$(
            timeout --signal=TERM --kill-after=5s 45s \
                mtp-delfile -n "$file_id" 2>&1
        )"
        delete_file_status=$?
        printf '\n=== Test-file cleanup ===\n'
        printf '%s\n' "$delete_file_output" | redact
        if ((delete_file_status == 0)); then
            file_deleted=1
            say "PASS: deleted only returned file ID $file_id."
        else
            set_failure 17 "PARTIAL: deletion of returned file ID $file_id failed."
        fi
    fi

    if ((folder_created == 1)) && ((file_created == 0 || file_deleted == 1)); then
        delete_folder_output="$(
            timeout --signal=TERM --kill-after=5s 45s \
                mtp-delfile -n "$folder_id" 2>&1
        )"
        delete_folder_status=$?
        printf '\n=== Test-folder cleanup ===\n'
        printf '%s\n' "$delete_folder_output" | redact
        if ((delete_folder_status == 0)); then
            folder_deleted=1
            say "PASS: deleted only returned folder ID $folder_id."
        else
            set_failure 18 "PARTIAL: deletion of returned folder ID $folder_id failed."
        fi
    fi

    if ((folder_created == 1)); then
        folders_after="$(timeout --signal=TERM --kill-after=5s 45s mtp-folders 2>&1)"
        folders_after_status=$?
        if ((folders_after_status != 0)); then
            set_failure 19 "PARTIAL: post-cleanup folder listing exited $folders_after_status."
        else
            remaining_count="$(
                printf '%s\n' "$folders_after" |
                    awk -v name="$FOLDER_NAME" '$1 ~ /^[0-9]+$/ && $NF == name { count++ } END { print count+0 }'
            )"
            if [[ "$remaining_count" != "0" ]]; then
                set_failure 20 "PARTIAL: test folder $FOLDER_NAME remains on the phone."
            else
                folder_deleted=1
                say "PASS: test-folder name is absent after cleanup."
            fi
        fi
    fi

    if ((roundtrip_verified == 1 && file_deleted == 1 && folder_deleted == 1 && run_status == 0)); then
        say "PASS: bounded MTP create/upload/retrieve/delete transaction complete."
    elif ((folder_created == 1 && folder_deleted == 0)); then
        say "RESIDUE: test folder may remain at Mass memory:/$FOLDER_NAME"
    fi

    say "UTC finish: $(date -u --iso-8601=seconds 2>/dev/null || date -u)"
} >"$REPORT" 2>&1

cat >"$NEXT_FILE" <<EOF
Nokia E7 bounded MTP round trip finished with status ${run_status}.

Test folder: ${FOLDER_NAME}
Folder created: ${folder_created}
File created: ${file_created}
Round trip verified: ${roundtrip_verified}
File deleted: ${file_deleted}
Folder absent after cleanup: ${folder_deleted}

Expected shareable files:
  ${RUN_NAME}.tar.gz
  ${RUN_NAME}.tar.gz.sha256
EOF

if ! have tar || ! have gzip || ! have sha256sum; then
    say "PARTIAL: report created, but packaging tools are unavailable."
    say "Report: $REPORT"
    exit 21
fi

tar -czf "$BUNDLE" -C "$START_DIR" "$RUN_NAME" || exit 22
(
    cd "$START_DIR" || exit 1
    sha256sum "$(basename "$BUNDLE")" >"$(basename "$BUNDLE_SUM")"
) || exit 23

if ((run_status == 0)); then
    say "PASS: Nokia E7 bounded MTP round trip complete and cleaned up."
else
    say "PARTIAL: Nokia E7 MTP round-trip status $run_status."
fi
say "Bundle:   $BUNDLE"
say "Checksum: $BUNDLE_SUM"

exit "$run_status"
