# Project state

Updated: 2026-08-23

## Scope

- Device: US-model Nokia E7.
- Intended role: Wi-Fi-only modernised pocket computer.
- Excluded: restoring cellular service.

## Fresh host evidence

The read-only capture at `2026-08-23T19:06:16Z` proved:

- USB identity `0421:0333`, reported as Nokia E7-00;
- USB 2.0 high-speed operation at 480 Mbit/s;
- one Mass Storage interface using class/subclass/protocol `08/06/50` and the
  Linux `usb-storage` driver;
- one removable, hot-pluggable Nokia `S60` disk at `/dev/sdb`, approximately
  15 GiB, with a single unmounted VFAT partition at `/dev/sdb1`;
- the kernel did not mark the disk read-only, although the capture itself made
  no device write;
- no `ttyACM`, `ttyUSB`, MTP, or GVFS phone interface in Mass storage mode.

The raw capture remains private because it contains host and device identifiers.
Version 1 of the capture script incompletely redacted the USB serial in two
secondary inventories. Version 2 corrected those fields but missed serial text
embedded in a tty `DEVLINKS` value. Version 3 applies a global 15-digit
identifier redaction to udev output. Both affected captures remain private.

The read-only Nokia Suite capture at `2026-08-23T19:14:49Z` additionally
proved:

- Suite-mode USB identity `0421:0335`, still reported as Nokia E7-00;
- one 18-interface USB composite device operating at 480 Mbit/s;
- `/dev/ttyACM0`, interface `01`, bound to `cdc_acm` and proven by udev as
  Nokia vendor `0421`, model `0335`;
- `/dev/ttyACM1`, interface `03`, with the same Nokia ownership proof;
- `usbpn0`, backed by the `cdc_phonet` function and currently unmanaged by
  NetworkManager;
- an Imaging/PTP interface marked by udev as MTP-capable, although no host MTP
  utility is currently installed;
- no mass-storage block device in Nokia Suite mode.

The allowlisted identity probe at `2026-08-23T19:21:20Z` freshly proved:

- interface `01` (`/dev/ttyACM0` during that enumeration) is the responsive
  standard AT information channel;
- manufacturer `Nokia`, model `Nokia E7-00`, RM variant `RM-626`;
- firmware `111.040.1511`, dated `2012-07-28`;
- interface `03` (`/dev/ttyACM1` during that enumeration) returned no response
  to `AT`, `ATI`, `AT+CGMI`, `AT+CGMM`, or `AT+CGMR`;
- ModemManager was active, but the complete interface-01 exchange returned
  clean `OK` responses.

The fixed capability probe at `2026-08-23T19:25:58Z` proved:

- `+CFUN: 0`: the cellular modem is in minimum-functionality mode;
- `+CBC: 1,14`: the battery is connected, the handset is externally powered,
  and 14% capacity was reported;
- cellular signal was unknown/unavailable and SIM, registration, and operator
  queries returned errors;
- the AT character set is UTF-8;
- SMS PDU and text syntaxes are implemented, but the exposed message-storage
  lists are empty;
- AT phonebook storage/read commands are not exposed;
- keypad emulation and Nokia backlight control are implemented, with backlight
  state `2` reported;
- the command catalogue exposes a much larger cellular and manufacturer test
  surface which remains unauthorised.

The guarded mass-memory census at `2026-08-23T19:34:24Z` proved:

- `/dev/sdb1` mounted with `ro,nosuid,nodev,noexec` and unmounted successfully;
- the 15 GiB VFAT filesystem uses only about 18 MiB;
- 321 directories, 120 files, and no symbolic links;
- Symbian `Private`, `sys`, and `cities` roots are present;
- no top-level `resource` tree and no SIS/SISX installers are present;
- media consists primarily of nine JPEGs plus factory-era maps/gallery/index
  metadata;
- the ordinary `Installs`, `Games`, `Music`, `Sounds`, and `Videos` payload
  areas are essentially empty.

The user explicitly confirms that none of the current mass-memory contents
require preservation. A retrieved or newly created image is therefore not a
prerequisite for bounded writes to ordinary payload folders on that partition.
This does not authorise formatting, repartitioning, or manual mutation of
Symbian-managed `Private` or `sys` trees.

The guarded MTP device-information probe at `2026-08-23T19:42:41Z` proved:

- libmtp recognises the Suite-mode interface as Nokia E7 in Ovi mode;
- the MTP identity agrees with the AT evidence: E7-00 firmware
  `111.040.1511`;
- Mass memory is exposed as a 16,068,378,624-byte read/write store with
  16,021,946,368 bytes free;
- Phone memory is separately exposed as a 496,525,312-byte read-only store;
- the responder uses 64-bit object sizes and reports battery level 14%;
- it advertises object metadata for common audio, video, image, text, HTML,
  playlist, and legacy Office formats;
- no default media or document folders are assigned.

The advertised format list is a transfer/object capability catalogue, not
proof that every codec or document feature renders on the phone. The responder
also advertises destructive operations; none were executed by this probe.

The bounded MTP transaction at `2026-08-23T19:50:01Z` then proved:

- explicit selection of the Mass memory store;
- creation of one uniquely named root folder and one 52-byte text object;
- successful retrieval with a byte-for-byte and SHA-256 match;
- deletion of only the exact file and folder object IDs returned at creation;
- no test-folder residue after cleanup.

MTP is therefore a verified bidirectional payload and retrieval path, not just
an advertised interface.

The local Wi-Fi/browser probe at `2026-08-23T20:03:28Z` proved:

- the E7 can reach a same-subnet host over plain HTTP by Wi-Fi;
- its user agent identifies Symbian/3, Series60/5.3, E7-00 firmware
  `111.040.1511`, and AppleWebKit/535.1;
- its reported screen is 640×360 with a 640×284 page viewport at DPR 1;
- CSS, JavaScript, GIF, favicon, and same-origin XHR resources loaded;
- XHR returned status 200;
- touch, canvas, local storage, application cache, WebSocket, geolocation, and
  HTML audio/video interfaces are present;
- Web Workers are absent;
- the HTTP `Accept` catalogue includes JAR/JAD, Nokia widget, OMA, HTML/XML,
  and OPML content types.

Presence of a browser interface or accepted content type is not proof of full
standards conformance, codec support, permission success, or installability.

## Reported working state

The following is inherited from earlier hands-on work and is not yet backed by
a fresh capture in this repository:

- the phone boots and can be operated;
- Wi-Fi has connected successfully;
- power-saving mode was disabled during earlier testing;
- USB mass-storage mode has worked;
- several earlier interaction probes passed;
- one earlier probe produced a visible brightness change or flash.

These facts are useful starting evidence, not permission to assume the current
state is identical.

## Unknowns to resolve

- exact product code and full Symbian build beyond the proven RM-626 firmware;
- lock, developer-certificate, and software-installation state;
- internal system-drive and removable-media layout beyond the proven 15 GiB
  mass-memory partition;
- additional USB personalities beyond the proven Mass storage and Nokia Suite
  modes;
- installed applications, patches, certificates, and user data worth keeping;
- viable backup and recovery routes;
- current browser/TLS limits and local-network capabilities.

The restoration target is the E7's native Symbian experience. The working
Field Deck is retained only as a reversible MTP/browser test fixture; it is not
a proposed replacement shell. The handset-specific retain/repair/bridge/prune
map and its evidence requirements are maintained in
[`NATIVE-RESTORATION.md`](NATIVE-RESTORATION.md).

## Historical toolkit evidence

An earlier toolkit supplied on 2026-08-23 identifies the tested phone as
RM-626 running firmware `111.040.1511`. Its preservation receipt records an
original mass-memory image of exactly `16,076,767,232` bytes with SHA-256:

`b5dd4b7e07afec8e0648ad40dfef37ef78a4e7b37d05382e5a4818728a071dfa`

The user confirms that this preservation image is stored on the Acer, not on
the current `niggacentre` host. Its present integrity has therefore not been
freshly verified in this project. That does not block read-only interface
enumeration, but the image must be retrieved and verified—or a new preservation
image made—before any destructive phone operation is considered.

## Active gate

Capture a read-only visual census of the handset's main menu, every application
folder, full installed-application list, home-screen widgets, and complete
device/software information. Do not expose personal content. This census will
replace family-level assumptions with an exact installed inventory before any
native application repair or reversible menu pruning begins.




## Evidence policy

Raw captures may contain serial numbers, filesystem UUIDs, paths, SSIDs, or
personal filenames. Keep them out of the public repository until reviewed and
sanitised. Commit conclusions, hashes, and redacted evidence instead.
