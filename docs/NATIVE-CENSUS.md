# Native handset census

Captured: 2026-08-23

## Evidence boundary

Three user-supplied videos provide a readable visual census of the menu,
settings families, widget catalogue, installed-package list, home screens, and
device-manager information. The raw videos remain private. No unique handset
identifier or private screen capture is stored in this public repository.

## Device software

- Release: Nokia Belle Refresh.
- Software version: `111.040.1511`, dated `2012-07-28`.
- Custom version: `111.040.1511.230.01`, dated `2012-09-11`.
- Language set: `111.040.1511.01.01`.
- Model/type: E7-00 / RM-626.
- Browser version: 8.3.
- Flash version: 4.0.
- Java version: 2.3.
- The device-manager screen reports `Latest update: Not updated`.
- The product code was captured privately for future firmware matching.

The native home-screen clock showed `27/07/2012` while this census was being
made on 2026-08-23. The handset's system date is therefore stale. This is a
likely blocker for certificate validation, TLS, mail, signed content, and other
date-sensitive services; it must be corrected before diagnosing those systems.

## Main menu

The menu is one vertically scrolling grid. No existing application folder was
visible. The following launchers were observed from top to bottom:

| | | |
| --- | --- | --- |
| Contacts | Messaging | Web |
| Gallery | Calendar | Mail |
| Store | Videos | Music player |
| Search | Maps | Settings |
| Log | User guide | Zip |
| Weather | Microsoft Apps | Msg. reader |
| Nokia Music | Map Loader | Public Transport |
| Guides | Drive | Communicator |
| Video editor | Photo editor | Adobe Reader |
| Social | Nat Geo | My Nokia |
| Nokia Sync | About | Calculator |
| Camera | Clock | Files |
| FM radio | Dictionary | Notes |
| Recorder | SW update | |

This is a strong native base. Offline PIM, documents, maps, media, capture,
editing, file management, synchronisation, and utility surfaces are present.
Store, Weather, Nokia Music, Public Transport, Social, Nat Geo, My Nokia, and
other service-dependent launchers are candidates for focused testing and later
pruning or bridging.

## Settings surface

The top-level Settings screen contains Profiles, Themes, Phone, Installations,
Calling, Connectivity, and Application settings.

Observed Phone settings include time and date, speech, language, display,
voice commands, sensors, touch input, accessories, phone management, and
notification lights.

Observed Connectivity settings include Bluetooth, USB, connection settings,
Connection manager, Mobile data tracker, Data transfer, Video sharing, and
Administrative settings.

Observed per-application settings include default applications, Messaging,
Videos, Log, Positioning, Map Apps, Voice recorder, Camera, Calendar, Mail, and
Product improvement.

## Package manager

The `Already installed` list is short and contains:

- Adobe Reader LE, 4 MB;
- JoikuSpot Light Engine, 60 kB;
- one 16 kB entry displayed with an ambiguous `lkm`/`Ikm` label;
- Microsoft Communicator, 3 MB;
- Microsoft Shared, 7 MB;
- Nat Geo, 1 MB;
- Nokia Notifications Support (label truncated), 1 kB;
- PhotoEditor AIW plugin (label truncated), 45 kB;
- PhotoEditor memory plugin (label truncated), 1 kB;
- Security Engine, 324 kB;
- Social, 3 MB;
- VideoEditor AIW plugin (label truncated), 45 kB;
- VideoEditor OOM plugin (label truncated), 1 kB.

The `To be installed` queue is empty.

Installation settings currently report:

- Software installation: `All`;
- Online certificate check: `Off`;
- Default web address: `None`.

These settings are favourable for restoration work, but they do not by
themselves prove that an arbitrary unsigned or capability-bearing SIS package
will install. A disposable, known-safe package must test the actual boundary
later.

## Home screens and widgets

Four home-screen panels were shown. They include a relatively bare panel, a
blue service/widget panel, a clock-and-calendar panel, and a mail-oriented
panel. The full widget chooser was also scrolled. It includes useful local
controls alongside many network, news, social, weather, and cellular-era
widgets.

The first pruning pass can therefore be entirely reversible: remove obsolete
widgets and shortcuts, retain the native panels, and reorganise the menu. No
ROM component removal is needed to achieve a clean Wi-Fi-only interface.

## Census conclusion

The handset is not an empty shell. It has a broad Belle Refresh application
set, a permissive-looking installation policy, no staged installers, four
working home screens, and a small installed-package overlay. Native-first
restoration is practical.

The immediate gate is to correct the system date, time, and local time zone,
then verify that they survive a normal power cycle. Only after that should TLS,
mail, certificates, Maps networking, or software-install behaviour be judged.
