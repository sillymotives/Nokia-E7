#!/usr/bin/env bash
# Nokia E7 imported native-media deployment, version 1.
# Creates Mass memory:/KAI-MEDIA-V1, uploads five fixed fixtures, retrieves and
# compares each one, then deliberately leaves the verified folder in place.

set -u
set -o pipefail

export LC_ALL=C.UTF-8
export LANG=C.UTF-8
umask 077

readonly SCRIPT_VERSION="1"
readonly FOLDER_NAME="KAI-MEDIA-V1"
readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
readonly TOOLKIT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd -P)"

readonly -a PAYLOAD_NAMES=(
    "KAI-IMAGE-V1.JPG"
    "KAI-TRACK-01.MP3"
    "KAI-TRACK-02.MP3"
    "KAI-PLAYLIST.M3U"
    "KAI-VIDEO-V1.MP4"
)
readonly -a PAYLOAD_PATHS=(
    "$TOOLKIT_ROOT/output/media/KAI-IMAGE-V1.JPG"
    "$TOOLKIT_ROOT/output/media/KAI-TRACK-01.MP3"
    "$TOOLKIT_ROOT/output/media/KAI-TRACK-02.MP3"
    "$TOOLKIT_ROOT/payloads/native-media-v1/KAI-PLAYLIST.M3U"
    "$TOOLKIT_ROOT/output/media/KAI-VIDEO-V1.MP4"
)
readonly -a EXPECTED_BYTES=("12454" "129419" "129418" "114" "562616")
readonly -a EXPECTED_SHAS=(
    "def9fb641a7b25e79874a2441065d6a5cb8df6e870d5fcb221bb94e9db015ef5"
    "b01d58217b1455b168b03a4204f26a050df140b965076215161e1ec279063215"
    "3052738ee6a1c936f4411ac37721149609c32fbbb3eb30b40b266b811dda547b"
    "d168564cfc280b56cfe0ecaf6f7af15e2143cca3cd780013146796c03df0d044"
    "aa9285f1fbb0c75d875fb484537e324775fcee9a50619891fa4672f1e23cc9bf"
)

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

if (($# != 0)); then
    say "Usage: $0"
    exit 2
fi

readonly START_DIR="$(pwd -P)"
case "$START_DIR/" in
    /media/*|/run/media/*|/mnt/*)
        say "REFUSED: run from host storage, not $START_DIR"
        exit 2
        ;;
esac

readonly STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
readonly RUN_NAME="nokia-e7-native-media-v1-${STAMP}"
readonly RUN_DIR="${START_DIR}/${RUN_NAME}"
readonly REPORT="${RUN_DIR}/native-media-v1.txt"
readonly NEXT_FILE="${RUN_DIR}/NEXT.txt"
readonly BUNDLE="${START_DIR}/${RUN_NAME}.tar.gz"
readonly BUNDLE_SUM="${BUNDLE}.sha256"

mkdir -m 700 -- "$RUN_DIR" || exit 1

run_status=0
usb_node=""
storage_id_hex=""
storage_id_dec=""
folder_id=""
folder_created=0
folder_visible=0
verified_count=0
declare -a file_ids=("" "" "" "" "")
declare -a file_created=("0" "0" "0" "0" "0")
declare -a file_verified=("0" "0" "0" "0" "0")

{
    say "NOKIA E7 NATIVE MEDIA V1 DEPLOYMENT"
    say "Script version: $SCRIPT_VERSION"
    say "UTC start: $(date -u --iso-8601=seconds 2>/dev/null || date -u)"
    say "Policy: create only Mass memory:/$FOLDER_NAME"
    say "Payload policy: upload only five fixed, hash-allowlisted files"
    say "Persistence: successful objects are deliberately left on the phone"

    for required in basename cmp find grep lsusb mtp-detect mtp-folders \
        mtp-getfile mtp-newfolder mtp-sendfile sed sha256sum tar timeout tr \
        udevadm wc awk gzip; do
        if ! have "$required"; then
            set_failure 2 "REFUSED: required command is absent: $required"
        fi
    done

    if ((run_status == 0)); then
        for index in "${!PAYLOAD_NAMES[@]}"; do
            payload="${PAYLOAD_PATHS[$index]}"
            name="${PAYLOAD_NAMES[$index]}"
            if [[ ! -f "$payload" || -L "$payload" ]]; then
                set_failure 3 "REFUSED: $name is absent, not regular, or a symlink."
                break
            fi
            if [[ "$(basename -- "$payload")" != "$name" ]]; then
                set_failure 4 "REFUSED: payload basename mismatch for $name."
                break
            fi
            actual_bytes="$(wc -c <"$payload")"
            actual_sha="$(sha256sum "$payload" | awk '{print $1}')"
            say "$name bytes: $actual_bytes"
            say "$name SHA-256: $actual_sha"
            if [[ "$actual_bytes" != "${EXPECTED_BYTES[$index]}" || \
                  "$actual_sha" != "${EXPECTED_SHAS[$index]}" ]]; then
                set_failure 5 "REFUSED: $name does not match the v1 allowlist."
                break
            fi
        done
    fi

    if ((run_status == 0)); then
        mapfile -t matches < <(lsusb -d 0421:0335 2>/dev/null)
        say "Matching Nokia Suite USB count: ${#matches[@]}"
        if ((${#matches[@]} != 1)) || [[ "${matches[0]}" != *E7-00* ]]; then
            set_failure 6 "REFUSED: expected exactly one Nokia E7-00 with USB ID 0421:0335."
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
            set_failure 7 "REFUSED: sysfs did not contain exactly one matching device."
        else
            busnum="$(read_one_line "${sysfs_matches[0]}/busnum")"
            devnum="$(read_one_line "${sysfs_matches[0]}/devnum")"
            if [[ "$busnum" =~ ^[0-9]+$ && "$devnum" =~ ^[0-9]+$ ]]; then
                printf -v usb_node '/dev/bus/usb/%03d/%03d' \
                    "$((10#$busnum))" "$((10#$devnum))"
                say "Proven USB node: $usb_node"
            else
                set_failure 8 "REFUSED: invalid bus or device number from sysfs."
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
            set_failure 9 "REFUSED: the Nokia is not the host's sole MTP candidate."
        fi
    fi

    if ((run_status == 0)); then
        gvfs_dir="/run/user/$(id -u)/gvfs"
        if [[ -d "$gvfs_dir" ]] && \
           find "$gvfs_dir" -mindepth 1 -maxdepth 1 -name 'mtp:*' \
                -print -quit | grep -q .; then
            set_failure 10 "REFUSED: an MTP GVFS mount is already active."
        fi
    fi

    if ((run_status == 0)) && have fuser; then
        owners="$(fuser "$usb_node" 2>/dev/null || true)"
        if [[ -n "$owners" ]]; then
            set_failure 11 "REFUSED: the Nokia USB node is open by process(es): $owners"
        fi
    fi

    if ((run_status == 0)); then
        detect_output="$(timeout --signal=TERM --kill-after=5s 45s mtp-detect 2>&1)"
        detect_status=$?
        if ((detect_status != 0)); then
            set_failure 12 "REFUSED: mtp-detect exited $detect_status."
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
                set_failure 13 "REFUSED: did not prove exactly one read/write Mass memory store."
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
            set_failure 14 "REFUSED: preflight folder listing exited $folders_before_status."
        else
            preexisting_count="$(
                printf '%s\n' "$folders_before" |
                    awk -v name="$FOLDER_NAME" '$1 ~ /^[0-9]+$/ && $NF == name { count++ } END { print count+0 }'
            )"
            if [[ "$preexisting_count" != "0" ]]; then
                set_failure 15 "REFUSED: $FOLDER_NAME already exists on the phone."
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
            set_failure 16 "PARTIAL: persistent folder creation was not cleanly proven."
        else
            say "PASS: created Mass memory:/$FOLDER_NAME as folder ID $folder_id."
        fi
    fi

    if ((run_status == 0)); then
        for index in "${!PAYLOAD_NAMES[@]}"; do
            name="${PAYLOAD_NAMES[$index]}"
            payload="${PAYLOAD_PATHS[$index]}"
            send_output="$(
                timeout --signal=TERM --kill-after=5s 45s \
                    mtp-sendfile "$payload" "/$FOLDER_NAME" 2>&1
            )"
            send_status=$?
            printf '\n=== Upload: %s ===\n' "$name"
            printf '%s\n' "$send_output" | redact
            mapfile -t returned_file_ids < <(
                printf '%s\n' "$send_output" |
                    sed -n -E 's/^New file ID: ([0-9]+)$/\1/p'
            )
            if ((${#returned_file_ids[@]} == 1)) && \
               [[ "${returned_file_ids[0]}" =~ ^[1-9][0-9]*$ ]]; then
                file_ids[$index]="${returned_file_ids[0]}"
                file_created[$index]=1
            fi
            if ((send_status != 0)) || ((file_created[$index] == 0)); then
                set_failure 17 "PARTIAL: upload of $name was not cleanly proven."
                break
            fi
            say "PASS: uploaded $name as file ID ${file_ids[$index]}."

            retrieved="${RUN_DIR}/RETRIEVED-${name}"
            get_output="$(
                timeout --signal=TERM --kill-after=5s 45s \
                    mtp-getfile "${file_ids[$index]}" "$retrieved" 2>&1
            )"
            get_status=$?
            printf '\n=== Retrieval: %s ===\n' "$name"
            printf '%s\n' "$get_output" | redact
            if ((get_status != 0)) || [[ ! -f "$retrieved" ]]; then
                set_failure 18 "PARTIAL: retrieval of $name was not cleanly proven."
                break
            fi
            retrieved_bytes="$(wc -c <"$retrieved")"
            retrieved_sha="$(sha256sum "$retrieved" | awk '{print $1}')"
            say "Retrieved bytes: $retrieved_bytes"
            say "Retrieved SHA-256: $retrieved_sha"
            if [[ "$retrieved_bytes" != "${EXPECTED_BYTES[$index]}" || \
                  "$retrieved_sha" != "${EXPECTED_SHAS[$index]}" ]] || \
               ! cmp -s -- "$payload" "$retrieved"; then
                set_failure 19 "FAIL: retrieved $name does not match the host original."
                break
            fi
            file_verified[$index]=1
            verified_count=$((verified_count + 1))
            say "PASS: retrieved $name is byte-identical to the host payload."
        done
    fi

    if ((folder_created == 1)); then
        folders_after="$(timeout --signal=TERM --kill-after=5s 45s mtp-folders 2>&1)"
        folders_after_status=$?
        if ((folders_after_status != 0)); then
            set_failure 20 "PARTIAL: post-deployment folder listing exited $folders_after_status."
        else
            deployed_count="$(
                printf '%s\n' "$folders_after" |
                    awk -v name="$FOLDER_NAME" '$1 ~ /^[0-9]+$/ && $NF == name { count++ } END { print count+0 }'
            )"
            if [[ "$deployed_count" != "1" ]]; then
                set_failure 21 "PARTIAL: expected exactly one visible $FOLDER_NAME folder."
            else
                folder_visible=1
                say "PASS: exactly one persistent $FOLDER_NAME folder is visible."
            fi
        fi
    fi

    if ((run_status == 0 && folder_created == 1 && verified_count == 5 && \
          folder_visible == 1)); then
        say "PASS: all native-media v1 fixtures deployed and verified."
        say "Target: Mass memory:/$FOLDER_NAME"
    elif ((folder_created == 1)); then
        say "RESIDUE: Mass memory:/$FOLDER_NAME was created and deliberately not auto-deleted."
    fi
    say "UTC finish: $(date -u --iso-8601=seconds 2>/dev/null || date -u)"
} >"$REPORT" 2>&1

cat >"$NEXT_FILE" <<EOF
Nokia E7 native-media v1 deployment finished with status ${run_status}.

Target: Mass memory:/${FOLDER_NAME}
Folder object ID: ${folder_id:-unproven}
Image object ID: ${file_ids[0]:-unproven}
Track 1 object ID: ${file_ids[1]:-unproven}
Track 2 object ID: ${file_ids[2]:-unproven}
Playlist object ID: ${file_ids[3]:-unproven}
Video object ID: ${file_ids[4]:-unproven}
Folder created: ${folder_created}
Files verified: ${verified_count}/5
Folder visible: ${folder_visible}

The deployment is persistent. No cleanup was requested or attempted.

On the phone, refresh Music player and inspect the KAI Test album and playlist.
Use Gallery or Files to open KAI-IMAGE-V1.JPG and KAI-VIDEO-V1.MP4.

Expected shareable files:
  ${RUN_NAME}.tar.gz
  ${RUN_NAME}.tar.gz.sha256
EOF

if ! have tar || ! have gzip || ! have sha256sum; then
    say "PARTIAL: report created, but packaging tools are unavailable."
    say "Report: $REPORT"
    exit 22
fi

tar -czf "$BUNDLE" -C "$START_DIR" "$RUN_NAME" || exit 23
(
    cd "$START_DIR" || exit 1
    sha256sum "$(basename "$BUNDLE")" >"$(basename "$BUNDLE_SUM")"
) || exit 24

if ((run_status == 0)); then
    say "PASS: Nokia E7 native-media v1 deployed persistently and verified."
else
    say "PARTIAL: Nokia E7 native-media v1 deployment status $run_status."
fi
say "Bundle:   $BUNDLE"
say "Checksum: $BUNDLE_SUM"
say "No existing phone object was changed or deleted."

exit "$run_status"

