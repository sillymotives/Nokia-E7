# Imported native-media probe v1

Prepared: 2026-08-23

## Purpose

Test the E7's imported-media and Music-player paths without confusing a codec
failure with an MTP transfer failure. The guarded deployment creates one new
folder, `Mass memory:/KAI-MEDIA-V1`, containing five hash-allowlisted fixtures.

| File | Conservative format | Native path under test |
| --- | --- | --- |
| `KAI-IMAGE-V1.JPG` | Baseline JPEG, 640x360, YUV 4:2:0 | Gallery/image viewer indexing and rendering |
| `KAI-TRACK-01.MP3` | MP3, 44.1 kHz stereo, 128 kb/s CBR, ID3v2.3 | Music decoding and metadata for track 1 |
| `KAI-TRACK-02.MP3` | MP3, 44.1 kHz stereo, 128 kb/s CBR, ID3v2.3 | Track ordering and transition to track 2 |
| `KAI-PLAYLIST.M3U` | Extended M3U with ASCII relative paths | Native playlist discovery and ordering |
| `KAI-VIDEO-V1.MP4` | H.264 Constrained Baseline Level 3.0, 640x360 at 25 fps; AAC-LC 44.1 kHz stereo | Imported video and audio playback |

The two MP3 files are tagged as artist `KAI Test`, album
`E7 Native Media V1`, titles `KAI Tone Alpha` and `KAI Tone Beta`, and tracks
`1/2` and `2/2`. Alpha is an eight-second 440 Hz tone; Beta is an eight-second
660 Hz tone. The video is six seconds of a moving test pattern with a 523.25 Hz
tone and an identifying title bar.

All streams fully decode on the host. The JPEG and first video frame were also
visually inspected for clipping, corruption, and legibility.

## Host deployment

Put the E7 in Nokia Suite USB mode, close any graphical file manager using the
phone, and run:

```bash
./scripts/e7-deploy-native-media-v1.sh
```

The script verifies all five local hashes, proves the E7 and its read/write
Mass memory store, refuses an existing `KAI-MEDIA-V1` folder, uploads only the
five allowlisted files, retrieves every created object by its returned MTP ID,
and compares every retrieval byte-for-byte. It overwrites and deletes nothing.

## On-device sequence

Wi-Fi may remain disconnected. No step requires an account or service.

1. Open Gallery or Files and display `KAI-IMAGE-V1.JPG`. Confirm the colour
   bars and complete `KAI IMAGE V1 640x360 JPEG` title are visible.
2. In Music player, use its refresh/rescan command if the two tracks do not
   appear automatically.
3. Confirm artist `KAI Test`, album `E7 Native Media V1`, both titles, and the
   order Alpha then Beta.
4. Play both tracks. Confirm Alpha is the lower tone, Beta the higher tone,
   automatic track transition works, and seeking does not break playback.
5. Leave Music player while a track is playing. Confirm background playback
   continues, then return and exercise pause/resume, repeat, and shuffle.
6. Record whether `KAI-PLAYLIST.M3U` appears as a native playlist and, if so,
   whether it contains both tracks in order. Playlist absence is a partial
   result, not failure of MP3 playback.
7. Open `KAI-VIDEO-V1.MP4` through Gallery, Videos, or Files. Confirm the title
   bar, moving pattern, tone, seeking, orientation, and full-screen playback.

Do not choose an online update, add an account, install a codec, or alter
pre-existing media. A direct user report or a readable video is sufficient
evidence. HDMI remains a separate hardware-dependent test.

