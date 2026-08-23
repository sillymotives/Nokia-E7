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
| Clock, alarms, calendar | Retain | High-value offline PIM; test alarms, recurring entries, time zone handling, and local backup/export. |
| Contacts | Retain / Bridge | Keep the native database; determine safe import/export and whether CardDAV must be translated through a host. |
| Notes, calculator, dictionary, ZIP manager | Retain | High-value offline tools; verify each application and its storage/export behaviour. |
| Quickoffice and PDF reader | Retain / Repair | MTP advertises legacy Office and PDF object types, but rendering and editing are unproved. Test representative local files. |
| File manager and device search | Retain | Verify access to ordinary mass-memory folders and useful indexed content. |
| Camera, Photos, image editor, video editor | Retain | Test capture, autofocus/flash, geotagging choices, editing, gallery indexing, and export. |
| Music player, playlists, recorder, FM radio | Retain / Repair | MTP transport formats are known; playback, recording, headset antenna requirements, library refresh, and tags remain unproved. |
| Video player, HDMI/TV output, Web TV | Retain / Prune | Keep local playback and physical output if they work; legacy Web TV catalogues are likely prune candidates. |
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

## Active gate: native local-content validation

Native content probe v1 has been built and independently verified on the host.
It contains hash-allowlisted PDF 1.3, Deflate ZIP, and plain-text fixtures. Its
guarded MTP script creates only `Mass memory:/KAI-NATIVE-V1`, retrieves all
three uploaded objects, compares them byte-for-byte, and leaves the verified
folder for native testing. Deploy it and test Files, ZIP manager, and Adobe
Reader according to [`NATIVE-CONTENT-V1.md`](NATIVE-CONTENT-V1.md).

Do not add an Office fixture merely to exercise the account-dependent
Microsoft Apps setup form. First identify a genuine local Office file handler;
then give it representative documents in a separate controlled probe.

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
