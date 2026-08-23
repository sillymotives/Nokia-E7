#!/usr/bin/env bash
# Nokia E7 mass-memory census, version 1.
# Mounts the uniquely proven E7 VFAT partition read-only, records names and
# metadata (never file contents), then unmounts it.

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

readonly START_DIR="$(pwd -P)"
case "$START_DIR/" in
    /media/*|/run/media/*|/mnt/*)
        say "REFUSED: run from host storage, not $START_DIR"
        exit 2
        ;;
esac

readonly STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
readonly RUN_NAME="nokia-e7-mass-memory-census-${STAMP}"
readonly RUN_DIR="${START_DIR}/${RUN_NAME}"
readonly REPORT="${RUN_DIR}/mass-memory-census.txt"
readonly NEXT_FILE="${RUN_DIR}/NEXT.txt"
readonly BUNDLE="${START_DIR}/${RUN_NAME}.tar.gz"
readonly BUNDLE_SUM="${BUNDLE}.sha256"

mkdir -m 700 -- "$RUN_DIR" || exit 1
: >"$REPORT"

mounted_by_script=0
source_partition=""

cleanup() {
    if ((mounted_by_script)) && [[ -n "$source_partition" ]]; then
        {
            say "Cleanup: unmounting $source_partition"
            if udisksctl unmount --block-device "$source_partition"; then
                mounted_by_script=0
                say "Cleanup: unmount succeeded."
            else
                say "WARNING: cleanup unmount failed; check $source_partition manually."
            fi
        } >>"$REPORT" 2>&1
    fi
}
trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

run_status=0
source_device=""
mountpoint=""

{
    say "NOKIA E7 MASS-MEMORY CENSUS"
    say "Script version: $SCRIPT_VERSION"
    say "UTC start: $(date -u --iso-8601=seconds 2>/dev/null || date -u)"
    say "Policy: verified read-only mount; names and metadata only"

    for required in lsusb lsblk findmnt udisksctl find sort awk sed grep df wc tar gzip sha256sum; do
        if ! have "$required"; then
            say "REFUSED: required command is absent: $required"
            run_status=2
        fi
    done

    if ((run_status == 0)) && ! lsusb | grep -Eq '0421:0333.*E7-00'; then
        say "REFUSED: Nokia E7 mass-storage USB identity 0421:0333 is absent."
        run_status=3
    fi

    if ((run_status == 0)); then
        mapfile -t candidates < <(
            lsblk -dnbpo NAME,MODEL,TRAN,RM,SIZE |
                awk '$2 == "S60" && $3 == "usb" && $4 == "1" && $5 > 15000000000 && $5 < 17000000000 {print $1}'
        )
        say "Matching Nokia S60 disk count: ${#candidates[@]}"
        if ((${#candidates[@]} != 1)); then
            say "REFUSED: expected exactly one removable 15-17 GB USB S60 disk."
            run_status=4
        else
            source_device="${candidates[0]}"
            say "Verified source disk: $source_device"
            lsblk -o NAME,PATH,MODEL,SIZE,FSTYPE,RO,RM,TRAN,MOUNTPOINTS "$source_device"
        fi
    fi

    if ((run_status == 0)); then
        mapfile -t mounted_nodes < <(
            lsblk -lnpo NAME,MOUNTPOINT "$source_device" |
                awk '$2 != "" {print $1}'
        )
        if ((${#mounted_nodes[@]} != 0)); then
            say "REFUSED: the Nokia disk is already mounted; state was not changed."
            printf 'mounted_node=%s\n' "${mounted_nodes[@]}"
            run_status=5
        fi
    fi

    if ((run_status == 0)); then
        mapfile -t partitions < <(
            lsblk -lnpo NAME,TYPE,FSTYPE "$source_device" |
                awk '$2 == "part" && $3 == "vfat" {print $1}'
        )
        say "Matching VFAT partition count: ${#partitions[@]}"
        if ((${#partitions[@]} != 1)); then
            say "REFUSED: expected exactly one VFAT partition on the Nokia disk."
            run_status=6
        else
            source_partition="${partitions[0]}"
            say "Verified source partition: $source_partition"
        fi
    fi

    if ((run_status == 0)); then
        say "Mount request: ro,nosuid,nodev,noexec"
        if udisksctl mount --block-device "$source_partition" --options ro,nosuid,nodev,noexec; then
            mounted_by_script=1
        else
            say "REFUSED: read-only mount request failed."
            run_status=7
        fi
    fi

    if ((run_status == 0)); then
        mountpoint="$(findmnt -rn -S "$source_partition" -o TARGET | sed -n '1p')"
        mount_options="$(findmnt -rn -S "$source_partition" -o OPTIONS | sed -n '1p')"
        say "Observed mountpoint: $mountpoint"
        say "Observed options: $mount_options"

        if [[ -z "$mountpoint" || ! -d "$mountpoint" ]]; then
            say "REFUSED: mountpoint could not be resolved."
            run_status=8
        elif [[ ",$mount_options," != *,ro,* ]]; then
            say "REFUSED: kernel did not report the mount read-only."
            run_status=9
        elif [[ ",$mount_options," != *,nosuid,* || ",$mount_options," != *,nodev,* || ",$mount_options," != *,noexec,* ]]; then
            say "REFUSED: one or more defensive mount options are absent."
            run_status=10
        fi
    fi

    if ((run_status == 0)); then
        say "PASS: read-only mount boundary verified."

        printf '\n=== Filesystem summary ===\n'
        findmnt -rn -S "$source_partition" -o SOURCE,TARGET,FSTYPE,OPTIONS
        df -h -- "$mountpoint"

        printf '\n=== Object counts ===\n'
        printf 'directories='; find "$mountpoint" -xdev -type d -printf . | wc -c
        printf 'files='; find "$mountpoint" -xdev -type f -printf . | wc -c
        printf 'symlinks='; find "$mountpoint" -xdev -type l -printf . | wc -c

        printf '\n=== Top-level objects ===\n'
        find "$mountpoint" -xdev -mindepth 1 -maxdepth 1 \
            -printf '%y\t%s\t%TY-%Tm-%TdT%TH:%TM:%TS\t%f\n' |
            sort | sed -n 'l'

        printf '\n=== Important Symbian roots present ===\n'
        for relative in private resource sys system data cities documents downloads images install music sounds videos; do
            if [[ -e "$mountpoint/$relative" ]]; then
                printf 'present\t%s\n' "$relative"
            else
                printf 'absent\t%s\n' "$relative"
            fi
        done

        printf '\n=== File extension counts (top 120) ===\n'
        find "$mountpoint" -xdev -type f -printf '%f\n' |
            awk '
                {
                    name=tolower($0)
                    if (name !~ /\./) { ext="[none]" }
                    else { sub(/^.*\./, "", name); ext="." name }
                    count[ext]++
                }
                END { for (ext in count) print count[ext] "\t" ext }
            ' |
            sort -nr | sed -n '1,120p' | sed -n 'l'

        printf '\n=== Largest files (top 160; metadata only) ===\n'
        find "$mountpoint" -xdev -type f -printf '%s\t%P\n' |
            sort -nr | sed -n '1,160p' | sed -n 'l'

        printf '\n=== Bounded tree (maximum depth 5; first 20000 objects) ===\n'
        find "$mountpoint" -xdev -mindepth 1 -maxdepth 5 \
            -printf '%y\t%s\t%TY-%Tm-%TdT%TH:%TM:%TS\t%P\n' |
            sort | sed -n '1,20000p' | sed -n 'l'
    fi
} >>"$REPORT" 2>&1

if ((mounted_by_script)); then
    {
        say "Unmounting verified Nokia partition: $source_partition"
        if udisksctl unmount --block-device "$source_partition"; then
            mounted_by_script=0
            say "PASS: Nokia partition unmounted."
        else
            say "ERROR: normal unmount failed; cleanup will retry."
            run_status=11
        fi
    } >>"$REPORT" 2>&1
fi

if ((mounted_by_script)); then
    cleanup
fi

{
    say "UTC finish: $(date -u --iso-8601=seconds 2>/dev/null || date -u)"
    if ((run_status == 0)); then
        say "PASS: metadata-only mass-memory census complete."
    else
        say "PARTIAL: census status $run_status."
    fi
} >>"$REPORT"

cat >"$NEXT_FILE" <<EOF
Nokia E7 mass-memory census finished with status ${run_status}.

This bundle contains filenames and filesystem metadata. Keep it private.

Expected shareable files:
  ${RUN_NAME}.tar.gz
  ${RUN_NAME}.tar.gz.sha256
EOF

if ! have tar || ! have gzip || ! have sha256sum; then
    say "PARTIAL: report created, but packaging tools are unavailable."
    say "Report: $REPORT"
    exit 12
fi

tar -czf "$BUNDLE" -C "$START_DIR" "$RUN_NAME" || exit 13
(
    cd "$START_DIR" || exit 1
    sha256sum "$(basename "$BUNDLE")" >"$(basename "$BUNDLE_SUM")"
) || exit 14

if ((mounted_by_script == 0)); then
    trap - EXIT HUP INT TERM
fi

if ((run_status == 0)); then
    say "PASS: Nokia E7 mass-memory census complete."
else
    say "PARTIAL: Nokia E7 mass-memory census status $run_status."
fi
say "Bundle:   $BUNDLE"
say "Checksum: $BUNDLE_SUM"
if ((mounted_by_script == 0)); then
    say "The phone partition is unmounted. No file content was read."
else
    say "WARNING: the phone partition still appears mounted; exit cleanup will retry."
fi

exit "$run_status"
