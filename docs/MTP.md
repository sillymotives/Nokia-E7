# MTP interface

Captured: 2026-08-23

## Proven device identity

The guarded `mtp-detect` run completed successfully against the sole physical
MTP candidate on the host:

- USB identity `0421:0335`, recognised by libmtp as Nokia E7 in Ovi mode;
- manufacturer `Nokia`, model `E7-00`;
- device version `111.040.1511`;
- 64-bit MTP object sizes;
- friendly name `Nokia E7-00` and synchronisation partner `E7-00`;
- battery level 14% during the capture.

The 15-digit device identifier was redacted before the bundle was written.

## Proven storage boundary

| MTP store | Capacity | Free | Access |
| --- | ---: | ---: | --- |
| Mass memory | 16,068,378,624 bytes | 16,021,946,368 bytes | Read/write |
| Phone memory | 496,525,312 bytes | 0 bytes reported | Read-only |

This gives us a protocol-level boundary for future tests: ordinary payloads
may target the explicitly identified read/write Mass memory store. The Phone
memory store is not a write target.

No default MTP folders were assigned for music, playlists, pictures, video,
organiser data, albums, or text.

## Advertised transfer types

The device advertises MTP object metadata for folders, MP4, 3GP, AAC, MP3,
WMA, WAV, WMV, ASF, playlists, text, HTML, JPEG, BMP, GIF, PNG, abstract
albums, and legacy DOC/XLS/PPT documents.

This is evidence that the MTP responder knows those object categories. It is
not, by itself, proof that every codec, profile, document feature, or file in
those containers can be rendered by the installed phone applications.

## Mutation boundary

The capability catalogue also advertises deletion, upload, move, copy, device
reset, property changes, and vendor DRM/data-store operations. Their presence
is not authorisation to execute them.

The next gate permits only one reversible transaction on the proven Mass
memory store: create one unique root folder, upload one tiny text file,
retrieve and hash it, then delete only the exact file and folder object IDs
returned by their creation commands. Reset, format, bulk deletion, phone-memory
writes, and arbitrary property changes remain unauthorised.

## Verified round trip

The bounded transaction at `2026-08-23T19:50:01Z` completed successfully:

- the script selected only Mass memory storage ID `0x00020001`;
- it proved the unique test name absent, then created folder object `323`;
- it uploaded a 52-byte `KAI.TXT` as file object `16777331`;
- the retrieved file matched the host original byte-for-byte and at SHA-256
  `2f8263b8ffa7176279d8511381853dc190db32c82a61664ee3455e2375b60437`;
- it deleted only the returned file and folder object IDs;
- a final folder listing proved the unique test folder absent.

The transaction therefore proves working host-to-phone upload, phone-to-host
retrieval, byte integrity, exact-object deletion, and clean teardown over MTP.
