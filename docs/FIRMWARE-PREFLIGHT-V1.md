# Firmware preflight v1

Prepared: 2026-08-24

## Purpose

The project is now permitted to investigate custom firmware. This does not
make an unverified flash acceptable. The first firmware gate inventories the
exact handset build, stock firmware payloads, preservation images, Nokia
service tools, and available recovery hosts without modifying the phone.

The handset identity already proven through allowlisted AT information queries
is:

- Nokia E7-00;
- hardware family `RM-626`;
- Nokia Belle Refresh `111.040.1511`;
- build date `2012-07-28`.

The exact product/variant code remains unproven. It cannot be inferred merely
from `RM-626` or from the installed release number.

## Why recovery comes first

The no-SIM General/RF-on experiment produced a partial system deadlock. On the
timed follow-up the phone entered General mode, the AT endpoint stopped
responding, automatic `CFUN=0` rollback could not be delivered, and a hard
reset was required. This is enough evidence to close runtime General-mode
forcing as an operating strategy.

Firmware work can cross a much larger failure boundary. Before any ROFS or
core image is changed, the project must prove:

1. an exact matching stock firmware set;
2. the handset product/variant code;
3. a host toolchain that recognises the phone in normal and dead-USB modes;
4. a documented stock recovery procedure;
5. verified preservation material stored away from the working host;
6. a first patch that is narrow, reviewable, and reversible by reflashing the
   original image.

## Intended firmware architecture

The first custom image will retain Nokia's boot chain, kernel, hardware
adaptation, drivers, camera pipeline, graphics, power management, USB, WLAN,
Bluetooth, and GNSS components. Cellular-facing applications and dead service
surfaces can be hidden, disabled, replaced, or eventually stubbed, but core
telephony/profile dependencies are not deleted blindly.

The initial functional target is an Offline-first policy repair. Camera calls
the Location Trail service for geotagging, and the available Symbian source
contains an Offline path that clears cellular network fields while retaining
GPS position handling. The installed Belle image therefore deserves a narrow
Location Trail/LBS/profile-policy investigation before any broad component
removal.

## Private probe

The host scanner is distributed privately as
`nokia-e7-firmware-preflight-v1.zip`; it is deliberately not stored in this
public repository because its generated report inventories private host paths.
Run its `e7-firmware-preflight-v1.sh` from host storage. With no options it
searches the user's common data locations plus conventional Wine and system
software locations. Additional hosts or backup roots can be targeted with
repeatable `--root PATH` options. `--skip-phone` disables the allowlisted AT
identity query.

The script:

- reads Nokia USB identity and, when possible, repeats only `AT`, `ATI`,
  `AT+CGMI`, `AT+CGMM`, and `AT+CGMR`;
- inventories host firmware inspection, Windows compatibility, virtualisation,
  and USB tools;
- searches without extracting for `RM-626`, `111.040.1511`, FPSX/VPL/DCP
  payloads, Nokia service utilities, and likely preservation images;
- hashes candidates up to 2 GiB and records larger candidates without hashing;
- emits a private report bundle and checksum.

It does not mount, extract, unlock, reset, flash, or write phone storage.

## Gate

No preflight result by itself authorises flashing. The next firmware step is
chosen only after the private report proves which stock payload and recovery
resources actually exist.
