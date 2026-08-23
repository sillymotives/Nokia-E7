#!/usr/bin/env bash
# Nokia E7 track-aware native-music deployment, version 2.
# Creates Mass memory:/KAI-MUSIC-V2, sends two fixed MP3s as MTP track
# objects with explicit metadata, creates a native playlist object, proves the
# resulting MTP model, and deliberately leaves all verified objects in place.

set -u
set -o pipefail

export LC_ALL=C.UTF-8
export LANG=C.UTF-8
umask 077

readonly SCRIPT_VERSION="2.1"
readonly FOLDER_NAME="KAI-MUSIC-V2"
readonly ALBUM_NAME="E7 Native Music V2"
readonly PLAYLIST_NAME="KAI Playlist V2"
readonly ARTIST_NAME="KAI Test"
readonly GENRE_NAME="Test"
readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
readonly TOOLKIT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd -P)"
readonly SYSFS_USB_ROOT="${E7_SYSFS_USB_ROOT:-/sys/bus/usb/devices}"

readonly -a TRACK_NAMES=("KAI-TRACK-01.MP3" "KAI-TRACK-02.MP3")
readonly -a TRACK_PATHS=(
    "$TOOLKIT_ROOT/output/media/KAI-TRACK-01.MP3"
    "$TOOLKIT_ROOT/output/media/KAI-TRACK-02.MP3"
)
readonly -a TRACK_TITLES=("KAI Tone Alpha" "KAI Tone Beta")
readonly -a EXPECTED_BYTES=("129419" "129418")
readonly -a EXPECTED_SHAS=(
    "b01d58217b1455b168b03a4204f26a050df140b965076215161e1ec279063215"
    "3052738ee6a1c936f4411ac37721149609c32fbbb3eb30b40b266b811dda547b"
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

extract_track_block() {
    local wanted_id="$1"
    awk -v wanted_id="$wanted_id" '
        /^Track ID:/ {
            if (active) exit
            active = ($3 == wanted_id)
        }
        active { print }
    '
}

extract_album_block() {
    local wanted_id="$1"
    awk -v wanted_id="$wanted_id" '
        /^Album ID:/ {
            if (active) exit
            active = ($3 == wanted_id)
        }
        active { print }
    '
}

extract_playlist_block() {
    local wanted_id="$1"
    awk -v wanted_id="$wanted_id" '
        /^Playlist ID:/ {
            if (active) exit
            active = ($3 == wanted_id)
        }
        active { print }
    '
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
readonly RUN_NAME="nokia-e7-native-music-v2-${STAMP}"
readonly RUN_DIR="${START_DIR}/${RUN_NAME}"
readonly REPORT="${RUN_DIR}/native-music-v2.txt"
readonly NEXT_FILE="${RUN_DIR}/NEXT.txt"
readonly BUNDLE="${START_DIR}/${RUN_NAME}.tar.gz"
readonly BUNDLE_SUM="${BUNDLE}.sha256"

mkdir -m 700 -- "$RUN_DIR" || exit 1

run_status=0
usb_node=""
storage_id_hex=""
storage_id_dec=""
folder_id=""
album_id=""
playlist_id=""
folder_created=0
folder_visible=0
album_verified=0
playlist_verified=0
verified_count=0
declare -a track_ids=("" "")
declare -a track_created=("0" "0")
declare -a track_verified=("0" "0")

{
    say "NOKIA E7 TRACK-AWARE NATIVE MUSIC V2 DEPLOYMENT"
    say "Script version: $SCRIPT_VERSION"
    say "UTC start: $(date -u --iso-8601=seconds 2>/dev/null || date -u)"
    say "Filesystem policy: create only Mass memory:/$FOLDER_NAME"
    say "MTP policy: create two fixed track objects, one uniquely named album, and one uniquely named playlist"
    say "Payload policy: send only two fixed, hash-allowlisted MP3 files"
    say "Persistence: successful objects are deliberately left on the phone"

    for required in awk basename cmp date find grep gzip id lsusb \
        mtp-albums mtp-detect mtp-folders mtp-getfile mtp-newfolder \
        mtp-newplaylist mtp-playlists mtp-sendtr mtp-tracks sed sha256sum \
        tar timeout tr udevadm wc; do
        if ! have "$required"; then
            set_failure 2 "REFUSED: required command is absent: $required"
        fi
    done

    if ((run_status == 0)); then
        for index in "${!TRACK_NAMES[@]}"; do
            payload="${TRACK_PATHS[$index]}"
            name="${TRACK_NAMES[$index]}"
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
                set_failure 5 "REFUSED: $name does not match the v2 allowlist."
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
        for device in "$SYSFS_USB_ROOT"/*; do
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
        for device in "$SYSFS_USB_ROOT"/*; do
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
        gvfs_dir="${E7_GVFS_DIR:-/run/user/$(id -u)/gvfs}"
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
    elif ((run_status == 0)); then
        say "INFO: fuser is absent; optional USB-node ownership check skipped."
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
        albums_before="$(timeout --signal=TERM --kill-after=5s 45s mtp-albums 2>&1)"
        albums_before_status=$?
        if ((albums_before_status != 0)); then
            set_failure 16 "REFUSED: preflight album listing exited $albums_before_status."
        else
            preexisting_album_count="$(
                printf '%s\n' "$albums_before" |
                    awk -v name="$ALBUM_NAME" '
                        /^[[:space:]]+Name:/ {
                            value=$0
                            sub(/^[[:space:]]+Name:[[:space:]]*/, "", value)
                            if (value == name) count++
                        }
                        END { print count+0 }
                    '
            )"
            if [[ "$preexisting_album_count" != "0" ]]; then
                set_failure 17 "REFUSED: album $ALBUM_NAME already exists on the phone."
            else
                say "PASS: uniquely named album is absent before deployment."
            fi
        fi
    fi

    if ((run_status == 0)); then
        playlists_before="$(timeout --signal=TERM --kill-after=5s 45s mtp-playlists 2>&1)"
        playlists_before_status=$?
        if ((playlists_before_status != 0)); then
            set_failure 18 "REFUSED: preflight playlist listing exited $playlists_before_status."
        else
            preexisting_playlist_count="$(
                printf '%s\n' "$playlists_before" |
                    awk -v name="$PLAYLIST_NAME" '
                        /^[[:space:]]+Name:/ {
                            value=$0
                            sub(/^[[:space:]]+Name:[[:space:]]*/, "", value)
                            if (value == name) count++
                        }
                        END { print count+0 }
                    '
            )"
            if [[ "$preexisting_playlist_count" != "0" ]]; then
                set_failure 19 "REFUSED: playlist $PLAYLIST_NAME already exists on the phone."
            else
                say "PASS: uniquely named playlist is absent before deployment."
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
            set_failure 20 "PARTIAL: persistent folder creation was not cleanly proven."
        else
            say "PASS: created Mass memory:/$FOLDER_NAME as folder ID $folder_id."
        fi
    fi

    if ((run_status == 0)); then
        for index in "${!TRACK_NAMES[@]}"; do
            name="${TRACK_NAMES[$index]}"
            payload="${TRACK_PATHS[$index]}"
            title="${TRACK_TITLES[$index]}"
            track_number="$((index + 1))"
            send_output="$(
                timeout --signal=TERM --kill-after=5s 60s \
                    mtp-sendtr -q \
                        -t "$title" \
                        -a "$ARTIST_NAME" \
                        -A "$ARTIST_NAME" \
                        -l "$ALBUM_NAME" \
                        -g "$GENRE_NAME" \
                        -n "$track_number" \
                        -y 2026 \
                        -d 8 \
                        -s "$storage_id_dec" \
                        "$payload" "/$FOLDER_NAME/$name" 2>&1
            )"
            send_status=$?
            printf '\n=== Track-aware upload: %s ===\n' "$name"
            printf '%s\n' "$send_output" | redact
            mapfile -t returned_track_ids < <(
                printf '%s\n' "$send_output" |
                    sed -n -E 's/^New track ID: ([0-9]+)$/\1/p'
            )
            if ((${#returned_track_ids[@]} == 1)) && \
               [[ "${returned_track_ids[0]}" =~ ^[1-9][0-9]*$ ]]; then
                track_ids[$index]="${returned_track_ids[0]}"
                track_created[$index]=1
            fi
            if ((send_status != 0)) || ((track_created[$index] == 0)); then
                set_failure 21 "PARTIAL: track-aware upload of $name was not cleanly proven."
                break
            fi
            say "PASS: uploaded $name as track ID ${track_ids[$index]}."

            retrieved="${RUN_DIR}/RETRIEVED-${name}"
            get_output="$(
                timeout --signal=TERM --kill-after=5s 45s \
                    mtp-getfile "${track_ids[$index]}" "$retrieved" 2>&1
            )"
            get_status=$?
            printf '\n=== Track retrieval: %s ===\n' "$name"
            printf '%s\n' "$get_output" | redact
            if ((get_status != 0)) || [[ ! -f "$retrieved" ]]; then
                set_failure 22 "PARTIAL: retrieval of $name was not cleanly proven."
                break
            fi
            retrieved_bytes="$(wc -c <"$retrieved")"
            retrieved_sha="$(sha256sum "$retrieved" | awk '{print $1}')"
            say "Retrieved bytes: $retrieved_bytes"
            say "Retrieved SHA-256: $retrieved_sha"
            if [[ "$retrieved_bytes" != "${EXPECTED_BYTES[$index]}" || \
                  "$retrieved_sha" != "${EXPECTED_SHAS[$index]}" ]] || \
               ! cmp -s -- "$payload" "$retrieved"; then
                set_failure 23 "FAIL: retrieved $name does not match the host original."
                break
            fi
            track_verified[$index]=1
            verified_count=$((verified_count + 1))
            say "PASS: retrieved $name is byte-identical to the host payload."
        done
    fi

    if ((run_status == 0)); then
        tracks_after="$(timeout --signal=TERM --kill-after=5s 60s mtp-tracks 2>&1)"
        tracks_after_status=$?
        printf '\n=== MTP track metadata read-back ===\n'
        printf '%s\n' "$tracks_after" | redact
        if ((tracks_after_status != 0)); then
            set_failure 24 "PARTIAL: track metadata listing exited $tracks_after_status."
        else
            for index in "${!TRACK_NAMES[@]}"; do
                block="$(printf '%s\n' "$tracks_after" | extract_track_block "${track_ids[$index]}")"
                track_number="$((index + 1))"
                if [[ -z "$block" ]] || \
                   ! grep -Fxq "   Title: ${TRACK_TITLES[$index]}" <<<"$block" || \
                   ! grep -Fxq "   Artist: $ARTIST_NAME" <<<"$block" || \
                   ! grep -Fxq "   Genre: $GENRE_NAME" <<<"$block" || \
                   ! grep -Fxq "   Album: $ALBUM_NAME" <<<"$block" || \
                   ! grep -Fxq "   Origfilename: ${TRACK_NAMES[$index]}" <<<"$block" || \
                   ! grep -Fxq "   Track number: $track_number" <<<"$block" || \
                   ! grep -Fxq "   Duration: 8000 milliseconds" <<<"$block" || \
                   ! grep -Fxq "   File size ${EXPECTED_BYTES[$index]} bytes" <<<"$block"; then
                    set_failure 25 "PARTIAL: MTP metadata read-back mismatch for track ID ${track_ids[$index]}."
                    break
                fi
                say "PASS: explicit metadata is readable for track ID ${track_ids[$index]}."
            done
        fi
    fi

    if ((run_status == 0)); then
        albums_after="$(timeout --signal=TERM --kill-after=5s 60s mtp-albums 2>&1)"
        albums_after_status=$?
        printf '\n=== MTP album read-back ===\n'
        printf '%s\n' "$albums_after" | redact
        if ((albums_after_status != 0)); then
            set_failure 26 "PARTIAL: album listing exited $albums_after_status."
        else
            mapfile -t album_ids < <(
                printf '%s\n' "$albums_after" |
                    awk -v name="$ALBUM_NAME" '
                        /^Album ID:/ { id=$3 }
                        /^[[:space:]]+Name:/ {
                            value=$0
                            sub(/^[[:space:]]+Name:[[:space:]]*/, "", value)
                            if (value == name) print id
                        }
                    '
            )
            if ((${#album_ids[@]} == 1)) && [[ "${album_ids[0]}" =~ ^[1-9][0-9]*$ ]]; then
                album_id="${album_ids[0]}"
                album_block="$(printf '%s\n' "$albums_after" | extract_album_block "$album_id")"
                if grep -Fq "    Artist: $ARTIST_NAME" <<<"$album_block" && \
                   grep -Fq "    Genre:  $GENRE_NAME" <<<"$album_block" && \
                   grep -Fq "    Tracks: 2" <<<"$album_block"; then
                    album_verified=1
                    say "PASS: native album object $album_id contains two tracks."
                else
                    set_failure 27 "PARTIAL: native album object fields did not match."
                fi
            else
                set_failure 28 "PARTIAL: did not find exactly one native album named $ALBUM_NAME."
            fi
        fi
    fi

    if ((run_status == 0)); then
        playlist_create_output="$(
            timeout --signal=TERM --kill-after=5s 45s \
                mtp-newplaylist \
                    -i "${track_ids[0]}" \
                    -i "${track_ids[1]}" \
                    -n "$PLAYLIST_NAME" \
                    -s "$storage_id_dec" \
                    -p "$folder_id" 2>&1
        )"
        playlist_create_status=$?
        printf '\n=== Native playlist creation ===\n'
        printf '%s\n' "$playlist_create_output" | redact
        mapfile -t playlist_ids < <(
            printf '%s\n' "$playlist_create_output" |
                sed -n -E 's/^Created new playlist: ([0-9]+)$/\1/p'
        )
        if ((${#playlist_ids[@]} == 1)) && [[ "${playlist_ids[0]}" =~ ^[1-9][0-9]*$ ]]; then
            playlist_id="${playlist_ids[0]}"
        fi
        if ((playlist_create_status != 0)) || [[ -z "$playlist_id" ]]; then
            set_failure 29 "PARTIAL: native playlist creation was not cleanly proven."
        else
            say "PASS: created native playlist object $playlist_id."
        fi
    fi

    if ((run_status == 0)); then
        playlists_after="$(timeout --signal=TERM --kill-after=5s 60s mtp-playlists 2>&1)"
        playlists_after_status=$?
        printf '\n=== MTP playlist read-back ===\n'
        printf '%s\n' "$playlists_after" | redact
        if ((playlists_after_status != 0)); then
            set_failure 30 "PARTIAL: playlist listing exited $playlists_after_status."
        else
            playlist_block="$(printf '%s\n' "$playlists_after" | extract_playlist_block "$playlist_id")"
            mapfile -t playlist_track_ids < <(
                printf '%s\n' "$playlist_block" |
                    awk '
                        /^[[:space:]]+Tracks:/ { in_tracks=1; next }
                        in_tracks {
                            line=$0
                            sub(/^[[:space:]]+/, "", line)
                            split(line, fields, ":")
                            if (fields[1] ~ /^[0-9]+$/) print fields[1]
                        }
                    '
            )
            if [[ -z "$playlist_block" ]] || \
               ! grep -Fxq "   Name: $PLAYLIST_NAME" <<<"$playlist_block" || \
               ! grep -Fxq "   Parent ID: $folder_id" <<<"$playlist_block" || \
               ((${#playlist_track_ids[@]} != 2)) || \
               [[ "${playlist_track_ids[0]}" != "${track_ids[0]}" ]] || \
               [[ "${playlist_track_ids[1]}" != "${track_ids[1]}" ]]; then
                set_failure 31 "PARTIAL: native playlist read-back did not preserve name, parent, membership, and order."
            else
                playlist_verified=1
                say "PASS: native playlist contains Alpha then Beta by exact track ID."
            fi
        fi
    fi

    if ((folder_created == 1)); then
        folders_after="$(timeout --signal=TERM --kill-after=5s 45s mtp-folders 2>&1)"
        folders_after_status=$?
        if ((folders_after_status != 0)); then
            set_failure 32 "PARTIAL: post-deployment folder listing exited $folders_after_status."
        else
            deployed_count="$(
                printf '%s\n' "$folders_after" |
                    awk -v name="$FOLDER_NAME" '$1 ~ /^[0-9]+$/ && $NF == name { count++ } END { print count+0 }'
            )"
            if [[ "$deployed_count" != "1" ]]; then
                set_failure 33 "PARTIAL: expected exactly one visible $FOLDER_NAME folder."
            else
                folder_visible=1
                say "PASS: exactly one persistent $FOLDER_NAME folder is visible."
            fi
        fi
    fi

    if ((run_status == 0 && folder_created == 1 && verified_count == 2 && \
          album_verified == 1 && playlist_verified == 1 && folder_visible == 1)); then
        say "PASS: track-aware native-music v2 deployed and its MTP model is verified."
        say "Target: Mass memory:/$FOLDER_NAME"
    elif ((folder_created == 1)); then
        say "RESIDUE: one or more clearly named v2 objects may remain; no automatic cleanup was attempted."
    fi
    say "UTC finish: $(date -u --iso-8601=seconds 2>/dev/null || date -u)"
} >"$REPORT" 2>&1

cat >"$NEXT_FILE" <<EOF
Nokia E7 track-aware native-music v2 deployment finished with status ${run_status}.

Target: Mass memory:/${FOLDER_NAME}
Folder object ID: ${folder_id:-unproven}
Track 1 object ID: ${track_ids[0]:-unproven}
Track 2 object ID: ${track_ids[1]:-unproven}
Album object ID: ${album_id:-unproven}
Playlist object ID: ${playlist_id:-unproven}
Folder created: ${folder_created}
Tracks byte-verified: ${verified_count}/2
Album metadata verified: ${album_verified}
Playlist verified: ${playlist_verified}
Folder visible: ${folder_visible}

The deployment is persistent. No cleanup was requested or attempted.

On the phone, refresh Music player and inspect artist "${ARTIST_NAME}",
album "${ALBUM_NAME}", and playlist "${PLAYLIST_NAME}".

Expected shareable files:
  ${RUN_NAME}.tar.gz
  ${RUN_NAME}.tar.gz.sha256
EOF

if ! have tar || ! have gzip || ! have sha256sum; then
    say "PARTIAL: report created, but packaging tools are unavailable."
    say "Report: $REPORT"
    exit 34
fi

tar -czf "$BUNDLE" -C "$START_DIR" "$RUN_NAME" || exit 35
(
    cd "$START_DIR" || exit 1
    sha256sum "$(basename "$BUNDLE")" >"$(basename "$BUNDLE_SUM")"
) || exit 36

if ((run_status == 0)); then
    say "PASS: Nokia E7 track-aware native-music v2 deployed persistently and verified."
else
    say "PARTIAL: Nokia E7 track-aware native-music v2 deployment status $run_status."
fi
say "Bundle:   $BUNDLE"
say "Checksum: $BUNDLE_SUM"
say "No pre-existing phone object was changed or deleted."

exit "$run_status"
