# Project state

Updated: 2026-08-23

## Scope

- Device: US-model Nokia E7.
- Intended role: Wi-Fi-only modernised pocket computer.
- Excluded: restoring cellular service.

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

## Active gate

Run the read-only host baseline with the phone connected. No flashing,
formatting, firmware download, certificate replacement, system-file mutation,
or installation is authorised by this gate.

## Evidence policy

Raw captures may contain serial numbers, filesystem UUIDs, paths, SSIDs, or
personal filenames. Keep them out of the public repository until reviewed and
sanitised. Commit conclusions, hashes, and redacted evidence instead.

