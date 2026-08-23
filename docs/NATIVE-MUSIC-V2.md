# Track-aware native-music probe v2

Prepared: 2026-08-23

## Why v2 exists

Imported-media v1 proved that both MP3 byte streams decode and play. It also
isolated two library-ingestion limitations: Music player displayed filenames
instead of the embedded tags, and a copied M3U remained a file rather than a
native playlist.

That result is consistent with the generic libmtp transfer used by v1.
`mtp-sendfile` creates an ordinary file object and does not populate title,
artist, album, track-number, or duration properties. v2 changes only that
variable:

- the exact same two MP3 files are sent with `mtp-sendtr`;
- their metadata is supplied as MTP track properties;
- libmtp creates/updates one uniquely named native album object;
- `mtp-newplaylist` creates one native playlist object referencing the two
  returned track IDs in order;
- `mtp-tracks`, `mtp-albums`, and `mtp-playlists` must prove the object model
  before the handset result is interpreted.

The E7 advertises writable audio metadata properties and native audio-album and
playlist formats. This probe tests that advertised model; it does not install a
codec, alter the player, or assume that embedded ID3 parsing and MTP metadata
ingestion are the same path.

## Fixed objects

| Object | Expected MTP values |
| --- | --- |
| `KAI-TRACK-01.MP3` | title `KAI Tone Alpha`; artist/album artist `KAI Test`; album `E7 Native Music V2`; genre `Test`; track 1; duration 8000 ms |
| `KAI-TRACK-02.MP3` | title `KAI Tone Beta`; artist/album artist `KAI Test`; album `E7 Native Music V2`; genre `Test`; track 2; duration 8000 ms |
| `KAI Playlist V2` | native playlist object containing track 1 then track 2 |

The persistent filesystem target is `Mass memory:/KAI-MUSIC-V2`. The playlist
object is parented to that folder. libmtp may represent the album as a separate
MTP object rather than as an ordinary file visible in Files.

## Host deployment

Put the phone in Nokia Suite USB mode, close graphical programs using it, and
run from host storage:

```bash
./scripts/e7-deploy-native-music-v2.sh
```

The script refuses a pre-existing target folder, album name, or playlist name.
It verifies both source hashes, creates one folder, sends only the two fixed
tracks, retrieves each returned track object and compares it byte-for-byte,
verifies the explicit MTP metadata, creates the native playlist, and verifies
its name, parent, membership, and order. It deletes and overwrites nothing.

Successful objects deliberately remain on the phone. A partial run may also
leave the clearly named folder, tracks, album, or playlist; the report lists
every proven object ID. Do not rerun blindly after a partial result.

## On-device decision

1. Open Music player and use its refresh/rescan command if available.
2. Find artist `KAI Test` or album `E7 Native Music V2`.
3. Confirm the player shows `KAI Tone Alpha` and `KAI Tone Beta`, not the two
   filenames.
4. Confirm album grouping and order 1 then 2.
5. Open playlists and confirm `KAI Playlist V2` exists with Alpha then Beta.
6. Play the playlist through the transition from Alpha to Beta.

Interpretation:

- Correct metadata and playlist: retain the stock Music player and use
  track-aware MTP ingestion for the restored library.
- Correct metadata but no playlist: retain playback/library grouping and
  investigate the player's playlist database independently.
- Host-visible MTP metadata but filenames/no playlist in Music player: the
  handset accepts the object model but the stock player does not consume it;
  classify that layer as a native-client limitation rather than a tag or codec
  failure.
- Host verification failure: stop at the transport/object layer; do not draw a
  Music-player conclusion.

## Implementation basis

- libmtp `sendfile.c`: generic file-object construction
- libmtp `sendtr.c`: track properties and album creation/update
- libmtp `newplaylist.c`: native playlist-object creation
- libmtp `tracks.c`, `albums.c`, and `playlists.c`: read-back inspection
