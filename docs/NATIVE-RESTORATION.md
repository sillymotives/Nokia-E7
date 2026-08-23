# Native restoration matrix

Updated: 2026-08-23

## Goal

Restore the Nokia E7 as a coherent Symbian Belle device. Prefer the phone's
built-in applications, hardware controls, and native data stores. Use a host or
LAN bridge only where a native client remains valuable but its original remote
service has disappeared.

The self-contained Field Deck at `Mass memory:/KAI/INDEX.HTM` is a successful
MTP and browser test fixture. It is not the replacement launcher or the product
direction.

## Status vocabulary

| Status | Meaning |
| --- | --- |
| Unknown | Documented for the E7 family, but not yet observed on this handset. |
| Proven | The feature or transport has passed a focused test on this handset. |
| Retain | Useful as-is after its data, settings, and limits are understood. |
| Repair | A native feature needs configuration, compatible content, certificates, or a native package. |
| Bridge | Keep the native UI, with a controlled LAN/host service replacing a dead dependency. |
| Prune | Hide, disable, or remove a dead or irrelevant surface after rollback is proved. |

`Prune` does not initially mean deleting ROM components. The first pruning
pass is reversible menu organisation, shortcut/widget removal, account cleanup,
and disabling unwanted automatic connections.

## Current matrix

The Nokia E7 user guide documents the subsystem families below. Presence in the
guide is not proof of the installed state or behaviour of firmware
`111.040.1511`; the census must confirm each item on the phone.

| Native area | Candidate treatment | Current evidence and restoration question |
| --- | --- | --- |
| Home screen, profiles, themes, notification light, device search | Retain | Core native shell; confirm current widgets, shortcuts, profiles, and dead service prompts. |
| Clock, alarms, calendar | Retain | Correct time survives reboot; alarm firing/cleanup and calendar entry persistence/cleanup work. Recurrence and export remain later tests. |
| Contacts | Retain / Bridge | Keep the native database; determine safe import/export and whether CardDAV must be translated through a host. |
| Notes, calculator, dictionary | Retain | Note save/edit/delete, prescribed arithmetic, and local English lookup all work. Export and extra language packs remain optional. |
| ZIP manager | Retain | A controlled local Deflate archive works; archive creation remains unproved. |
| PDF reader | Retain | A conservative local PDF 1.3 fixture renders correctly; establish complexity and performance limits later. |
| Local Office handler | Unknown / Repair | MTP advertises legacy Office object types, but Microsoft Apps exposes an account setup surface rather than a local browser. Identify a genuine handler before testing documents. |
| File manager and device search | Retain | Files browses Mass memory and opens the controlled plain-text fixture; indexed search and local mutations remain unproved. |
| Camera, Photos, image editor, video editor | Retain | Still and video capture, Gallery display, native playback, photo editing, and video editing all work by direct user observation. Autofocus/flash modes, geotagging choices, and export remain later detail tests. |
| Recorder | Retain | Native audio recording and playback work by direct user observation. Format/export limits remain later tests. |
| FM radio | Retain | The user confirms that native FM reception works. Station memory and RDS are optional later detail tests. |
| Music player and playlists | Retain | Imported MP3 playback and the exercised player controls work. A track-aware MTP object exposed Alpha and a native MTP playlist registered successfully. Beta did not appear through that particular ingest probe, but this non-blocking content-transfer quirk does not diminish the useful native player. |
| Video player and Web TV | Retain / Prune | Handset-captured and imported H.264/AAC video playback work. The player does not autorotate even though system rotation works elsewhere; treat that as a local player limitation. Legacy Web TV catalogues are likely prune candidates. |
| HDMI/TV output | Blocked: test hardware | No suitable mini-HDMI cable is available. There is no failure evidence; defer physical verification rather than inferring a pass. |
| Maps, GPS, favourites, drive/walk navigation | Repair / Bridge | Maps stops at a missing-street-maps screen and exits when it is dismissed. Offline mode blocks Camera location, so the integrated receiver cannot yet be isolated. Test runtime full functionality first; offline map data remains a separate repair. |
| Wi-Fi and browser | Retain / Bridge | Local HTTP, CSS, JavaScript, XHR, and storage are proven. Use the browser as infrastructure only where no meaningful native client exists. |
| Mail | Repair / Bridge | Test direct IMAP/SMTP/TLS first; if protocol or certificate limits block it, translate on the trusted LAN while retaining native Mail. |
| Bluetooth and Phone switch | Retain | Verify pairing, object push, audio profiles, keyboard/tether roles, and device-to-device transfer. |
| USB modes and USB host | Retain | Mass storage, Nokia Suite composite mode, and MTP are proven. USB host/accessory behaviour remains untested. |
| VPN and remote drives | Repair / Bridge | Confirm the clients are present before investigating compatible endpoints or LAN translation. |
| Synchronisation and device backup | Repair / Bridge | Establish contacts/calendar/notes backup and restore before invasive work. Prefer documented native stores and reversible transforms. |
| Application manager and software update | Retain / Repair | Inventory packages, signatures, install locations, and certificate state. Never uninstall or modify firmware during census. |
| Internet calling | Repair / Bridge | Potentially meaningful on Wi-Fi; confirm SIP/VoIP components and accounts before choosing a bridge. |
| Telephone, SMS/MMS, voicemail, cellular widgets | Prune | Cellular service is out of scope. Preserve emergency/recovery behaviour; remove distractions only through reversible UI changes first. |
| Nokia/Ovi account, Store, Ovi Music, Social, obsolete support links | Prune / Bridge selectively | Assume nothing from age alone. Test only if a native workflow remains valuable; otherwise hide dead entry points and prevent connection churn. |

## Completed gate: native UI census

The menu, settings families, installed-package list, installation policy,
widget catalogue, four home-screen panels, and complete software-information
screen were captured on 2026-08-23. Sanitised findings are recorded in
[`NATIVE-CENSUS.md`](NATIVE-CENSUS.md).

## Completed gate: establish trustworthy device time

The date, time, and Cardiff time zone were corrected and survived a normal
power cycle on 2026-08-23. The phone no longer depends on its stale 2012 clock
for date-sensitive testing.

## Completed gate: core offline launch pass

Clock, Calendar, Notes, Calculator, Dictionary, Files, ZIP, Adobe Reader,
Microsoft Apps, and the on-device User guide all reached their native UI without
a crash. Files and ZIP browsed Mass memory. The User guide exposed its offline
topic index. Microsoft Apps exposed an account-dependent setup form and is not
evidence of local Office document handling. Detailed results and unproved
transactions are recorded in
[`CORE-OFFLINE-SMOKE.md`](CORE-OFFLINE-SMOKE.md).

## Completed gate: native local-content validation v1

Native content probe v1 has been built and independently verified on the host.
It contains hash-allowlisted PDF 1.3, Deflate ZIP, and plain-text fixtures. Its
guarded MTP script creates only `Mass memory:/KAI-NATIVE-V1`, retrieves all
three uploaded objects, compares them byte-for-byte, and leaves the verified
folder for native testing. Deploy it and test Files, ZIP manager, and Adobe
Reader according to [`NATIVE-CONTENT-V1.md`](NATIVE-CONTENT-V1.md).

Do not add an Office fixture merely to exercise the account-dependent
Microsoft Apps setup form. First identify a genuine local Office file handler;
then give it representative documents in a separate controlled probe.

The user completed the on-device check on 2026-08-23 and reports that the text,
PDF, and ZIP fixtures all work correctly. Files, Adobe Reader, and ZIP manager
are now retain candidates backed by local-content use, not merely launch tests.

## Completed gate: core local transactions

The sequence in [`CORE-OFFLINE-SMOKE.md`](CORE-OFFLINE-SMOKE.md) comprised alarm
firing and cleanup, calendar entry persistence and cleanup, note
persistence/edit/delete, calculator arithmetic, dictionary lookup, and User
guide search. Every action was local, disposable, and independent of retired
services.

The user completed this sequence on 2026-08-23 and reported that all six areas
work. Clock, Calendar, Notes, Calculator, Dictionary, and User guide therefore
have transaction-level or functional local evidence rather than launch-only
evidence.

## Completed gate: handset-originated capture and media

The native camera, Gallery, photo editor, video capture/player/editor, and voice
recorder were exercised with handset-originated media. The user reports that
all capture, viewing, editing, recording, and playback paths work.

This establishes the handset's own codecs and media-database paths without
introducing external encoding variables.

## Partial gate: radio and physical output

The user reports that FM radio works. HDMI/TV output is untested because no
suitable mini-HDMI cable is available. This is a test-hardware blocker, not a
device failure and not evidence of a pass.

## Completed gate: imported media compatibility v1

Imported native-media probe v1 passed its image, audio, and video decoding
tests. Music player found and played both MP3s, and the useful player controls
exercised during the test worked. The imported H.264/AAC video also played.

Two ingestion details were partial: Music player displayed filenames instead
of the surviving embedded tags, and the copied M3U opened as a file but did not
become a native playlist. The video player's playback surface also did not
autorotate, while system rotation works elsewhere. Full observations and the
bounded interpretation are in [`NATIVE-MEDIA-V1.md`](NATIVE-MEDIA-V1.md).

## Partial gate: track-aware music ingestion v2

Music player exposed Alpha and registered the native playlist containing that
visible track. Together with the successful imported-media playback and player
controls, this is sufficient to classify Music player as **Retain**. Beta's
absence remains a non-blocking transfer/library-ingestion observation. The
generated host report was not supplied, so no stronger transport-layer claim
is made. Full interpretation is in [`NATIVE-MUSIC-V2.md`](NATIVE-MUSIC-V2.md).

## Partial gate: integrated GPS and offline Maps v1

The handset exposed the expected positioning-method families, and Integrated
GPS was isolated from Assisted GPS, Bluetooth GPS, Wi-Fi/Network, and Network
based methods. Maps then stopped at its missing-street-maps screen and exited
when that screen was dismissed. No separate GPS Data, Location, or Landmarks
front end was found. Camera states that location is unavailable in Offline
mode. Detailed observations are in [`GPS-MAPS-V1.md`](GPS-MAPS-V1.md).

The mass-memory census found only Nokia Maps catalogue/icon scaffolding, not a
substantial offline map payload. The missing tiles and the Offline-profile
location block remain separate problems.

## Completed gate: guarded General-mode runtime trial v1

The first authorised system-state write proved CFUN 0 to CFUN 1, absent SIM
context, denied rather than active registration, an empty operator, and a
responsive AT path. Nokia's source confirms that this directly activates
General profile ID 0 and the normal RF-on system state.

The user then opened Belle's top status/settings drawer. The handset froze and
required a hard reset; reboot restored its normal no-SIM Offline state. The
script had already completed and sent no reset or persistent-profile command.
Full evidence and interpretation are in
[`GENERAL-MODE-TRIAL-V1.md`](GENERAL-MODE-TRIAL-V1.md).

## Active gate: firmware recovery preflight

The timed Camera-location follow-up also deadlocked, stopped answering AT
commands, and required a hard reset after its automatic rollback became
unreachable. Runtime no-SIM General/RF-on forcing is closed. Follow
[`GENERAL-MODE-LOCATION-PULSE-V2.md`](GENERAL-MODE-LOCATION-PULSE-V2.md).

The current gate inventories the exact stock firmware, product/variant code,
preservation images, Nokia service tools, and dead-USB recovery path before any
custom image is built. The intended first patch is a narrow Offline-safe
location-policy repair. Follow
[`FIRMWARE-PREFLIGHT-V1.md`](FIRMWARE-PREFLIGHT-V1.md).

This gate does not authorise package installation, uninstall, account creation,
network-dependent setup, reset, format, firmware flashing, or system-file
mutation.

## First test order after census

1. Clock, calendar, notes, calculator, dictionary, ZIP, Quickoffice, and PDF.
2. Camera, gallery/editors, recorder, music, FM radio, video, and HDMI.
3. GPS and offline Maps.
4. Bluetooth, USB host, file manager, and native synchronisation/backup.
5. Mail, Internet calling, VPN, remote drives, and other Wi-Fi clients.
6. Reversible home-screen and menu pruning of confirmed dead surfaces.

## Documentation basis

- Nokia, *Nokia E7-00 User Guide*:
  <https://nds1.webapps.microsoft.com/phones/files/guides/Nokia_E7-00_UG_en.pdf>
- Nokia, *Nokia E7-00 Nokia Belle User Guide*:
  <https://nds1.webapps.microsoft.com/phones/files/guides/Nokia_E7-00_Nokia_Belle_UG_en.pdf>

The guides establish intended feature families. Fresh handset observations and
focused tests determine the project status.
