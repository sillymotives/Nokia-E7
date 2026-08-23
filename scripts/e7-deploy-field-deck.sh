#!/usr/bin/env bash
# Nokia E7 persistent Field Deck deployment, version 1.
# Creates Mass memory:/KAI, uploads the allowlisted INDEX.HTM, retrieves it for
# integrity verification, and deliberately leaves the verified payload in place.

set -u
set -o pipefail

export LC_ALL=C.UTF-8
export LANG=C.UTF-8
umask 077

readonly SCRIPT_VERSION="1"
readonly EXPECTED_PAYLOAD_NAME="INDEX.HTM"
readonly EXPECTED_PAYLOAD_BYTES="5493"
readonly EXPECTED_PAYLOAD_SHA="c5e11110d3b7272a6fa58b8033a47a8689204cf0e3342ceb8d9d63ae05117777"
readonly FOLDER_NAME="KAI"

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

if (($# != 1)); then
    say "Usage: $0 /path/to/INDEX.HTM"
    exit 2
fi

readonly START_DIR="$(pwd -P)"
case "$START_DIR/" in
    /media/*|/run/media/*|/mnt/*)
        say "REFUSED: run from host storage, not $START_DIR"
        exit 2
        ;;
esac

readonly PAYLOAD_INPUT="$1"
if [[ ! -f "$PAYLOAD_INPUT" || -L "$PAYLOAD_INPUT" ]]; then
    say "REFUSED: payload must be a regular non-symlink file."
    exit 2
fi
if [[ "$(basename -- "$PAYLOAD_INPUT")" != "$EXPECTED_PAYLOAD_NAME" ]]; then
    say "REFUSED: payload basename must be $EXPECTED_PAYLOAD_NAME."
    exit 2
fi

readonly STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
readonly RUN_NAME="nokia-e7-field-deck-deploy-${STAMP}"
readonly RUN_DIR="${START_DIR}/${RUN_NAME}"
readonly REPORT="${RUN_DIR}/field-deck-deploy.txt"
readonly NEXT_FILE="${RUN_DIR}/NEXT.txt"
readonly LOCAL_PAYLOAD="${RUN_DIR}/${EXPECTED_PAYLOAD_NAME}"
readonly RETRIEVED="${RUN_DIR}/INDEX.RETRIEVED.HTM"
readonly BUNDLE="${START_DIR}/${RUN_NAME}.tar.gz"
readonly BUNDLE_SUM="${BUNDLE}.sha256"

mkdir -m 700 -- "$RUN_DIR" || exit 1
cp -- "$PAYLOAD_INPUT" "$LOCAL_PAYLOAD" || exit 1
chmod 600 "$LOCAL_PAYLOAD"

run_status=0
usb_node=""
storage_id_hex=""
storage_id_dec=""
folder_id=""
file_id=""
folder_created=0
file_created=0
payload_verified=0
folder_visible=0

{
    say "NOKIA E7 FIELD DECK DEPLOYMENT"
    say "Script version: $SCRIPT_VERSION"
    say "UTC start: $(date -u --iso-8601=seconds 2>/dev/null || date -u)"
    say "Policy: create only Mass memory:/KAI and upload only INDEX.HTM"
    say "Persistence: successful objects are deliberately left on the phone"

    for required in basename cp chmod lsusb udevadm mtp-detect mtp-folders \
        mtp-newfolder mtp-sendfile mtp-getfile timeout find grep sed awk tr \
        cmp wc tar gzip sha256sum; do
        if ! have "$required"; then
            set_failure 2 "REFUSED: required command is absent: $required"
        fi
    done

    if ((run_status == 0)); then
        payload_bytes="$(wc -c <"$LOCAL_PAYLOAD")"
        payload_sha="$(sha256sum "$LOCAL_PAYLOAD" | awk '{print $1}')"
        say "Payload bytes: $payload_bytes"
        say "Payload SHA-256: $payload_sha"
        if [[ "$payload_bytes" != "$EXPECTED_PAYLOAD_BYTES" || \
              "$payload_sha" != "$EXPECTED_PAYLOAD_SHA" ]]; then
            set_failure 3 "REFUSED: payload does not match the allowlisted Field Deck v1."
        fi
    fi

    if ((run_status == 0)); then
        mapfile -t matches < <(lsusb -d 0421:0335 2>/dev/null)
        say "Matching Nokia Suite USB count: ${#matches[@]}"
        if ((${#matches[@]} != 1)) || [[ "${matches[0]}" != *E7-00* ]]; then
            set_failure 4 "REFUSED: expected exactly one Nokia E7-00 with USB ID 0421:0335."
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
            set_failure 5 "REFUSED: sysfs did not contain exactly one matching device."
        else
            busnum="$(read_one_line "${sysfs_matches[0]}/busnum")"
            devnum="$(read_one_line "${sysfs_matches[0]}/devnum")"
            if [[ "$busnum" =~ ^[0-9]+$ && "$devnum" =~ ^[0-9]+$ ]]; then
                printf -v usb_node '/dev/bus/usb/%03d/%03d' \
                    "$((10#$busnum))" "$((10#$devnum))"
                say "Proven USB node: $usb_node"
            else
                set_failure 6 "REFUSED: invalid bus or device number from sysfs."
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
            set_failure 7 "REFUSED: the Nokia is not the host's sole MTP candidate."
        fi
    fi

    if ((run_status == 0)); then
        gvfs_dir="/run/user/$(id -u)/gvfs"
        if [[ -d "$gvfs_dir" ]] && \
           find "$gvfs_dir" -mindepth 1 -maxdepth 1 -name 'mtp:*' \
                -print -quit | grep -q .; then
            set_failure 8 "REFUSED: an MTP GVFS mount is already active."
        fi
    fi

    if ((run_status == 0)) && have fuser; then
        owners="$(fuser "$usb_node" 2>/dev/null || true)"
        if [[ -n "$owners" ]]; then
            set_failure 9 "REFUSED: the Nokia USB node is open by process(es): $owners"
        fi
    fi

    if ((run_status == 0)); then
        detect_output="$(timeout --signal=TERM --kill-after=5s 45s mtp-detect 2>&1)"
        detect_status=$?
        if ((detect_status != 0)); then
            set_failure 10 "REFUSED: mtp-detect exited $detect_status."
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
                set_failure 11 "REFUSED: did not prove exactly one read/write Mass memory store."
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
            set_failure 12 "REFUSED: preflight folder listing exited $folders_before_status."
        else
            preexisting_count="$(
                printf '%s\n' "$folders_before" |
                    awk -v name="$FOLDER_NAME" '$1 ~ /^[0-9]+$/ && $NF == name { count++ } END { print count+0 }'
            )"
            if [[ "$preexisting_count" != "0" ]]; then
                set_failure 13 "REFUSED: Mass memory already exposes a KAI folder."
            else
                say "PASS: persistent target folder is absent before deployment."
            fi
        fi
    fi

    if ((run_status == 0)); then
        create_output="$(
            timeout --signal=TERM --kill-after=5s 45s \
                mtp-newfolder "$FOLDER_NAME" 0 "$storage_id_dec" 2>&1
        )"
        create_status=$?
        printf '\n=== Persistent folder creation ===\n'
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
            set_failure 14 "PARTIAL: persistent folder creation was not cleanly proven."
        else
            say "PASS: created Mass memory:/KAI as folder ID $folder_id."
        fi
    fi

    if ((run_status == 0)); then
        send_output="$(
            timeout --signal=TERM --kill-after=5s 45s \
                mtp-sendfile "$LOCAL_PAYLOAD" "/$FOLDER_NAME" 2>&1
        )"
        send_status=$?
        printf '\n=== Field Deck upload ===\n'
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
            set_failure 15 "PARTIAL: Field Deck upload was not cleanly proven."
        else
            say "PASS: uploaded INDEX.HTM as file ID $file_id."
        fi
    fi

    if ((run_status == 0)); then
        get_output="$(
            timeout --signal=TERM --kill-after=5s 45s \
                mtp-getfile "$file_id" "$RETRIEVED" 2>&1
        )"
        get_status=$?
        printf '\n=== Deployed-object retrieval ===\n'
        printf '%s\n' "$get_output" | redact
        if ((get_status != 0)) || [[ ! -f "$RETRIEVED" ]]; then
            set_failure 16 "PARTIAL: deployed-object retrieval was not cleanly proven."
        else
            retrieved_bytes="$(wc -c <"$RETRIEVED")"
            retrieved_sha="$(sha256sum "$RETRIEVED" | awk '{print $1}')"
            say "Retrieved bytes: $retrieved_bytes"
            say "Retrieved SHA-256: $retrieved_sha"
            if [[ "$retrieved_bytes" != "$EXPECTED_PAYLOAD_BYTES" || \
                  "$retrieved_sha" != "$EXPECTED_PAYLOAD_SHA" ]] || \
               ! cmp -s -- "$LOCAL_PAYLOAD" "$RETRIEVED"; then
                set_failure 17 "FAIL: deployed Field Deck does not match the allowlisted host payload."
            else
                payload_verified=1
                say "PASS: deployed Field Deck is byte-identical to the host payload."
            fi
        fi
    fi

    if ((folder_created == 1)); then
        folders_after="$(timeout --signal=TERM --kill-after=5s 45s mtp-folders 2>&1)"
        folders_after_status=$?
        if ((folders_after_status != 0)); then
            set_failure 18 "PARTIAL: post-deployment folder listing exited $folders_after_status."
        else
            deployed_count="$(
                printf '%s\n' "$folders_after" |
                    awk -v name="$FOLDER_NAME" '$1 ~ /^[0-9]+$/ && $NF == name { count++ } END { print count+0 }'
            )"
            if [[ "$deployed_count" != "1" ]]; then
                set_failure 19 "PARTIAL: expected exactly one visible KAI folder after deployment."
            else
                folder_visible=1
                say "PASS: exactly one persistent KAI folder is visible after deployment."
            fi
        fi
    fi

    if ((run_status == 0 && folder_created == 1 && file_created == 1 && \
          payload_verified == 1 && folder_visible == 1)); then
        say "PASS: Field Deck deployed and verified at Mass memory:/KAI/INDEX.HTM"
    elif ((folder_created == 1)); then
        say "RESIDUE: Mass memory:/KAI was created and deliberately not auto-deleted."
    fi
    say "UTC finish: $(date -u --iso-8601=seconds 2>/dev/null || date -u)"
} >"$REPORT" 2>&1

cat >"$NEXT_FILE" <<EOF
Nokia E7 Field Deck deployment finished with status ${run_status}.

Target: Mass memory:/KAI/INDEX.HTM
Folder object ID: ${folder_id:-unproven}
File object ID: ${file_id:-unproven}
Folder created: ${folder_created}
File created: ${file_created}
Payload verified: ${payload_verified}
KAI folder visible: ${folder_visible}

The deployment is persistent. No cleanup was requested or attempted.

Expected shareable files:
  ${RUN_NAME}.tar.gz
  ${RUN_NAME}.tar.gz.sha256
EOF

if ! have tar || ! have gzip || ! have sha256sum; then
    say "PARTIAL: report created, but packaging tools are unavailable."
    say "Report: $REPORT"
    exit 20
fi

tar -czf "$BUNDLE" -C "$START_DIR" "$RUN_NAME" || exit 21
(
    cd "$START_DIR" || exit 1
    sha256sum "$(basename "$BUNDLE")" >"$(basename "$BUNDLE_SUM")"
) || exit 22

if ((run_status == 0)); then
    say "PASS: Nokia E7 Field Deck deployed persistently and verified."
else
    say "PARTIAL: Nokia E7 Field Deck deployment status $run_status."
fi
say "Bundle:   $BUNDLE"
say "Checksum: $BUNDLE_SUM"
say "No existing phone object was changed or deleted."

exit "$run_status"
