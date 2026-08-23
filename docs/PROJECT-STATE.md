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
secondary inventories; version 2 corrects that defect.

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

- exact product code, RM variant, firmware version, and Symbian build;
- lock, developer-certificate, and software-installation state;
- internal mass-memory and removable-media layout;
- available USB personalities and host-visible interfaces;
- installed applications, patches, certificates, and user data worth keeping;
- viable backup and recovery routes;
- current browser/TLS limits and local-network capabilities.

## Historical toolkit evidence

An earlier toolkit supplied on 2026-08-23 identifies the tested phone as
RM-626 running firmware `111.040.1511`. Its preservation receipt records an
original mass-memory image of exactly `16,076,767,232` bytes with SHA-256:

`b5dd4b7e07afec8e0648ad40dfef37ef78a4e7b37d05382e5a4818728a071dfa`

That receipt proves what the earlier run reported, but the image's present
location and current integrity must be verified before it is treated as an
available recovery artifact.

## Active gate

Switch the phone from Mass storage to Nokia Suite mode and run version 2 of the
read-only host baseline. No AT command, flashing, formatting, firmware
download, certificate replacement, system-file mutation, or installation is
authorised by this gate.


## Evidence policy

Raw captures may contain serial numbers, filesystem UUIDs, paths, SSIDs, or
personal filenames. Keep them out of the public repository until reviewed and
sanitised. Commit conclusions, hashes, and redacted evidence instead.
