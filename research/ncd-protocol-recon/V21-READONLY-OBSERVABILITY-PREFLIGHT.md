# E7 NCD: read-only observability feasibility preflight

**12 October 2026 | Prepared and tested on the authoring host only. E7 not accessed. This is NOT a v0.21 NCD response experiment.**

## Where experiments leave us

The owner-operated v0.19 observation included one original configuration HTTP 200, one original 566-byte root-folder HTTP 200, and a guarded zero-body **child HTTP 404**. The phone kept spinning. The paired v0.20 gave the identical configuration and an empty-body root HTTP 200; the phone stopped and reported its standard error. These host-side writes do **not** establish device parse or callback completion. Historical v0.12/v0.13 FolderRef-only trials also spun, though with different fixtures.

The [Belle root-to-child completion audit](V20-BELLE-ROOT-TO-CHILD-COMPLETION-AUDIT.md) ran 54/54 read-only assertions on four preserved actual Belle E32 images and shipped XML fixtures. It establishes that the IAUpdateLoader's compiled `NodesUpdated` is a no-op, `OperationComplete` can launch child loading after root completion, and the NCD child failure IPC path depends on a pending client message. Since the *child* browse followed the successful root response, initial root completion is now a less-favored wait point than **later child error delivery or another outstanding load**.

**Important:** The condition `iPendingMessage != NULL` is a normal code gate, **not proof that it was false on the real handset**. There is no E7 callback trace.

## What existing E7 Bridge v0.8 can measure

[Installed bridge documentation](../../bridge/e7-bridge/README.md) and its [phone source](../../bridge/e7-bridge/phone/main.cpp) confirm that the existing manually launched bridge supports authenticated:

- Paged read-only process-name enumeration via Symbian `TFindProcess`.
- Host-only `ps save`, `capture`, `record` process/RAM/power snapshots.
- Read-only installed-package registry listing.

None of these APIs captures `CNcdLoadNodeOperationImpl::HandleHttpError`, `CNcdLoadNodeOperationProxy::CompleteCallback`, proxy's `Continue` IPC, or `CIAUpdateLoader::iOperations.Count()`. The bridge does not expose arbitrary process memory or privileged system debug events. A process-name snapshot **cannot demonstrate completion or failure of child IPC**.

## Debugger feasibility and security

Historical [Qt Creator's Symbian documentation](https://qt.developpez.com/doc/qtcreator-2.3/creator-developing-symbian/) identifies Nokia **CODA** as an on-device application debugger with USB/WLAN options. However, the agent must be present/installed and linked to an appropriate host debugger; merely possessing a CODA `.sis` cannot read another protected process. Older [MetroTRK/IDA documentation](https://manualzz.com/doc/29445867/hex-rays-ida-pro-debugger--symbian-application--metrotrk-...) discusses restrictions while stepping into protected system areas; independent [Symbian AppTRK security research](https://sec-consult.com/fileadmin/user_upload/sec-consult/Statisch/Vulnerability_Lab/Studies_and_Whitepapers/SEC-Consult_Whitepaper_pwning_symbian_v105_public.pdf) documents restrictions on attaching to capability-protected and ROM processes. The precise CODA policy on this particular phone is **unverified**, but a standard app debugger is not a proven read-only window into the NCD server.

Do **not** install or start CODA/TRK, attach to `ncdserver` or `iaupdate`, patch capabilities, or change protected cache on this evidence. Debugger attachment often changes execution scheduling; "observation" is not automatically non-invasive. A malicious/modified debugger or platform-security bypass would be a much higher-risk project, and is **not authorized** by this preflight.

## Sanctuary-only checker

The user-facing standalone file `e7-observability-preflight.py` was created outside the GitHub repo and SHA256 checked:

`628a96e63d6e597df4c329d9003baf021144ab054414922baa30bc24b64ff221`

The Python 3 standard-library-only command:

```sh
python3 ~/Downloads/e7-observability-preflight.py
```

does **not** open sockets, authenticate to E7, invoke another executable, use `sudo`, write files or change services. It scans only a bounded set of *existing host files* within common SDK/Downloads roots for filenames suggesting legacy CODA or TRK packages; it prints candidate file **basenames, byte counts and SHA256** (or skips hashing candidates over 64 MiB). It reports whether named host development commands are in the current `PATH`. It also summarizes up to five **already saved** Bridge process snapshot JSON files under `~/.local/share/e7-bridge/snapshots` without returning raw process names.

Explicit roots are supported:

```sh
python3 ~/Downloads/e7-observability-preflight.py --root ~/Downloads --root /toolchain/current
```

The scan is bounded (depth <=8, <=12000 files/root, <=16 candidates), excludes nested symlinks and common huge generated directories, resolves only explicitly chosen SDK-root symlinks, reads at most 1 MB per saved JSON, and doesn't print pairing keys, phone identifiers or raw process inventories.

**8/8 local unit tests passed**, covering strict file detection, bounded walks, symlink handling, digest correctness, private-name redaction, and lack of file creation. These tests were host-only, not E7 tests. The authoring container's lack of matching tools has **no bearing on whether Sanctuary has them**.

## Interpretation and next decision

- If **no agent** is found: don't assume one is absent from the phone; the host-side install path is simply unconfirmed.
- If a **CODA/TRK package** is found on Sanctuary: first verify provenance, signer/compatibility and whether this actual agent could inspect protected system services without changing them; do **not** install it just to see what happens.
- If old E7 Bridge snapshots include `ncdserver` or `iaupdate`: they confirm process *names at snapshot time*, not active callbacks, queued operations or a hang cause.
- Without a **verified, already-installed, authorized read-only system-debug interface**, the legitimate next action remains offline source/binary analysis and preserving the phone, not synthesizing additional catalogue variants.

**No v0.21 OTA trial, package installation, debugger injection, service patch, ROM write, E7 private C: cache access or post-hoc claim of child IPC observation was performed.** PR #17 stays docs-only, draft/unmerged; `main` unchanged.
