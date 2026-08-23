# Nokia E7 Wi-Fi Restoration Project

This repository documents the restoration of a US-model Nokia E7 as a useful,
Wi-Fi-only pocket computer. Cellular service is outside the project scope.

## Mission

Preserve what makes the E7 special—its aluminium body, AMOLED display,
hardware keyboard, camera, USB host support, and Symbian software ecosystem—
while recovering as much practical modern functionality as the hardware and
operating system can honestly support.

This is a native-first restoration. The goal is to make the E7's built-in
applications and hardware useful again, not to replace Symbian with a browser
dashboard. Host services and local web pages are support infrastructure: they
may bridge a dead remote service, deliver content, or test a capability, but
they are not the device's primary interface.

Likely workstreams include:

- reliable Wi-Fi and local-network services;
- file transfer and synchronisation;
- offline books, music, video, maps, notes, and reference tools;
- certificate and TLS investigation;
- compatible native applications and carefully chosen web bridges;
- terminal, scripting, SSH, Bluetooth, and USB-host possibilities;
- backup, recovery, and reproducible installation records;
- visual polish worthy of the hardware.

Every native subsystem is tracked as **retain**, **repair**, **bridge**, or
**prune** in
[`docs/NATIVE-RESTORATION.md`](docs/NATIVE-RESTORATION.md). Unverified items
remain explicitly unknown until observed on this handset.
The handset-specific visual inventory is recorded in
[`docs/NATIVE-CENSUS.md`](docs/NATIVE-CENSUS.md).

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

The safe host paths are established: USB identity, AT interrogation, guarded
mass-memory access, reversible MTP transfer, and local Wi-Fi HTTP have all been
proved. A read-only visual census of the native menu, installed applications,
widgets, home screens, installation policy, and device information is also
complete. The stale system date, time, and Cardiff time zone have been repaired
and survived a normal power cycle. The controlled PDF/ZIP/text probe has passed
on the handset, establishing Files, Adobe Reader, and ZIP manager as useful
native local-content paths. The core alarm, calendar, notes, calculator,
dictionary, and offline User guide transactions also pass. Native capture and
media also pass end-to-end: stills, Gallery, photo editing, video
capture/playback/editing, and voice recording/playback. Imported media, Music
player behaviour, FM radio, and physical output are the current restoration
gate.

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
The proven Wi-Fi/browser path and web-runtime capabilities are recorded in
[`docs/WIFI-BROWSER.md`](docs/WIFI-BROWSER.md).
The guarded local-content deployment and on-device pass conditions are recorded
in [`docs/NATIVE-CONTENT-V1.md`](docs/NATIVE-CONTENT-V1.md).

The non-private serial-probe subset of the recovered 2026-08-05 Linux toolkit
is preserved under
[`archive/nokia-e7-toolkit-20260805/`](archive/nokia-e7-toolkit-20260805/).
Its trust boundaries are documented in
[`docs/TOOLKIT-AUDIT.md`](docs/TOOLKIT-AUDIT.md).
