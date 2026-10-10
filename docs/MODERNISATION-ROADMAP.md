# Nokia E7: native-first modernisation roadmap

Updated: 2026-10-10

## Desired end state

A trustworthy **Wi-Fi-only pocket computer** that still feels like a Nokia E7: real sliding keyboard, Symbian Belle UI, native camera/media, useful offline tools, and working bridges to modern network services. No cellular service is requested. It is not realistic to treat the E7 as a drop-in current Android/iOS replacement; modernisation means selecting concrete useful workflows and demonstrating them on this handset.

The existing `Retain / Repair / Bridge / Prune` matrix in `NATIVE-RESTORATION.md` remains authoritative. We protect native music playback, camera, Wi-Fi, timekeeping, the existing offline tools and the phone's boot chain. Dead cloud service panels are candidates for reversible **hiding/bridging**, not for blind removal of dependencies.

## Engineering gates and order

| Priority | Capability | Handset-visible acceptance condition | Safety prerequisite |
| --- | --- | --- | --- |
| P0: ongoing | Recovery and measurable baseline | Verified, separately stored backups; early-post-boot/settled process and RAM snapshots; documented stock image/recovery path before flashing | Keep `Z:` archive distinct from writable `C:` state, and avoid unreviewed startup edits |
| P1: first real modern feature | Trustworthy cable-free file transfer | From E7, transfer a bounded test file to Debian and verify size + SHA-256; compare with existing MTP path | Restrict sources, avoid private files, test disconnect/retry, preserve existing E7 contents |
| P1 | LAN bridge security | Pairing and confidentiality model suitable for transferring non-public user data, with device-side constraints documented | Existing v0.4 HMAC transport authenticates but does **not encrypt**; keep current channel on trusted LAN and use synthetic test files initially |
| P2 | Modern host-service gateway | One specific native E7 workflow can access a current service via a narrow, modern-TLS-capable host adapter | No storing external account secrets on public GitHub or exposing an unauthenticated LAN proxy |
| P2 | Contacts/calendar/notes continuity | Round-trip a disposable local fixture through a modern exchange format without destroying existing data | Reversible import/export; backup and comparison first |
| P3 | Maps and positioning | Offline map content visibly works on the native E7; location behaviour tested separately | Never repeat the failed runtime no-SIM General/RF-on forcing; avoid replacing core location libraries blindly |
| P3 | Native email / messaging | A narrowly scoped modern service works through a native client or a reviewed bridge | Constrain authentication and transport, verify privacy and data handling |
| P4 | Selective UI/boot cleanup | Remove or hide dead surfaces **reversibly**, with no regression in music, Wi-Fi, camera, USB or standby | Multiple stage captures, dependency evidence and a proved rollback route |
| P5 | Firmware image research | A minimal, auditable patch with a verified original-image restore route | Existing product/variant, stock firmware, dead-USB, independent preservation and recovery gates must pass |

## What has already been demonstrated

- Native media, camera, several offline productivity apps, Wi-Fi and browser-local content are usable, as described in `PROJECT-STATE.md` and `NATIVE-RESTORATION.md`.
- E7 Bridge v0.4.0 compiled and installed on physical Nokia E7 (2026-10-10). Authenticated commands, read-only RAM/power telemetry, process snapshots, `diff` and `record` passed. Native music, Wi-Fi and standby still worked after exit.
- The 173-process census and approximately 245 MiB reported RAM total describe this E7 session, not a guaranteed platform baseline or proof of wasted services.
- A private `Z:` archive and a firmware-resource audit exist. A recovered `Z:` filesystem is **not** proof of full stock flash recoverability or a backup of writable phone memory.

## Next physical test

Use the existing v0.4 application for an early post-boot capture, a settled capture ~3 minutes later, and optionally a normal-use capture. The read-only offline comparison utility is `bridge/e7-bridge/tools/stage_compare.py` and the protocol is `bridge/e7-bridge/BOOT-STAGES.md`.

If the baseline is usable, the next functional engineering slice should be **verified E7-to-Debian transfer of a deliberately non-private test file**, with byte/hash comparison and explicit size/path limits. Do not start by adding general-purpose remote writes or changing firmware.

## Non-goals and open questions

- No revival of out-of-scope cellular connectivity.
- No assumption that legacy Symbian TLS, current websites, application signing or cloud APIs will work unmodified.
- No claim that a service is safe to disable simply because it has an obsolete-looking name.
- Future bridge encryption design, storage of service credentials, package compatibility and exact recovery procedure all require independent investigation.
