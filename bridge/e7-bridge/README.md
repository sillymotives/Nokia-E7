# E7 Bridge v0.3.0: Nokia Belle live process audit

**Status (2026-10-09):** The v0.3.0 application was compiled, installed, and
authenticated from a physical Nokia E7 to a Debian host over local Wi-Fi.
The operator exercised `ping`, `info`, `drives`, `ls`, `stat`, `ps`, `ps all`,
and `ps save`. A saved process census contained 172 names; an earlier live
listing contained 173. This is an operator-reported physical test, not a
reproducible hardware run in CI.

This release adds *read-only native Symbian process-name enumeration* plus a
read-only offline firmware boot-resource audit for the recovered Dumberdore
`SYM.RPKG`. There are **no new Symbian capabilities**, firmware writes,
process termination, autostart, or remote shells. Music and Wi-Fi configuration
are untouched.

## First: what the supplied firmware archive showed

An offline audit of an operator-provided Dumberdore archive parsed **13,356** `Z:`
entries and checked paths, sizes, and SHA-256 against a separate private inventory.
Generated per-file inventories and reports are intentionally excluded from this
public source release.

The following are embedded ASCII references in compiled startup `.rsc`
resources, not proof that each component starts on every boot:

- `Z:\PRIVATE\2000D75B\startup\0\uiservicescmdlist_ext.rsc` mentions
  `iaupdatedaemon.exe`.
- `...\noncriticalcmdlist_ext.rsc` mentions `fotacustcmds.dll`,
  `dmutilserver.exe`, `emailservermonitor.exe`, and other components.
- `...\criticalappscmdlist.rsc` mentions `sysap.exe`; other boot resources
  mention `sysmon.exe`, `ewsrv.exe` and `hwrmserver.exe`.

**Do not edit these resources or overwrite `Z:`.** We need runtime observations,
recovery planning, and actual dependency analysis before any change.

## 1. Simulated Linux tests

From this extracted project directory:

```sh
python3 -m unittest discover -s tests -v
bash -n build/*.sh
```

We verified **20 passing tests** and build-shell syntax in the authoring
environment. That includes crypto tests, pagination, JSON export, and a small
synthetic RPK2 fixture. This is not a substitute for a real Symbian compile.

For an offline mock bridge, run:

```sh
python3 host/e7_bridge.py serve --bind 127.0.0.1
# In a second terminal:
python3 tests/fake_phone.py --host 127.0.0.1
```

Reuse the pairing key stored under `~/.config/e7-bridge/pairing-key`.
**Do not run `init` again** or publish the key.

## 2. Compile and upgrade the Nokia app

On your Debian workstation, with PocketJS's `sr1-qt474-v1` historical Symbian
toolchain already working:

```sh
cd /path/to/Nokia-E7/bridge/e7-bridge
python3 -m unittest discover -s tests -v
./build/build-with-pocketjs.sh --pocketjs ~/StudioProjects/pocketjs
file dist/E7Bridge-v0.3.0.sis
```

The build isolates the toolchain, source, and signer as read-only Docker mounts
and disables network / USB access inside the container. Only `dist/` is
writable. A successful build emits `dist/E7Bridge-v0.3.0.sis`.

- Copy the **SIS file** to `E:/Installs` using your working transfer method.
- Install / upgrade **E7 Bridge** on the phone's **C: phone memory**.
- The SIS uses the **same UID (`0xE94B7001`) and signing volume** as v0.2.1,
  with an increased *package version* `0.3.0`. Keep that signing volume intact.
- Close the old agent before installing. If Symbian rejects the upgrade, stop
  and report its exact error; don't force the installer or modify ROMPatcher.
- Launch the app manually. It should show `v0.3.0`.

## 3. Connect to Debian and inspect processes

```sh
cd /path/to/Nokia-E7/bridge/e7-bridge
ip -4 addr show
python3 host/e7_bridge.py serve --bind YOUR_DEBIAN_LAN_IP
```

Replace the IP with your workstation's *current* Wi-Fi address. Keep the Nokia on the
same trusted network and connect from its UI with the **existing** pairing key.

In the terminal:

```text
ping
info
drives
ps           # first 20 process names
ps 20        # next 20
ps all       # all names, paginated
ps save      # save an inventory JSON on Debian only
exit
```

`ps save` writes a timestamped `0600` JSON file under:

`~/.local/share/e7-bridge/snapshots/`

This is a **point-in-time inventory of names**, not process IDs, resources,
dependencies, or persistence. App crashes or permission restrictions may leave
some processes invisible. A service absent from this list is not necessarily
safe to remove.

On the Nokia, exit the agent and verify normal music playback, Wi-Fi and
standby afterwards. Initial network and process commands passed on a physical E7;
post-upgrade long-term battery and standby effects remain unmeasured.

## 4. Optional: compare with the ROM archive on Debian

If you have a private Dumberdore `SYM.RPKG` on your workstation, run:

```sh
python3 tools/audit_boot.py \
  --archive '/path/to/SYM.RPKG' \
  --processes "$HOME/.local/share/e7-bridge/snapshots/e7-processes-EXACTNAME.json" \
  --out ./audit-output
```

Use the actual JSON filename produced by `ps save`. This writes local
`e7-boot-map.md` and `e7-boot-map.json`. Supplying a CSV from the prior inventory
via `--inventory /path/to/nokia_e7_zdrive_inventory.csv` also cross-checks
size and SHA-256 of **every archive entry**.

The tool only scans `Z:\PRIVATE\2000D75B\startup\0\*.rsc`. It extracts
printable binary references, *not* a full compiled-Symbian RSC parse. It never
modifies the archive and doesn't contact the phone. Do not publish generated maps without manual review; keep raw ROM-derived output private.
A sanitised live-summary is documented in the parent repository instead.

## Important security / safety boundaries

- The link has authenticated HMAC but **no encryption**. Process names and
  directory names can be observed by anyone capturing traffic on the Wi-Fi.
  Use only your trusted LAN and never expose TCP 46270 to the internet.
- Keep all keys private. The 16-hex-digit pairing key is only 64 random bits.
  It is a development pairing mechanism, not modern secure remote administration.
- No C: system/private folder enumeration is added. No remote file download,
  process control, root access, patch activation, or destructive commands.
- The **original signed firmware** and **writable C: state** are separate:
  a complete ROM or Z: backup is not a full backup of the live system.
- `Q_OS_SYMBIAN` native `TFindProcess` compiled and enumerated processes on a
  physical E7. This does not validate privilege elevation or process control.

## References

- PocketJS Symbian E7 build workflow: https://github.com/pocket-nexus/pocketjs/blob/main/docs/SYMBIAN_E7.md
- Nokia Symbian RSC reference: https://cortex.p.gen.nz/nokia/symbian/Nokia%20Symbian3%20Developer%27s%20Library%20v0.8/GUID-4406BDE0-8256-5F97-9FC5-BBFD11D9C4A3.html
- `TFindProcess` example (historical Symbian C++): https://stackoverflow.com/questions/6400573/is-it-possible-to-know-what-processes-are-running-on-a-symbian-phone-with-qt
