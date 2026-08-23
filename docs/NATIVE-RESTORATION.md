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
| Music player, playlists, FM radio | Retain / Repair | MTP transport formats are known; imported playback, library refresh, playlists/tags, and the FM headset-antenna path remain unproved. |
| Video player, HDMI/TV output, Web TV | Retain / Prune | Handset-captured local video playback works. Imported codec limits and physical output remain unproved; legacy Web TV catalogues are likely prune candidates. |
| Maps, GPS, favourites, drive/walk navigation | Repair / Bridge | Preserve native Maps if GPS and offline map data work. Online search, traffic, and account functions may need offline data or a bridge. |
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

## Active gate: imported media, radio, and physical output

Test conservative imported audio, image, and video fixtures through MTP, then
verify Music player library refresh, metadata, playlists, repeat/shuffle, and
background playback. Test FM radio with a wired 3.5 mm headset acting as the
antenna. Test HDMI/TV output only if an appropriate cable and display are
available.

This gate permits adding and removing clearly named test media in ordinary user
storage. It does not permit deleting pre-existing media, installing codecs,
accepting network services, or changing system files.

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
