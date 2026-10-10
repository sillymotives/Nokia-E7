# Nokia E7: read-only update, messaging, analytics and ROM service triage

**Status:** experimental host-side research tool. No Symbian rebuild, SIS installation,
ROMPatcher controls, service stops, package removal, or files written on the E7.
Works offline with two ordinary v0.9 inventory captures. The `--archive` argument
is optional and reads an existing Dumberdore `SYM.RPKG` without extraction.

## Why this exists

The first physical v0.9 baseline captured **407 base SIS package entries and
168 process instances**. A second capture with the native music player running
reported **407 packages and 170 processes**. The new process names were `mpx.exe`
and `!SensorServer`; free RAM changed from **148,140,032 to 146,718,720 bytes**.
Both 2026-10-10 captures were sequential rather than atomic. We can say that
certain process names were observed, but cannot infer their owning SIS packages,
per-process RAM use, network destinations, or whether a startup resource actually
launched a process. The goal is to correlate evidence without guessing.

Priorities for investigation, **not** disablement:

1. `iaupdatebgchecker` was observed running. The ROM archive contains
   `Z:\sys\bin\iaupdatedaemon.exe`, and `uiservicescmdlist_ext.rsc` contains a
   string referring to that executable. These are *distinct* executables.
2. `NokiaAnalyticsCollector` is installed, and the ROM includes
   `analyticscollector.dll`. A DLL is not a standalone process; missing a
   same-named EXE does not establish inactivity or data transmission.
3. `emailservermonitor.exe`, `ozemailserver.exe`, `ozmonitor.exe`,
   `fsmailserver.exe`, `neasstartup.exe`, `neasserver.exe`, `ombengine.exe`
   and `xmppservice.exe` were observed. Their actual package ownership and
   modern-day usefulness are unverified. Preserve core messaging.
4. Norton/Symantec was historically used as a *quarantine-restore carrier*
   to enable RomPatcher+ and the Dumberdore ROM capture. Its processes
   `symc_AV.exe` and `symc_LM.exe` still run. **Do not casually remove or
   disable those components until the working patching path and writable-C:
   recovery are independently protected.**
5. Keep MPX music playback, the native UI, Wi-Fi, message store, software
   installer, package registry and Symbian service managers unchanged.

## Run offline on Sanctuary

From the matching `e7-bridge-v0.9.0` source directory:

```bash
python3 -m unittest discover -s tests -q

python3 tools/service_triage.py \
  --idle "$HOME/.local/share/e7-bridge/inventory/e7-inventory-20261010T184748135850Z-idle.json" \
  --active "$HOME/.local/share/e7-bridge/inventory/e7-inventory-20261010T185854253509Z-music-playing.json" \
  --archive "/path/to/your/SYM.RPKG"
```

Omit `--archive` if the Dumberdore archive isn't present on Sanctuary.
Change the inventory paths if your filenames differ. This command never
contacts the handset. It generates owner-only `.json` and `.md` files in
`~/.local/share/e7-bridge/service-audits/` (directory `0700`, files `0600`).
The parser refuses symlinked or malformed inventory/archive files and does not
overwrite earlier reports.

`SYM.RPKG` is a historical snapshot of the merged read-only `Z:` tree. Its
contents were previously independently validated by the boot-audit utility.
The service triage rechecks record bounds and duplicate paths but **does not
re-hash each archive payload**, so it must not be described as a cryptographic
revalidation. Nor is the archive a bootable recovery image or a full `C:` backup.

## What the report means

**Exact package UID** means the installed SIS registry was queried at the
snapshot time. A **running process** means one process-name instance existed
when sampled. **ROM Z: file** means the archive contained that filename.
**Startup string reference** means the bytecode `.rsc` contained a printable
name, not that a particular startup branch executed. Grouping entries on one
page is for analyst convenience; it is **not** an ownership link.

No candidate is marked removable. Even a package that no longer appears in
some phone menu can still supply DLLs, ECom plugins, install machinery, or
other dependencies. A file absent from the read-only ROM may exist on `C:` or
another writable drive.

## Next experiments (all reversible observations)

Capture another v0.9 baseline after a normal reboot and a later idle period.
Then, separately test Wi-Fi activity while keeping the bridge connected, and
opening/closing native Mail, recording what changes each time. Turning Wi-Fi
off would disconnect our present Wi-Fi-only bridge and prevent collection. Do not claim network traffic from process
names alone. Before any deeper OS action, we need a proper package-to-file/SID
registry query, decoded SSM startup conditions, preserved patcher inputs, a
verified writable-state backup, and a recovery procedure.

Never commit raw handset inventory, pairing keys, dumps or local execution
journals to a public repository. This tool and its unit tests use static
identifiers and **synthetic** fixtures only.
