# E7 Bridge v0.9: private installed-software and process baseline

**Status:** host-only v0.9 pilot captured the physical Nokia E7 on 2026-10-10. The phone remains on its existing v0.8.0 agent, with no Symbian rebuild or reinstall. A later capture comparison reported zero changes. Native music, Wi-Fi, standby and remembered-pairing regression checks are still pending. No private raw registry is committed to GitHub.

## What it collects

- `INFO`, fetched from the connected E7 agent.
- Every base SIS registry entry from the existing `PKGS OFFSET` paginated API, up to 2,000 entries. Stores UID, native package name and installed version. Does **not** query SIS augmentations, package ownership or package files.
- Up to 2,000 currently running Symbian process names from the existing `PROCS OFFSET` paginated API. Duplicate process-instance names are retained.
- The existing five raw `METRICS` fields. Raw battery values are **not** percentages.
- UTC start and finish timestamps, noting the capture is **not atomic**.

The controller finishes every read and validates the complete response before creating a baseline file. An error halfway through collection does not save a partial snapshot.

## Sanctuary commands

Download/extract the `e7-bridge-v0.9.0` source ZIP and start:

```bash
cd ~/Downloads/e7-bridge-v0.9.0
python3 -m unittest discover -s tests -q
bash ./build/serve-on-sanctuary.sh
```

Connect from the **existing E7 Bridge v0.8.0** app as usual. At `e7>` enter each command on its own line:

```text
baseline capture idle
baseline capture music
baseline diff
```

`baseline capture LABEL` uses a simple alphanumeric/underscore/dash label (max 32 characters); it does not change the device. You can also run `baseline capture` without a label.

The controller prints two paths for each capture:

- `~/.local/share/e7-bridge/inventory/e7-inventory-TIMESTAMP-LABEL.json` contains the full raw package inventory, process list and metrics.
- The adjacent `.md` file contains counts and **review leads** based on historical product-name hints. It never recommends uninstalling a package.

After two captures, `baseline diff` writes an offline JSON and Markdown comparison to the same directory. It reports new/removed/changed package entries, started/stopped process-name instances and raw metric differences. You may also provide exact files:

```text
baseline compare /path/to/idle.json /path/to/music.json
baseline report /path/to/idle.json
```

Offline from a normal Sanctuary terminal, without a connected Nokia:

```bash
python3 host/e7_bridge.py baseline report /path/to/idle.json
python3 host/e7_bridge.py baseline compare /path/to/idle.json /path/to/music.json
```

The inventory directory is owner-only (`0700`) and new reports use mode `0600` with no overwrites. The tool refuses a symlinked/widely readable output directory and oversized/malformed inventory imports. **Do not commit, publish or paste complete raw inventory files into the public repository.** They may reveal installed apps and processes.

## Limits and safety

The registry count is a count of installed base SIS packages, **not** the number of visible apps, alive processes, removable packages or software dependencies. Name similarity between a package and process is a *text clue*, not proof the process belongs to that package. One snapshot cannot prove a service is unused, and today's absence does not mean it is safe to delete. The initial review-term matches (e.g. Ovi-branded services) are investigation leads only, not claims those services are obsolete, disconnected or safe to remove.

No package installation/removal, process changes, ROMPatcher operation, writes to protected directories, privilege changes or firmware writes are introduced. Existing signed write-batch features remain available separately. The current LAN link is authenticated at connection establishment but **unencrypted**, so use the trusted LAN only. A trustworthy firmware recovery route, package-to-file/SID mapping and dependency research are prerequisites for deeper OS changes.

## Field acceptance

1. Launch the v0.9 **Sanctuary host only** and reconnect the E7 Bridge v0.8.0 phone app.
2. Run `ping`, `info`, then `baseline capture idle`. Confirm capture completes and prints the native SIS registry count (previously 407) and current process count, without claiming the same counts are invariant.
3. Check the generated `.json` and `.md` locally. Confirm all package UIDs are sorted, uniquely recorded and that the report says *review leads, not removal recommendations*.
4. Capture a second snapshot and `baseline diff`; verify the Markdown and JSON diff files are created. Genuine differences may be empty.
5. Check music playback, Wi-Fi, normal standby and remembered connection settings. Keep v0.8.1 host as rollback if v0.9 misbehaves.

Only after real-device acceptance should this candidate be merged into `main`.

## Physical handset first baseline (2026-10-10)

The operator used the v0.9 host with the existing v0.8.0 E7 agent and produced an idle inventory with **407 installed base SIS packages** and **168 running process entries**. Raw memory readings at that instant were **257,228,800 bytes total** and **148,140,032 bytes free**; battery readings were left raw. The operator also reported `baseline diff` found **zero changes** between captures. Only one raw capture was shared for review, so the second capture and diff outputs have not been independently examined. These are physical host/handset observations, not synthetic test fixtures.

The initial Markdown review contained a **false-positive Ovi naming bug**: the substring `ovi` appeared inside ordinary words such as `provider` and `provisioning`. The report heuristic now requires `ovi` at the start of a word or package-name token, while recognising `Ovi Music`, `Ovisync` and `ovistore`. It additionally marks tightly named `nokiastoreclient`, `NokiaAnalyticsCollector`, and Norton/Symantec packages for further investigation only; it does not imply they are unused or removable. A new regression test covers these cases and the Linux suite now passes **137/137 tests**.

No raw inventory, installed-process list, private journal, or pairing data was included in this source change. Keep this PR draft until native phone regression checks are reported.
