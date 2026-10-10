# E7 Bridge v0.6.0: authenticated write-enabled staging

A manually launched Qt 4.7.4 native Symbian Belle agent on the Nokia E7,
with a Python 3 Debian controller. **v0.6.0 is a SOURCE CANDIDATE** pending
native compilation and on-phone write tests. v0.4.1 connection persistence is
physically accepted. The v0.5 read-only Field Deck transfer was operator-tested
and delivered a readable HTML artifact to Sanctuary. This v0.6 branch depends
on v0.5 and does not bypass its review gate.

## New in v0.6: authenticated administrative writes

The E7 accepts **session-bound HMAC-authenticated, monotonically sequenced
admin commands**, with authenticated replies. The existing E7 Connect button
is the session boundary: **no extra approval pop-up per file**. The wire remains
unencrypted, so use the existing trusted LAN (payload contents are visible on it).

- `push LOCALFILE` stages a file up to **8 MiB** at `E:/KAI/INBOX/<filename>`.
- `push LOCALFILE installs` stages a `.sis`/`.sisx` package at `E:/Installs/`.
- The host checks input size and SHA-256 before transfer. The phone streams
  binary-safe 2048-byte chunks to a same-directory temporary file, verifies
  exact size/hash, and publishes only on a successful final rename.
- Interrupted uploads are discarded on disconnect. **Existing target filenames
  are never overwritten.** There is no arbitrary destination, delete, process
  killing, installer bypass, remote code execution, or service modification.
- Added **WriteUserData**, a basic Symbian capability; E:/ user storage writes
  are possible without AllFiles/TCB. Signing/install on real handset must be
  tested separately; neither capability flags nor a SIS imply actual root.

This is the start of a broader **owner-authorised administration programme**.
See [ADMINISTRATION.md](ADMINISTRATION.md) for the privilege map and later
possible device-admin capabilities, including app deployment and system-area
modifications only with a tested recovery path.

## First wireless transfer: `pull probe`

The Nokia still exposes exactly **one already deployed synthetic file**,
`E:/KAI/INDEX.HTM`, via two new authenticated-session read-only wire commands:
`FILEINFO` and `FILECHUNK OFFSET`. It will not read arbitrary paths. The fixed
source must be an ordinary non-symlinked file, canonically matching the expected
path, and be no larger than **64 KiB**. The controller downloads it into a
private host folder and only publishes the `.htm` after checking the full
size and SHA-256. Interrupted or inconsistent transfers leave no result.

On Sanctuary, after building/installing the matching v0.6 SIS and connecting:

```text
ping
info
pull probe
push ./bridge-test.txt
push ./E7Test-0.6.0.sis installs
exit
```

The `.sis` above is just a *sample local filename*, not a provided package.
For the first test, push a harmless non-private text file and verify it using
Symbian File Manager. Do not attempt to self-upgrade the currently running bridge
through the E7 installer in this first deployment experiment.


The Wi-Fi protocol **is not encrypted**. The SHA-256 supplied by the phone is
sent over the same unencrypted connection, so this verifies transfer
consistency, not protection against an active network attacker. Only the
known non-private test fixture is allowed. See
[`TRANSFER-PROBE.md`](TRANSFER-PROBE.md) for exact limitations and acceptance.

## Existing, physically accepted capabilities

v0.4.1 restored the last successfully authenticated IPv4 host and masked
pairing key on relaunch, without auto-connect. Remember and Forget controls
work on the handset. It also preserved the v0.4 read-only RAM/power metrics,
process capture/diff and bounded foreground diagnostic recording. Native
music, Wi-Fi and standby remained functional after physical acceptance.

## What is new

| Command on Debian | Behaviour |
| --- | --- |
| `metrics` | On-demand RAM totals/free bytes and **raw** power-state integers, or `unavailable` where the device denies/doesn't implement a read. No percentage is inferred. |
| `capture` | One host-timestamped, non-atomic RAM/power/process snapshot saved on **Debian only**. |
| `diff` | Compare the two newest saved `ps save`/`capture` process inventories, reporting appeared/disappeared entries. Does not contact the phone. |
| `record` | 3 foreground snapshots 10 seconds apart, written incrementally to a private Debian `.jsonl` file. |
| `record N S` | Bounded recording: 2–12 samples, 5–120 seconds between samples, up to 600 seconds between first/last samples. |

All existing `ping`, `info`, `drives`, `ls`, `stat`, `ps`, `ps all`, `ps save`
and `exit` commands remain available. The Nokia does not listen on TCP and
cannot be remotely started. Connection is initiated manually in its app UI.

The process list comes from `TFindProcess` in pages. It is **not an atomic
snapshot** or a service dependency graph. A process missing from one reading
may simply have exited or been started after its page was enumerated. Raw
battery-level/status values come from Symbian's HWRM publish/subscribe
properties, and must not be interpreted as 0–100 percent. Query failures are
preserved as `unavailable`, not silently replaced with plausible-looking data.

## Safety and trust model

- Same application UID `0xE94B7001`, same development signing identity, version
  raised to `0.6.0`. Original Nokia firmware is *not modified*.
- `NetworkServices ReadUserData WriteUserData` capabilities (one added basic
  user-data write capability); no AllFiles/TCB, process control or remote shell.
- Native `HAL::Get` and `RProperty::Get` stay read-only; local file writes only through the signed E: staging protocol.
- Host stores snapshots under `~/.local/share/e7-bridge/snapshots/` with new
  files created as mode `0600`. It does not upload telemetry to third parties.
- HMAC challenge authentication remains, but **the Wi-Fi link is not encrypted**.
  Use only on a trusted LAN. The short manually typed key is development-only.
- A ROM/`Z:` filesystem dump does not back up writable `C:` state. Do not
  remove services or edit startup resources based on these observations alone.
- Keep signing credentials, pairing keys, raw captures, host addresses,
  filesystem listings and serial/device identifiers **out of public Git**.

## Validate the Linux host and simulator

```sh
python3 -m unittest discover -s tests -v
bash -n build/*.sh
```

All **65** host-side Python tests passed in the authoring container for v0.6.0. The suite covers HMAC, framing, bounded `ps` pagination, metrics validation,
local report permissions, process differences, recording limits, interruptions,
binary transfer limits/checksums/failure cleanup, and Symbian source assertions and admin write boundaries. It does not replace Symbian compilation or
on-device measurements.

To run the simulator, use an **existing** pairing key in
`~/.config/e7-bridge/pairing-key`; do not run `init` if you already paired:

```sh
python3 host/e7_bridge.py serve --bind 127.0.0.1
# In another terminal:
python3 tests/fake_phone.py --host 127.0.0.1
```

## Build and install on Sanctuary (Debian)

Prerequisite: the pinned PocketJS Symbian Belle compiler has already passed
`bun tools/symbian.ts doctor` and built its probe on Sanctuary. The bridge
build does **not** modify the PocketJS checkout.

```sh
cd ~/StudioProjects/Nokia-E7/bridge/e7-bridge  # or wherever cloned
python3 -m unittest discover -s tests -v
./build/build-with-pocketjs.sh --pocketjs ~/StudioProjects/pocketjs
file dist/E7Bridge-v0.6.0.sis
sha256sum dist/E7Bridge-v0.6.0.sis
```

If the native compile or SIS packaging fails, **stop** and inspect the error.
Do not alter ROMPatcher or force an installation to bypass the failure.

If the build succeeds, copy the SIS to the Nokia's `E:/Installs` and use File
Manager to upgrade the installed E7 Bridge **on C: (phone memory)**. Retain the
existing PocketJS development signing volume so this has the same signer as
v0.4.1. Close the previous E7 Bridge before upgrading, and check that the new UI reports `v0.6.0`.

On Debian, substitute Sanctuary's **current** local IPv4 address:

```sh
python3 host/e7_bridge.py serve --bind YOUR_CURRENT_DEBIAN_IP
```

Manually start E7 Bridge on the E7 and connect with the same pairing key.
Use `help` for a complete list. Recommended first v0.6 physical acceptance:

```text
ping
info
pull probe
exit
```

Previous v0.4.1 read-only diagnostics (`metrics`, `ps save`, `capture`, `diff`, `record`) remain available.

`record` is a foreground operation; leave the phone's app visible and Wi-Fi
connected. If interrupted or disconnected, completed JSONL samples remain on
Debian. Do not misread `record 3 10` as continuous unattended monitoring.

Afterwards, manually exit E7 Bridge, check music playback and Wi-Fi, and
verify the Nokia returns to normal standby. Collect a cold-boot `ps save` only
if convenient; do **not** modify startup processes based on it yet.

## Developer layout

- `phone/main.cpp` — Qt 4.7.4 and Symbian native diagnostic/admin agent.
- `phone/sha256_compat.h` — SHA-256 HMAC compatible with Qt 4.7.4.
- `host/e7_bridge.py` — Python terminal, capture/diff/record commands.
- `tests/fake_phone.py` — synthetic reply source for safe host tests.
- `tests/` — auth, protocol, crypto, firmware parser, safety and Black Box tests.
- `build/` — isolated pinned PocketJS toolchain build and SIS packaging.
- `tools/audit_boot.py` — separate offline startup-resource inspection tool.

## Implementation references

- Symbian `HAL::Get(HALData::EMemoryRAM[Free])` and HAL library:
  https://flylib.com/books/en/2.338.1.119/1/
- Qt Mobility 1.2 Symbian HWRM power state property category `0x10205041`, keys 1–3:
  https://qt.developpez.com/doc/qtmobility-1.2/publ-subs/
- Symbian `RProperty::Get` permission checks (read-only):
  https://cortex.p.gen.nz/nokia/symbian/S60%203rd%20Edition%20C%2B%2B%20Developer%27s%20Library%20v1.1/GUID-35228542-8C95-4849-A73F-2B4F082F0C44/html/SDL_93/doc_source/reference/reference-cpp/E32_EKA2/RPropertyClass.html
- Historical Symbian Qt build workflow:
  https://github.com/pocket-nexus/pocketjs/blob/main/docs/SYMBIAN_E7.md

- `TRANSFER-PROBE.md` — fixed-file wireless transfer protocol, test and rollback gate.
