# Nokia E7: native-first modernisation roadmap

Updated: 2026-10-24

## Desired end state

A trustworthy **Wi-Fi-only pocket computer** that still feels like a Nokia E7: real sliding keyboard, Symbian Belle UI, native camera/media, useful offline tools, and working bridges to modern network services. No cellular service is requested. It is not realistic to treat the E7 as a drop-in current Android/iOS replacement; modernisation means selecting concrete useful workflows and demonstrating them on this handset.

The existing `Retain / Repair / Bridge / Prune` matrix in `NATIVE-RESTORATION.md` remains authoritative. We protect native music playback, camera, Wi-Fi, timekeeping, the existing offline tools and the phone's boot chain. Dead cloud service panels are candidates for reversible **hiding/bridging**, not for blind removal of dependencies.

## Engineering gates and order

| Priority | Capability | Handset-visible acceptance condition | Safety prerequisite |
| --- | --- | --- | --- |
| P0: ongoing | Recovery and measurable baseline | Verified, separately stored backups; early-post-boot/settled process and RAM snapshots; documented stock image/recovery path before flashing | Keep `Z:` archive distinct from writable `C:` state, and avoid unreviewed startup edits |
| P1: physically accepted | Trustworthy cable-free file transfer | Bounded synthetic E7-to-Debian transfer and checksums passed | Restrict sources, avoid private files, test disconnect/retry, preserve existing E7 contents |
| P1 | LAN bridge security | Pairing and confidentiality model suitable for transferring non-public user data, with device-side constraints documented | Existing v0.4 HMAC transport authenticates but does **not encrypt**; keep current channel on trusted LAN and use synthetic test files initially |
| P2: host candidate | Modern host-service gateway | E7 browser displays current public news delivered by a narrowly scoped HTTPS-fetching Sanctuary host gateway, including after screen lock | No account secrets, arbitrary forward proxy, public HTTP listener, or untested handset claims |
| P2 | Contacts/calendar/notes continuity | Round-trip a disposable local fixture through a modern exchange format without destroying existing data | Reversible import/export; backup and comparison first |
| P3 | Maps and positioning | Offline map content visibly works on the native E7; location behaviour tested separately | Never repeat the failed runtime no-SIM General/RF-on forcing; avoid replacing core location libraries blindly |
| P3 | Native email / messaging | A narrowly scoped modern service works through a native client or a reviewed bridge | Constrain authentication and transport, verify privacy and data handling |
| P4 | Selective UI/boot cleanup | Remove or hide dead surfaces **reversibly**, with no regression in music, Wi-Fi, camera, USB or standby | Multiple stage captures, dependency evidence and a proved rollback route |
| P5 | Firmware image research | A minimal, auditable patch with a verified original-image restore route | Existing product/variant, stock firmware, dead-USB, independent preservation and recovery gates must pass |

## What has already been demonstrated

- Native media, camera, several offline productivity apps, Wi-Fi and browser-local content are usable, as described in `PROJECT-STATE.md` and `NATIVE-RESTORATION.md`.
- E7 Bridge phone agent v0.8.0 and Sanctuary host controller v0.8.1 have passed their positive-path physical acceptance, including native SIS registry queries, bounded E:/ file transfer and verified host-side administrative write batches. Native music, Wi-Fi and standby were preserved during those checks. The HMAC-authenticated bridge is **not encrypted** and remains restricted to a trusted LAN.
- The 173-process census and approximately 245 MiB reported RAM total describe this E7 session, not a guaranteed platform baseline or proof of wasted services.
- A private `Z:` archive and a firmware-resource audit exist. A recovered `Z:` filesystem is **not** proof of full stock flash recoverability or a backup of writable phone memory.

## Next physical test

Use the existing v0.4 application for an early post-boot capture, a settled capture ~3 minutes later, and optionally a normal-use capture. The read-only offline comparison utility is `bridge/e7-bridge/tools/stage_compare.py` and the protocol is `bridge/e7-bridge/BOOT-STAGES.md`.

The bounded E7-to-Debian Field Deck transfer and E7 v0.8.0 / host v0.8.1 write-batch positive path have subsequently passed physical acceptance. The next service-facing milestone is **a practical modern HTTPS-to-E7 workflow**, initially a read-only BBC News RSS gateway hosted on Sanctuary and displayed in the stock E7 browser. The host candidate has offline tests but **has not yet passed on-device acceptance**. It uses fixed upstream feeds, not an arbitrary web proxy. Do not expose unencrypted local services to the public internet.


## WLAN power saving: provisional field observation (2026-10-24)

The E7 operator reports that disabling WLAN-specific power saving **appears to have stopped unexpected Wi-Fi dropouts**. This is a single user observation, not an independently verified root cause or a long-duration acceptance result. Nokia's stock WLAN implementation distinguishes the `WlanPowerMode` control from inactivity/connection-lifetime timeouts. The preserved Z: configuration includes a one-second WLAN last-session-closed timeout; we must not conflate ordinary idle disconnects with a UI Wi-Fi toggle actually moving to Off. A longer lock/unlock plus practical browser-reload test remains pending. See [WLAN-POWER-SAVING-OBSERVATION-2026-10-24.md](WLAN-POWER-SAVING-OBSERVATION-2026-10-24.md).

## Non-goals and open questions

- No revival of out-of-scope cellular connectivity.
- No assumption that legacy Symbian TLS, current websites, application signing or cloud APIs will work unmodified.
- No claim that a service is safe to disable simply because it has an obsolete-looking name.
- Future bridge encryption design, storage of service credentials, package compatibility and exact recovery procedure all require independent investigation.
