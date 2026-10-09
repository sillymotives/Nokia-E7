# E7 Bridge and firmware-startup reconnaissance

Updated: 2026-10-09

## Scope and evidence

This note describes a **separately authorised native application test**, not a
firmware-flash or system-file modification gate. The handset is a Nokia E7-00
(RM-626) running Nokia Belle Refresh `111.040.1511`, used as a Wi-Fi-only
pocket computer. The native music player remains a **Retain** subsystem.

Evidence categories are kept distinct:

- **Operator-reported device observation:** The independent E7-Bridge v0.2.1
  Qt application was compiled, installed and authenticated over local Wi-Fi to
  a Debian controller; `ping`, `info`, `drives`, `ls` and `stat` worked. The
  v0.3.0 upgrade was later installed and answered `ps`, `ps all` and `ps save`.
- **Host-side validation:** v0.3.0 source passed 20 Python unit tests and
  build-shell syntax checks in the authoring environment. This is not a
  hardware test or an independent rebuild of the owner's signed SIS.
- **Saved runtime observation:** One process snapshot enumerated **172 names**.
  An earlier interactive listing reported **173 names**. These are process
  names returned by Symbian `TFindProcess`, not PIDs, memory measurements,
  startup ordering, or a service dependency graph.
- **Offline archive observation:** A separately supplied Dumberdore `Z:`
  archive parsed as 13,356 entries; paths, sizes, and individual SHA-256 values
  matched a private inventory. That validates internal consistency, not the
  completeness of writable `C:` state or a flash-ready recovery image.

Public data intentionally omits pairing keys, live IP addresses, identifiers
unique to the handset, private filesystem captures, raw snapshots, and firmware
images. Keep these in an access-controlled local evidence store.

## Startup resource clues versus live evidence

The offline scan extracted printable executable and DLL references from
compiled resources under `Z:\PRIVATE\2000D75B\startup\0\`. It **did not fully
parse or execute** System State Manager command lists; a string is not proof
of unconditional boot-time execution.

| Candidate | Firmware clue | Observed at runtime | Interpretation |
| --- | --- | --- | --- |
| `iaupdatedaemon.exe` | Referenced in `uiservicescmdlist_ext.rsc` | Not listed; `iaupdatebgchecker` **was** listed | Different executables; investigate their relationship before modifying either |
| `dmutilserver.exe` | Referenced in `noncriticalcmdlist_ext.rsc` | Listed | Device-management candidate for dependency research |
| `emailservermonitor.exe` | Referenced in `noncriticalcmdlist_ext.rsc` | Listed | Investigate after evaluating native Mail/notifications |
| `fotacustcmds.dll` | Referenced in `noncriticalcmdlist_ext.rsc` | Not a process (DLL) | May be invoked by startup commands; process census cannot prove its use |
| `sysap.exe`, `cfserver.exe` | Referenced in `criticalappscmdlist.rsc` | Both listed | **Preserve**; core system/UI infrastructure |
| `xmppservice.exe`, `weatherpublisher.exe` | No claim established by the selected startup scan | Both listed | Investigate usage and lifecycle; do not assume startup origin |

The saved snapshot and earlier interactive listing differed by one visible
entry, `!SensorServer[1020507e]0001`. This single comparison is insufficient
to say why the entry disappeared, whether it runs on demand, or whether
sampling itself changed system activity.

## Native E7 Bridge v0.3.0

Source: [`../bridge/e7-bridge/`](../bridge/e7-bridge/).

The manually launched native Qt 4.7.4 agent makes an **outbound** TCP connection
to the user-operated Debian terminal. Its supported commands are `ping`,
`info`, `drives`, `ls`, `stat`, and paged process enumeration (`ps`, `ps all`,
`ps save`). `ps save` writes a timestamped JSON file **on Debian only**.

The application does **not** provide remote shell access, file writes,
process termination, ROMPatcher controls, startup modifications, or firmware
flashing. Listing is confined to permitted storage roots and excludes protected
system/private directories. Installation to phone memory (`C:`) was limited
to this user-space application, independently of the earlier firmware-preflight
prohibition on system changes.

Authentication is a mutual HMAC-SHA256 challenge using a manually entered
64-bit pairing key. **The transport is not encrypted** and is appropriate
only on a trusted LAN. Do not port-forward its TCP listener (port `46270`).
The pairing key, certificate private keys, signed SIS packages and private
captures are not committed here.

## Next controlled experiment

1. Preserve private raw process snapshots and the exact signed SIS; retain
   the existing verified ROM/Dumberdore backups without treating them as a
   complete backup of writable `C:`.
2. Restart the E7 normally. Open the agent manually and capture `ps save`
   immediately, after a few minutes of idle time, then following a short
   controlled music-player and Wi-Fi test. Record each test condition.
3. Compare process-name sets **and repeated sampling** before labeling any
   component persistent, conditional or idle-only. Avoid interpreting a
   changed process count as a performance improvement.
4. Research dependencies and a reversible recovery path before attempting to
   disable obsolete update, device-management or messaging services.
5. No firmware image modifications, service killing, patch toggles, remote
   writes or no-SIM General/RF-on experiments are authorised by this note.

**Current status:** successful read-only instrumentation; no service has been
cleared for removal and no custom firmware has been authorised for flashing.
