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

## Owner's Sanctuary preflight result (12 October 2026)

Owner ran `python3 e7-observability-preflight.py`. The actual tool reported:

- `debugger_binaries_or_packages: []`; `coda`, `gdb`, `qtcreator`, `symbian-gcce-link`, and `trk` command lookups all returned false.
- **But** the file-scan cap was reached under `/home/darkstar/Downloads`, and both configured `/opt/toolchain/current` and `/toolchain/current` paths were absent. This is **not evidence that Sanctuary has no SDK/debugger elsewhere**. The command inventory did not check `node`, `npm`, `java`, `javac`, `ghidraRun` or `support/analyzeHeadless`.
- Four pre-existing Bridge snapshots contained **173, 172, 166 and 173 process entries**, all with `iaupdate_present=true` and `ncdserver_present=false`; no CODA/TRK process names. These snapshots predate the v0.15–v0.20 active checks, so `ncdserver_present=false` is **not proof the server fails to launch during an updater run**.
- No phone connection, new process sampling or device action occurred in this preflight.

## Owner-proposed REA (`morluto/rea`) assessment

Examined [REA README](https://github.com/morluto/rea/blob/main/README.md), [Ghidra provider setup](https://github.com/morluto/rea/blob/main/docs/installation.md#ghidra), [current raw-binary specification](https://github.com/morluto/rea/blob/main/docs/raw-binary.md), and actual [raw language mapping](https://github.com/morluto/rea/blob/main/src/ghidra/GhidraRawBinaryLanguage.ts) on **2026-10-12**. `morluto/rea` is an MCP/CLI AI-agent **orchestrator around existing Ghidra, IDA or Hopper**, not a Symbian debug agent or live IPC monitor.

**Potential value:** prompt-driven local **static** decompilation, xrefs and caller tracing around actual Belle `CNcdLoadNodeOperationImpl::HandleHttpError`, `EFailed`, `CNcdLoadNodeOperationProxy::CompleteCallback`, and `CIAUpdateLoader::OperationComplete`; easy repeatable artifact evidence. This could speed hypothesis ranking. It cannot show the handset's live `iPendingMessage` value or `iOperations.Count()`, and does not by itself fix a stale updater service.

**Major format/architecture caveat:** REA's current *headerless* `--target-format raw-binary --architecture arm` mode forces generic **`ARM:LE:32:v7`**, mapping input file offset **zero** to a caller-supplied address. It explicitly does **not** support Thumb-only variants as raw processors. The preserved Nokia binaries are Symbian E32/flattened E32 with Thumb code, E32 code-section file offset `0x9c`, and historical code base `0x8000`. **Do not blindly import the `.flat.bin` as raw ARMv7 and treat pseudocode as correct.** Prefer a previously established **analysis-only ELF wrapper preserving the byte-for-byte E32 code section**, known code coordinate mapping and an explicitly selected/verified Ghidra ARM/Thumb language and seeded function starts. Confirm successful Ghidra import, Thumb disassembly and mapping **before** any decompilation assertion. The earlier private LLVM synthetic ELF was not itself validation of Ghidra's import or of REA compatibility.

**Dependencies:** README says REA needs Node.js 22.x >= 22.19, 24.x >= 24.11 or 26+ and npm. Native decompilation also requires an existing licensed/available analysis provider; on Linux REA's Ghidra adapter documents an existing Ghidra **12.1.x** and **64-bit full JDK 21+**. The host preflight did **not** check these dependencies. Running `npx rea-agents setup` is a configuration-changing setup action, **not** a read-only preflight. The documented npm release and repo `main` can differ: `docs/raw-binary.md` and `src/ghidra/GhidraRawBinaryLanguage.ts` were absent from the documented 6.4.0 release commit, so do not assume `@latest` exposes every current-`main` command.

Recommended next **host-only** commands, not executed by the assistant:

```sh
for cmd in node npm java javac ghidraRun analyzeHeadless; do
  printf '%-16s ' "$cmd"
  command -v "$cmd" || true
done
node --version 2>/dev/null || true
npm --version 2>/dev/null || true
java -version 2>&1 | head -n 2
javac -version 2>&1
find /opt "$HOME/Downloads" -maxdepth 6 -type f -name analyzeHeadless -print 2>/dev/null | head -n 12
```

No automatic download, `npx` execution, `sudo`, phone debugger installation, NCD responder or protected cache modification is justified from this evaluation. The original preserved Belle images should stay private; REA runs local analysis but an AI agent may transmit returned evidence to its provider under separate data terms.

## Owner-operated REA/Ghidra provider doctor result (12 October 2026)

The owner followed the user-local Sanctuary installation instructions and supplied the complete JSON from `npx -y rea-agents@latest doctor --provider ghidra --json`:

- `healthy=true` for the explicitly selected **Ghidra provider**. All **9 of 9** scoped checks passed: Node **24.21.0**, Ghidra **12.1.4** under `~/opt/ghidra_12.1.4_PUBLIC`, Linux x64 platform, valid Ghidra installation, `analyzeHeadless` present, native decompiler executable recognized as Linux x86-64 ELF, and JDK **21.0.12.1** 64-bit installed. npm reports **11.19.0**; REA CLI identifies as **6.4.0**.
- `environment_healthy=false` is a **broader informational** result rather than a failed selected-provider check. REA labels **Debian 13** `unsupported_host` even while all the direct Ghidra checks pass; Hopper and IDA are unconfigured, as are optional REA skill identity and Codex registration. Neither alternate engine nor agent setup is required for REA **standalone CLI** analysis.
- The diagnostic does **not prove headless Ghidra has actually imported or decompiled a target** on Debian 13. This needs a separate, fully offline **non-Symbian** smoke test before analyzing the protected Nokia artifacts.
- The pinned REA **6.4.0** documentation explicitly supports `rea analyze /absolute/path/to/program --provider ghidra --json`. Proposed smoke test: `/usr/bin/true` (local Linux ELF x86-64), with output saved privately and no E7 connection. Use `npx -y rea-agents@6.4.0 analyze /usr/bin/true --provider ghidra --json`, not `rea setup`, to avoid automatic agent registration. npx may contact npm for its package cache.
- **Still unresolved:** the correct importer and ARM/Thumb mapping for original Belle E32 binaries. Ghidra's importer on REA 6.4.0 does not automatically understand the original Symbian E32 format and the later current-`main` headerless ARM mode excludes Thumb-only mappings. Retain original E32 images and use independently verified analysis-only ELF mapping before drawing claims from pseudocode.

No smoke-test outcome was reported with this doctor output. The handset was not contacted, rebooted, patched or re-tested. No installer or private NCD/IAUpdate cache operation was performed.

## Post-static-analysis decision on further phone trials (12 October 2026)

After the preflight, the owner actually performed **checksum-verified, host-only** REA 6.4.0/Ghidra 12.1.4 analysis of the original expanded `iaupdateengine.dll`, `ncdproxy_20019119.dll`, and `ncdserver_20019119.exe` and independent LLVM-19 Thumb disassembly of the complicated NCD server state machine. Current byte-level evidence is recorded in [REA-GHIDRA-BELLE-ELF-WRAPPER-PREP.md](REA-GHIDRA-BELLE-ELF-WRAPPER-PREP.md). It confirms:

- In the **server** `HandleHttpError` body, the vtable pointer **0x25671** enters a secondary-interface adjusting thunk at **0x25670** which reaches implementation **0x25634**; compiled code stores the error, marks state `EFailed=5`, and calls `RunOperation`. The apparent vtable entry/body ordering discrepancy is resolved.
- In the **server** `DoRunOperationL::EFailed` compiled path, it checks the pending IPC message pointer `this+0x6c` at **0x27392–0x27396** and conditionally sends completion **ID 3 (error)** via virtual `CompleteMessage`. In the independently decoded `RunOperation` exception path, a similar conditional error IPC dispatch is seen near **0x27402–0x27414**.
- In the **server** ordinary failed-state shared exit, `0x27320: movs r0,r4; 0x27322: bl 0x24e12`. The owner then disassembled **0x24e12–0x24e3e**: it iterates an observer array at **`this+0x54`**, obtains stored **`iError` at `this+0x30`**, and calls each observer's virtual slot **+0x8**. This independently matches [`CNcdBaseOperation::CompleteCallback`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/server/src/ncdbaseoperation.cpp#L973-L979). **The server observer callback is not the same as the client IPC completion.**
- The **client NCD proxy** actual Belle `HandleCompletedMessage` at **0x1297c** special-cases **ID 5 (NodesUpdated)**, sends `Continue`, and has normal-progress/error callback branches. The separate `CompleteCallback` at **0x12b54** iterates registered client observers and calls `OperationComplete`. The **IAUpdate loader** actual `OperationComplete` at **0x9e7e** removes completed work and notifies its observer only when the outstanding-operation count is zero.
- The owner also force-disassembled the **base NCD client completion handler** near **0x12220**, but this was only a **bounded linear excerpt**, with likely embedded data/literal-pool/jump-table bytes being interpreted as instructions around **0x1224e–0x1225a**. Do **not** claim that its **ID 3 (Error)** versus **ID 4 (Complete)** handling was independently proved from that window. The historical [base proxy source](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/client/src/ncdbaseoperationproxy.cpp#L318-L330) does support that intended mapping. Prefer control-flow-aware Ghidra with explicit switch reconstruction and source cross-check, not linear `-D` through data.

**New source-only lifecycle nuance:** [server `CNcdBaseOperation::HandleContinueMessage`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/server/src/ncdbaseoperation.cpp#L222-L279) stores a new pending message for a running operation; a Continue arriving in an unexpected state stores it temporarily and invokes `FailOperation(KErrNotReady)`. [Server `CompleteMessage`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/server/src/ncdbaseoperation.cpp#L457-L481) clears the pending pointer when returning a completion. [Client `SendContinueMessageL`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/client/src/ncdbaseoperationproxy.cpp#L392-L419) submits another async Continue only when its active object is not already active. **Consequently `iPendingMessage==NULL` for one instant is not by itself proof of a permanent lost completion**: a later Continue might recover or produce another error. The lifecycle and actual event ordering remain undetermined.

### Explicit go/no-go criteria for any *new physical E7 update check*

1. **Interpretability / observability (currently NO-GO):** Establish a demonstrably read-only, authorized way to distinguish at least one previously unobserved *phone-side* transition during a trial: child's terminal HTTP event, `HandleHttpError`, `iPendingMessage` at failure, server error completion ID 3, client observer `CompleteCallback(error)`, or IAUpdate `iOperations.Count()`/final `LoadComplete`. A host HTTP socket write, passive network capture and the installed E7 Bridge's process-name list **cannot prove private callback or IPC delivery**. Current preflight found no verified pre-installed protected-system tracing capability. Do not install CODA/TRK or bypass system protections merely to satisfy this gate.
2. **Reversibility (currently NO-GO):** Identify exactly which original writable **C:** NCD/IAUpdate cache/registry contents a network-only catalogue test could mutate, preserve them independently and verify a **non-destructive restoration** path. Existing **Z:** archive `SYM.RPKG`, `romdumpplus.dmp`, or individual `.cre` are not established as a full recoverable C: state snapshot. If plan expands to firmware flashing, satisfy the separate exact RM-626 product/variant and stock dead-USB recovery requirements in [FIRMWARE-PREFLIGHT-V1](../../docs/FIRMWARE-PREFLIGHT-V1.md).
3. **Protocol / instrumentation design (offline):** Finish the server pending-message **Start → NodesUpdated → Continue → Error/Complete** lifecycle and base-client completion ID 3/4 switch analysis on saved binaries and historical source. Build a deterministic host-only test of the exact canned configuration/root/child fixture, fail closed on all unknown paths and bound response scope and duration. **No new synthetic payload design is authorized by static findings alone.**
4. **Only once (1) and (2) are proven:** propose a single consented, time-bounded, clearly logged Wi-Fi-only experiment with one changed variable, observable success/error/timeout criteria, an explicit stop/rollback method, and no installation/flash or cache reset. A comparison of "spinner versus no spinner" by itself is not sufficient diagnostic evidence.

**Disposition:** proceed with local static source/binary analysis and host-only deterministic tests. The new Ghidra/LLVM successes reduce *code uncertainty* but do not change the missing **live observability and recovery** requirements. The phone remains frozen from synthetic NCD response trials.

## Interpretation and next decision

- If **no agent** is found: don't assume one is absent from the phone; the host-side install path is simply unconfirmed.
- If a **CODA/TRK package** is found on Sanctuary: first verify provenance, signer/compatibility and whether this actual agent could inspect protected system services without changing them; do **not** install it just to see what happens.
- If old E7 Bridge snapshots include `ncdserver` or `iaupdate`: they confirm process *names at snapshot time*, not active callbacks, queued operations or a hang cause.
- Without a **verified, already-installed, authorized read-only system-debug interface**, the legitimate next action remains offline source/binary analysis and preserving the phone, not synthesizing additional catalogue variants.

**No v0.21 OTA trial, package installation, debugger injection, service patch, ROM write, E7 private C: cache access or post-hoc claim of child IPC observation was performed.** PR #17 stays docs-only, draft/unmerged; `main` unchanged.
