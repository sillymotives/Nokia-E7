# E7 Bridge v0.4.0: Black Box review gate

Prepared: 2026-10-09
Status: **physical E7 acceptance passed on 2026-10-10**; 27 host tests passed and the native application compiled/installed on Sanctuary + Nokia E7. Post-exit music, Wi-Fi and standby were operator-confirmed.

## Scope

Add read-only Symbian RAM values (in bytes) and three battery-related raw
HWRM property values to the manually started E7 Bridge app. Add bounded,
foreground process/telemetry capture, timestamped comparisons, and host-only
files to the Debian controller.

No firmware image editing, startup-service modifications, privileged profile
changes, network encryption claims, process termination, or new Symbian
capability is proposed.

## Test evidence (authoring container)

- `python3 -m unittest discover -s tests -v`: **27 tests passed**.
- `bash -n build/*.sh`: no shell syntax errors.
- Crypto/protocol regressions from v0.3.0 remain in place.
- `record` validates sample count, interval and total window, and flushes each
  record to a local private JSONL file. If the operator disconnects or interrupts,
  completed samples are retained.
- The native program's new API calls cannot be runtime verified without
  compiling and running on the physical E7.

## Physical acceptance gate

1. Build signed `E7Bridge-v0.4.0.sis` in Sanctuary's pinned Symbian toolchain.
2. Install as upgrade using the **same signer and UID**, never a firmware flash.
3. Connect over trusted Wi-Fi and confirm `ping` and `info`.
4. Run `metrics` and record which readings are available. **Do not infer charge
   percentage from the raw integer level**.
5. Run `capture`, `record 3 10`, `diff`, and inspect only the local files.
6. Manually exit, verify Wi-Fi and music-player function and check standby.
7. Do not disable any process until separate dependency and recovery analysis.

## Limitations

- Battery P&S reads can return unavailable due to permissions or firmware.
- `TFindProcess` is enumerated afresh for each 20-name page and is not atomic.
  Apparent differences may be sampling artefacts or process instance churn.
- Samples are timestamped on Debian, not at the exact moment the kernel values
  were taken.
- Wi-Fi traffic is authenticated but not encrypted. Reports contain process
  names that may disclose installed applications; they stay private.
- An old `ps save` snapshot can be compared with a new `capture` file, but
  `diff` only compares the two newest matching file names by UTC timestamp.

## Physical acceptance result (2026-10-10)

- Operator compiled and installed E7 Bridge v0.4.0 using Sanctuary's pinned Symbian toolchain. The UI and `info` identified v0.4.0.
- HMAC pairing succeeded; `ping` replied `PONG`.
- `metrics` returned 257,228,800 bytes RAM total, 143,917,056 bytes free, and accessible raw battery/charging status property values. Battery readings have **not** been translated to charge percentages or interpreted as charging state.
- `ps save` and `capture` each recorded 173 entries. `diff` found zero additions/deletions.
- `record 3 10` successfully wrote 3 samples with 173 entries each; the recorder reported no change between its first and last process census.
- `exit` completed. Operator separately confirmed native music playback, Wi-Fi and normal standby all still function correctly.
- This is a short observation session, not a battery-drain, startup-order, or service-removal dependency test. Process enumeration remains non-atomic.

**Gate:** Physical validation complete; merge of this read-only development tool is permitted. Firmware writes, service pruning, startup changes and public release of raw handset captures remain out of scope.
