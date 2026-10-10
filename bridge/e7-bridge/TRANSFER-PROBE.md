# E7 Bridge v0.5.0: first cable-free file transfer

Prepared: 2026-10-10. **Experimental source candidate. Symbian SDK build and handset acceptance pending.**

## Goal

Prove that Sanctuary can receive bytes from the physically running Nokia E7 over Wi-Fi, *without* writing phone files and without opening unrestricted file access. This is a constrained first step toward real wireless transfer, sync and modern service bridges.

## Exactly what this version can transfer

- **Only** the controlled, previously deployed static Field Deck file at `E:/KAI/INDEX.HTM`.
- The Nokia recognises only the no-path `FILEINFO` and `FILECHUNK OFFSET` wire commands. A remote request **cannot supply a path**. `FILECHUNK` offsets are nonnegative 1024-byte-aligned integers.
- A file must exist as an ordinary, non-symlinked file whose canonical path matches the fixed path, and must be **at most 65,536 bytes**.
- The phone opens files `QIODevice::ReadOnly`. It sends file length and a SHA-256 computed from the source file, then base64-encodes fixed 1024-byte binary chunks inside the existing bounded response envelope.
- The only Debian terminal command is `pull probe`; no arbitrary remote path or general-purpose GET/PUT command is exposed.
- Sanctuary accepts only the declared byte count, validates every chunk length, and computes an independent SHA-256 over the reconstructed bytes. It stores the result in owner-only `~/.local/share/e7-bridge/received/e7-fielddeck-TIMESTAMP.htm` **only after validation**. On errors the temporary `.part` file is removed, and nothing is changed on the phone. An existing result is never overwritten.

**Security limit:** The protocol still uses HMAC-based session authentication over *unencrypted* TCP. The hash is communicated over the same unauthenticated data stream, so it detects accidental damage/inconsistent captures but **does not establish authenticity against an active network attacker**. Use this only on a trusted LAN with the known non-sensitive Field Deck; do not transfer secrets or personal files. The existing 16-hex development key is not strong enough for public-internet use. A confidential, mutually authenticated transport is a separate milestone before generalising file access.

## Build and physical test

1. On Sanctuary, run `python3 -m unittest discover -s tests -v` and `bash -n build/*.sh` from the unpacked source directory. The authoring-container suite contains **54** tests at this point.
2. Run `./build/build-with-pocketjs.sh --pocketjs ~/StudioProjects/pocketjs` with the established Qt 4.7.4 toolchain and **same signing identity as v0.4.1**. Confirm `dist/E7Bridge-v0.5.0.sis` is produced. Stop and diagnose compiler/installer errors; do not change ROMPatcher or firmware.
3. In the working v0.4.1 bridge, optionally run `ls E:/KAI` to confirm `INDEX.HTM` is still on the phone. If it is missing, **do not** substitute an arbitrary path or copy anything to system directories; re-deploy the existing controlled Field Deck by its documented, guarded method or defer the physical transfer test.
4. Close v0.4.1, install signed v0.5.0 as an in-place upgrade on **C: phone memory**, and reconnect manually. Remembered pairing should still work. Confirm `info` says `E7 Bridge v0.5.0`.
5. On Sanctuary, launch the **matching v0.5 host controller**, using the current LAN IP: `python3 host/e7_bridge.py serve --bind YOUR_CURRENT_SANCTUARY_IP`.
6. In the authenticated `e7>` prompt, enter `ping`, `info`, `pull probe`, then `exit`. The controller should print a local path, byte count and SHA-256, and leave a validated `.htm` in the private receive directory.
7. To independently compare against the source in the repository, calculate the hash of the original `payloads/field-deck/INDEX.HTM` with `sha256sum`, and compare it to the newly received file. This independent check is strongest if the exact Git-tracked fixture was actually deployed on the phone, unchanged. An earlier custom or modified Field Deck can legitimately have a different hash; treat that as a provenance question, not proof of a wire failure.
8. Close E7 Bridge, verify native music, Wi-Fi and standby, and test normal save/load of the remembered host and key.
9. Try `pull E:/private` in the host terminal and confirm it is **rejected locally**. No device-side read request should occur.

The first meaningful acceptance is: **one deliberately public file, on a running Nokia E7, successfully transferred and reconstructed on Sanctuary with size/hash equality, zero phone mutations, and working legacy apps afterwards.**

## Rollback

Retain the already physically accepted `E7Bridge-v0.4.1.sis`. If compilation, authentication, file read or the native apps regress, stop the v0.5 trial and install v0.4.1 using the same application UID and signing identity. An in-place upgrade should preserve pairing settings, but that must be verified rather than assumed.

## Out of scope

- General-purpose remote file browser or file download from `C:` / arbitrary `E:` paths.
- Uploading or deleting files on the E7, modifying startup/ROM, running a shell, or enabling autostart.
- Sending credentials, medical data, or any private content over the v0.5 plaintext channel.
- Claiming real encryption or enterprise-grade authentication from a per-file SHA-256 transmitted over that same channel.
