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

## Active gate: establish trustworthy device time

The home-screen clock showed `27/07/2012`. Correct the date, time, and local
time zone manually, then prove that they survive a normal power cycle. Do not
judge TLS, mail, certificates, Maps networking, or signed content while the
device clock is wrong.

This gate authorises only the ordinary date, time, time-zone, and automatic-time
settings plus one normal shutdown/startup. It does not authorise reset, format,
firmware flashing, package installation, or component removal.

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
