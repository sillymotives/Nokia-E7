# Nokia E7 Wi-Fi Restoration Project

This repository documents the restoration of a US-model Nokia E7 as a useful,
Wi-Fi-only pocket computer. Cellular service is outside the project scope.

## Mission

Preserve what makes the E7 special—its aluminium body, AMOLED display,
hardware keyboard, camera, USB host support, and Symbian software ecosystem—
while recovering as much practical modern functionality as the hardware and
operating system can honestly support.

Likely workstreams include:

- reliable Wi-Fi and local-network services;
- file transfer and synchronisation;
- offline books, music, video, maps, notes, and reference tools;
- certificate and TLS investigation;
- compatible native applications and carefully chosen web bridges;
- terminal, scripting, SSH, Bluetooth, and USB-host possibilities;
- backup, recovery, and reproducible installation records;
- visual polish worthy of the hardware.

## Engineering rules

1. Inspect before changing.
2. Prefer reversible operations.
3. Separate user reports, host observations, and device-proven facts.
4. Preserve original firmware, user data, certificates, and recovery routes.
5. Hash downloaded and generated artifacts.
6. Do not place private captures or device identifiers in this public repo.
7. Cross a destructive boundary only after its exact target and recovery route
   have been proved.

## Current phase

Phase 0 is read-only discovery. Start with
[`scripts/e7-host-baseline.sh`](scripts/e7-host-baseline.sh) while the phone is
connected by USB. The script does not mount, unmount, install, unlock, flash, or
write to the E7.

Project status and evidence boundaries are recorded in
[`docs/PROJECT-STATE.md`](docs/PROJECT-STATE.md).
The host-proven USB personalities and functions are mapped in
[`docs/USB-INTERFACES.md`](docs/USB-INTERFACES.md).
The bounded AT command evidence is recorded in
[`docs/AT-CAPABILITIES.md`](docs/AT-CAPABILITIES.md).
The read-only mass-memory map and scoped write policy are recorded in
[`docs/MASS-MEMORY.md`](docs/MASS-MEMORY.md).
The proven MTP stores, transfer types, and mutation boundary are recorded in
[`docs/MTP.md`](docs/MTP.md).

The non-private serial-probe subset of the recovered 2026-08-05 Linux toolkit
is preserved under
[`archive/nokia-e7-toolkit-20260805/`](archive/nokia-e7-toolkit-20260805/).
Its trust boundaries are documented in
[`docs/TOOLKIT-AUDIT.md`](docs/TOOLKIT-AUDIT.md).
