#!/usr/bin/env bash
# Build conservative imported-media fixtures for the Nokia E7.

set -euo pipefail

export LC_ALL=C
export LANG=C

readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
readonly ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd -P)"
readonly OUTPUT_DIR="$ROOT/output/media"

for required in ffmpeg ffprobe mkdir; do
    if ! command -v "$required" >/dev/null 2>&1; then
        printf 'Missing required command: %s\n' "$required" >&2
        exit 2
    fi
done

mkdir -p -- "$OUTPUT_DIR"

ffmpeg -nostdin -hide_banner -loglevel error -n \
    -f lavfi -i 'smptebars=size=640x360:rate=1' \
    -frames:v 1 \
    -vf "drawbox=x=24:y=24:w=592:h=76:color=black@0.78:t=fill,drawtext=text='KAI IMAGE V1  640x360  JPEG':fontcolor=white:fontsize=28:x=(w-text_w)/2:y=48" \
    -map_metadata -1 -fflags +bitexact -flags:v +bitexact \
    -c:v mjpeg -pix_fmt yuvj420p -q:v 3 \
    "$OUTPUT_DIR/KAI-IMAGE-V1.JPG"

ffmpeg -nostdin -hide_banner -loglevel error -n \
    -f lavfi -i 'sine=frequency=440:sample_rate=44100:duration=8' \
    -af 'pan=stereo|c0=c0|c1=c0,afade=t=in:st=0:d=0.15,afade=t=out:st=7.7:d=0.3' \
    -map_metadata -1 -fflags +bitexact -flags:a +bitexact \
    -c:a libmp3lame -b:a 128k -ar 44100 -ac 2 \
    -id3v2_version 3 -write_id3v1 1 \
    -metadata title='KAI Tone Alpha' \
    -metadata artist='KAI Test' \
    -metadata album='E7 Native Media V1' \
    -metadata track='1/2' \
    -metadata date='2026' \
    -metadata genre='Test' \
    "$OUTPUT_DIR/KAI-TRACK-01.MP3"

ffmpeg -nostdin -hide_banner -loglevel error -n \
    -f lavfi -i 'sine=frequency=660:sample_rate=44100:duration=8' \
    -af 'pan=stereo|c0=c0|c1=c0,afade=t=in:st=0:d=0.15,afade=t=out:st=7.7:d=0.3' \
    -map_metadata -1 -fflags +bitexact -flags:a +bitexact \
    -c:a libmp3lame -b:a 128k -ar 44100 -ac 2 \
    -id3v2_version 3 -write_id3v1 1 \
    -metadata title='KAI Tone Beta' \
    -metadata artist='KAI Test' \
    -metadata album='E7 Native Media V1' \
    -metadata track='2/2' \
    -metadata date='2026' \
    -metadata genre='Test' \
    "$OUTPUT_DIR/KAI-TRACK-02.MP3"

ffmpeg -nostdin -hide_banner -loglevel error -n \
    -f lavfi -i 'testsrc2=size=640x360:rate=25:duration=6' \
    -f lavfi -i 'sine=frequency=523.25:sample_rate=44100:duration=6' \
    -vf "drawbox=x=12:y=12:w=616:h=54:color=black@0.72:t=fill,drawtext=text='KAI VIDEO V1  H264 BASELINE + AAC':fontcolor=white:fontsize=22:x=(w-text_w)/2:y=28" \
    -af 'pan=stereo|c0=c0|c1=c0,afade=t=in:st=0:d=0.15,afade=t=out:st=5.7:d=0.3' \
    -map_metadata -1 -fflags +bitexact -flags:v +bitexact -flags:a +bitexact \
    -c:v libx264 -preset slow -profile:v baseline -level:v 3.0 \
    -pix_fmt yuv420p -b:v 650k -maxrate 800k -bufsize 1600k \
    -g 50 -keyint_min 25 -sc_threshold 0 -bf 0 -refs 1 \
    -c:a aac -profile:a aac_low -b:a 96k -ar 44100 -ac 2 \
    -metadata title='KAI Video V1' \
    -metadata artist='KAI Test' \
    -metadata creation_time='2026-08-23T00:00:00Z' \
    -movflags +faststart -shortest \
    "$OUTPUT_DIR/KAI-VIDEO-V1.MP4"

printf '%s\n' \
    "$OUTPUT_DIR/KAI-IMAGE-V1.JPG" \
    "$OUTPUT_DIR/KAI-TRACK-01.MP3" \
    "$OUTPUT_DIR/KAI-TRACK-02.MP3" \
    "$OUTPUT_DIR/KAI-VIDEO-V1.MP4"
