# REA / Ghidra: first working Debian import, verified E32-to-analysis-ELF preparation

**12 October 2026 | Host-only; no new E7 Software Update check, debugger attachment, SIS install, cache manipulation or phone contact.**

## Actual owner REA/Ghidra smoke-test success

After `REA 6.4.0` provider doctor showed **all 9 Ghidra-scoped checks healthy** on Sanctuary, the owner ran:

```sh
source ~/opt/e7-rea-env.sh
npx -y rea-agents@6.4.0 analyze /usr/bin/true --provider ghidra --json
```

in a private output directory.

Owner directly reported **"REA analysis command succeeded"**, an empty diagnostic stderr preview and the beginning of JSON evidence containing:
- `subject.name=true`, `format=elf`, `architecture=x86_64`, and original target digest `b381cc8c55ec524b9fa92897f0882e855357468b4a763519cec47e05994d61ff`.
- The evidence profile's upstream provider explicitly names **Ghidra 12.1.4**, `loader=auto-from-header`, `language_id=auto-from-header`, `import_mode=ephemeral-source-immutable` and default analysis.

**What this proves:** REA successfully used Ghidra to import/analyze an actual *Linux x64 ELF* on Debian 13, despite Debian being an informationally unsupported host in the broader doctor report. It does **not yet demonstrate** decompiling an ARM/Thumb ELF, resolving E32 relocations or a specific method in the Belle binaries. The command was generic `analyze`, not a verified individual function decompilation.

## Authoring-host offline conversion verification

The separately delivered one-file Python utility `e7_make_ghidra_elf.py` (not committed in this documentation-only PR) has SHA256:

`e83e6096408b7768a1015a3bc90c0e876c9113d64b4eb52989e489f1d60e8200`.

It is **stdlib only**, requires explicit input path and separate existing output directory, and **refuses to run if the input filename or whole-file SHA256 doesn't exactly match one of the four owner-archived E32 images**. It validates `EPOC`, E32 code-file offset `0x9c`, and code image base `0x8000` from the original file header. It then builds an **analysis-only ELF32 little-endian ARM EABI5 ET_EXEC carrier**, containing an exact copy of the E32 code section as its sole RX mapped segment, and adds ELF symbols with Thumb bit 0 for selected previously audited code entrypoints. The original input is not modified; output is created with exclusive create, mode 0600, never overwritten. This ELF is **not a working Symbian image** and **must never be executed or installed on a device**.

The output is intentionally a **synthetic analysis representation**, not a linker-corrected implementation of E32 relocations, data sections or imported Symbian runtime functions. The remaining flat-E32 metadata and external imports are not reconstructed. Ghidra could misinterpret mixed ARM/Thumb regions, vtables or cross-module calls; every function must be checked against previously verified address/instruction bytes before relying on pseudocode.

## Owner's RPKG inventory and exact preserved images located (12 October 2026)

The owner confirmed the case-sensitive original dump filename **`SYM.RPKG`** (uppercase). The read-only `e7_rpkg_inventory.py` parsed **13,356/13,356** advertised records from the 178,829,422-byte **RPK2** archive, with **0 trailing bytes**, and identified 51 updater/catalogue related objects. The compressed E32 objects `Z:\\sys\\bin\\iaupdateengine.dll`, `iaupdate.exe`, `ncdproxy_20019119.dll`, and `ncdserver_20019119.exe` were all present with an `EPOC` signature at byte 16.

**More importantly:** four previously flattened image files exist already beneath the owner's E7 dump working tree in **`e7-updater-bytepair-v02/`**:

- `iaupdateengine.dll.flat.bin`
- `iaupdate.exe.flat.bin`
- `ncdproxy_20019119.dll.flat.bin`
- `ncdserver_20019119.exe.flat.bin`

These are *file-existence observations*, not new hash checks. The converter must still enforce the expected exact flat-E32 SHA256 before generating the analysis carrier. **Original RPKG embedded compressed-image hashes and later flattened-image hashes differ by design**; do not compare them as though they were identical raw files. There is **no reason to extract or unpack the 171-MiB archive again** just to begin Ghidra analysis.

Proposed next owner-only host command, after downloading the previously delivered converter:

```sh
source ~/opt/e7-rea-env.sh
DUMP="$HOME/Documents/E7 dump"
SRC="$DUMP/e7-updater-bytepair-v02/iaupdateengine.dll.flat.bin"
OUT="$HOME/Downloads/e7-rea-elf-work"
printf '%s  %s\\n' 'f395e88a078d6837823e169c1209d6ad295dad242ef5564b144c97584ec5ab99' "$SRC" | sha256sum -c -
install -d -m 0700 "$OUT"
python3 "$HOME/Downloads/e7_make_ghidra_elf.py" --input "$SRC" --output-dir "$OUT"
readelf -h -l -sW "$OUT/iaupdateengine.dll.flat.bin.analysis.elf"
npx -y rea-agents@6.4.0 analyze "$OUT/iaupdateengine.dll.flat.bin.analysis.elf" --provider ghidra --json > "$OUT/overview.json"
```

As of this note, **this converter command and Ghidra ARM import have not been run on Sanctuary**. Nothing is written to the E7, the source E32 is unchanged and no file blobs are uploaded or committed.

## Actual Sanctuary ARM ELF import succeeded (owner-operated, 12 October 2026)

The owner used the existing previously flattened E32 image at `~/Documents/E7 dump/e7-updater-bytepair-v02/iaupdateengine.dll.flat.bin`. Its independently displayed `sha256sum` was **`f395e88a078d6837823e169c1209d6ad295dad242ef5564b144c97584ec5ab99`**, an exact match to the earlier preserved-Belle audit. Running the separately supplied `e7_make_ghidra_elf.py` produced the following **actual** user-visible verification:

- `status=created_analysis_elf_not_phone_executable`
- `code_bytes_identical=true`, `code_bytes=62780`, `source_code_offset=0x9c`, `mapped_code_base=0x8000`
- **ELF digest exactly matches the previously authoring-host verified output:** `c148868d92d698124f04d68b88603e4682a076e2b71c9dc462e681ba37315e89`.
- `readelf` reported **ELF32 ARM, entry address 0x8000**. Five `CIAUpdateLoader_*` Thumb-tagged `STT_FUNC` ELF symbols were present, including `CIAUpdateLoader_OperationComplete` symbol **0x9e7f** (instruction address **0x9e7e**), and `NodesUpdated` symbol **0x9d9f**.
- Owner then ran the **actual** `npx -y rea-agents@6.4.0 analyze "$ELF" --provider ghidra --json` against the generated **Nokia** ELF. The returned JSON evidence began with `operation=binary_overview`, `subject.format=elf`, `architecture=arm`, a matching ELF SHA256, and an upstream `provider.id=ghidra`, `version=12.1.4`, `loader=auto-from-header`. **No stderr errors were reported.**

**Meaning:** REA/Ghidra did successfully import the ARM ELF carrier *on Sanctuary*, not just the earlier `/usr/bin/true` Linux x86-64 smoke target. This retires the prior "ARM Ghidra import untested" gate. It does **not** prove Ghidra selected Thumb mode for the target routine, decoded `OperationComplete` correctly, inferred imports/relocations, or produced valid function pseudocode.

**Next gate (host-only):** `npx -y rea-agents@6.4.0 instructions "$ELF" CIAUpdateLoader_OperationComplete --provider ghidra --json` (pinned 6.4.0 [CLI docs](https://github.com/morluto/rea/blob/a56f7bb668ab23fec8d33f7af353ac7ed2fe1895/docs/cli.md)). Inspect procedure identity, decoded instruction address and mnemonic. Compare the first Thumb instructions to independent LLVM Thumbv5TE bytes at `0x9e7e` before requesting or trusting pseudocode. Inference of runtime `iOperations` state on the E7 remains impossible from static decompilation alone.

No source firmware or generated ELF was committed or uploaded; this is a report of the owner's text output only. No live phone activity occurred.

## Actual Sanctuary Ghidra Thumb method validation (12 October 2026)

Owner ran REA 6.4.0 `instructions` with the original SHA256-verified `iaupdateengine.dll.flat.bin` analysis-only ELF. **Success**: `read_function_instructions`, `procedure.address=0x9e7e`, `procedure.name=CIAUpdateLoader_OperationComplete`, `external=false`, `thunk=false`, with valid code and exactly matching Thumb prologue `push {r0,r1,r2,r4,r5,r6,r7,lr}`, `sub sp,#8`, `movs r5,r0`. The decoded method also shows `bl 0x9e28` at `0x9ee8` and `0x9f24` (historical `NextLoadLoopL`), and the final `iOperations.Count()==0` gate `0x9f60: bl 0x12b10; 0x9f64: cmp r0,#0; 0x9f66: bne 0x9f88` before observer dispatch at `0x9f68..0x9f70`. These are real firmware instructions under Ghidra, consistent with [Nokia's `CIAUpdateLoader::OperationComplete`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/iaupdate/IAD/engine/controller/src/iaupdateloader.cpp#L323-L421).

**Ghidra caveat:** it reports three discontiguous body ranges `0x9e7e..0x9ef3`, `0x9f0a..0x9f2f`, `0x9f4e..0x9f89`, containing 216 bytes in a 268-byte span. Its ending branch `0x9f88: b 0x9e20` targets outside that reported function body; whether this is a legitimate shared tail or synthetic-ELF analysis boundary issue is unverified. Next do standalone REA `decompile` on the named function, check control flow against the historical source and reject unsound inferred symbols/imports. No live runtime values, HTTP callbacks or on-device operation counts have been established. This was host-only; no ROM/cache modification or E7 network request.

## Actual REA Ghidra OperationComplete pseudocode, source comparison (12 October 2026)

The owner executed `npx -y rea-agents@6.4.0 decompile ... CIAUpdateLoader_OperationComplete --provider ghidra --json` against the checksum-matched **analysis-only** `iaupdateengine.dll` ELF. The command returned `operation=procedure_pseudo_code` and decompiled the real Thumb method at `0x9e7e`, consistent with the previously verified instruction body.

Key decompiler identifications, **inferred by direct comparison to** [Nokia's historical `CIAUpdateLoader::OperationComplete` source](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/iaupdate/IAD/engine/controller/src/iaupdateloader.cpp#L323-L422):

| Ghidra representation | Source meaning |
| --- | --- |
| `param_1` | loader instance (`this`) |
| `param_2` | `MNcdLoadNodeOperation& aOperation` |
| `param_3` | `TInt aError` |
| `param_1 + 0x10` | `iOperations` array |
| `param_1 + 0x0c` | `iObserver` |
| `param_1 + 0x34` | accumulated `iErrorCode` |
| `piVar7` after `Node()` call | `operationNode` |
| `local_28` | operation-type enum retrieved from matched array record |
| `FUN_00012b10` with array pointer | consistent with array `Count()` helper |

The code searches the outstanding-operation array, finds a matching operation, gets `Node()`, releases and removes the matched operation, conditionally invokes `CIAUpdateLoader_NextLoadLoopL` both for `aError==0` and `aError!=0`, releases the node, and calls the observer **only if the current array count becomes zero**. Ghidra displays a branch `if (iVar1 == 0)` after `FUN_00012b10`; this matches the independent Thumb instruction sequence `0x9f60: bl 0x12b10`, `0x9f64: cmp r0,#0`, `0x9f66: bne 0x9f88`, followed by the indirect observer call at `0x9f68..0x9f70`. This is strong actual-Belle evidence of the final-completion gate, **not a trace of its runtime value**.

**Limits / potential discrepancies:**

- The generated C `thunk_EXT_FUN_0000080c` calls are **unresolved Symbian/import and TRAP mechanisms**, not reliable source-level function names or normal argument signatures. The decompiler fails to reproduce the historical source's `TRAPD(trapError)` propagation / `iErrorCode = trapError` for `NextLoadLoopL` throwing on the `aError==0` path. **Do not conclude the compiled binary omits this exception/error handling** from its absence in C pseudocode.
- The owner output shows the indirect observer call and then `FUN_0000cfe8()` conditionally when `iErrorCode==0`. In the historical source the (likely) firmware-version save is before `iObserver.LoadComplete`, so there is an **apparent call-order divergence**. The instruction ordering is real, but the anonymous `FUN_0000cfe8` identity has **not been independently proven** here; treat this as a discrepancy requiring confirmation, **not an established updater bug**.
- No imports, data section, relocations, live `iOperations.Count()`, client IPC callback or phone-side HTTP status was reconstructed. The synthetic ELF has limited runtime semantics; statically successful pseudocode is not proof the physical E7 ever took this path during the spinner.

**Next host-only step:** analyze independently verified `ncdproxy_20019119.dll.flat.bin` (SHA256 `09994060128754da1fe0bcfb6ce4c4766c8607eb978fc96768f623f9d9afda38`) with the same fail-closed ELF converter, beginning at already labeled `CNcdLoadNodeProxy_CompleteCallback` (code `0x12b54`) and then `CNcdLoadNodeProxy_HandleCompletedMessage` (code `0x1297c`). Historical [derived proxy callback](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/client/src/ncdloadnodeoperationproxy.cpp#L377-L390) notifies each observer's `OperationComplete`, while [base proxy completion ID 3](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/client/src/ncdbaseoperationproxy.cpp#L318-L330) calls `CompleteCallback(iStatus.Int())`. Neither path has been observed live.

**Preservation:** all research offline. Do not run a new updater check, alter private NCD cache, install Symbian debugger, or commit proprietary E32 images/ELF output. Draft PR #17 remains docs-only, unmerged; `main` untouched.

## Actual Sanctuary NCD proxy CompleteCallback Thumb validation (owner-operated, 12 October 2026)

The owner verified the preserved `ncdproxy_20019119.dll.flat.bin` using exact SHA256 `09994060128754da1fe0bcfb6ce4c4766c8607eb978fc96768f623f9d9afda38` (PASS), and created the analysis-only ARM ELF. Converter confirmed `0x9c` E32 source code offset, virtual code base `0x8000`, **180,476 identical code bytes**, four predefined Thumb entrypoint symbols, and exact previously verified generated ELF SHA256 `95e97a93f2a1a69e62876c699df22cfd9cb6cf6a1c578d7f3163339c93d53c07`.

The owner ran REA 6.4.0 / Ghidra 12.1.4 `instructions` for `CNcdLoadNodeProxy_CompleteCallback`. The returned actual method name was correct and resolved to **Thumb code at `0x12b54`**. Key observations (all from the owner's Ghidra instruction output):

- `0x12b54: push {r0,r1,r4,r5,r6,r7,lr}`; `0x12b56: sub sp,#4`: valid Thumb prologue.
- `0x12b5a..0x12b60`: virtual call through vtable offset `+0x18`, consistent with `AddRef()`.
- `0x12b66: adds r5,#0x74`, `0x12b6a: adds r7,#0x6c`: object/observer-array and interface-base pointer adjustments.
- `0x12b6e..0x12b80`: fetches current observer, loads saved error argument (`ldr r2,[sp,#8]`), and calls vtable offset `+0x8` with a `this`-adjusted operation argument, consistent with `iObservers[i]->OperationComplete(*this,aError)`.
- `0x12b82..0x12b8c`: increments index, fetches collection count and loops while observers remain.
- `0x12b8e..0x12b94`: vtable call through offset `+0x1c`, consistent with `Release()`; `0x12b96` restores registers and returns.

This independently tracks Nokia's [historical 377–390 `CNcdLoadNodeOperationProxy::CompleteCallback`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/client/src/ncdloadnodeoperationproxy.cpp#L377-L390), which explicitly implements `AddRef(); for observers: OperationComplete(*this,aError); Release();`.

**Evidence boundary:** Two *different preserved Belle modules* (IAUpdate engine and NCD proxy) have now been loaded into Ghidra and had meaningful Thumb methods validated against original Nokia source. Together they statically establish the producer/consumer ABI shape for this observer callback, **not its delivery in the physical E7 during the spinner**. This does **not** prove that the entire stack can be decompiled faithfully: other E32 binaries still require validation, missing import/data/relocation mappings limit cross-module decompilation, and the real waiting point (`iPendingMessage`, HTTP terminal state or `iOperations.Count()`) remains unobserved. Ghidra/REA supports the work; it is not a live Symbian debugger.

**Next offline discriminator:** inspect the NCD client's `CNcdLoadNodeProxy_HandleCompletedMessage` at `0x1297c` and the NCD server's HTTP error handler and `EFailed` completion IPC gate, then correlate explicit completion ID 3 with this validated observer callback. Avoid additional E7 tests or claims of a repaired updater. No source ROM/ELF uploaded to the public repo or execution on the phone; research PR stays draft, unmerged and `main` unchanged.

## Actual Sanctuary NCD HandleCompletedMessage Thumb and pseudocode validation (12 October 2026)

The owner ran REA 6.4.0 / Ghidra 12.1.4 `instructions` **and** `decompile` against the prior checksum-verified, analysis-only `ncdproxy_20019119.dll` ARM ELF (`95e97a93f2a1a69e62876c699df22cfd9cb6cf6a1c578d7f3163339c93d53c07`). Both operations completed. `CNcdLoadNodeProxy_HandleCompletedMessage` resolved at **0x1297c**, with **59 Ghidra instruction lines** in the owner's output.

Verified branch and virtual-dispatch observations:

| Belle ARM/Thumb code address | Observed behavior | Independently corroborating original Nokia source |
| --- | --- | --- |
| `0x12986: cmp r1,#5`, `0x12988: bne 0x12a18` | Completion ID **5** gets a distinct `NodesUpdated` path; others use the base dispatch | [`CNcdLoadNodeOperationProxy::HandleCompletedMessage`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/client/src/ncdloadnodeoperationproxy.cpp#L258-L306) |
| `0x129a8..0x129ce` | Clears/repopulates loaded-node identifiers from completion stream | same source, lines 270–283 |
| `0x129d0..0x129d6`: virtual call at `+0x28` | Sends the next **Continue** request | same source, line 284; separate request function ID **3** |
| `0x12a04..0x12a08`: virtual call at `+0x30` | Normal progress callback after successful trap | same source, lines 286–290 |
| `0x12a0e..0x12a14`: virtual call at `+0x38` | Error completion callback with error in `r1`, after error trap | same source, lines 291–294 |
| `0x12a18..0x12a1c`: direct call `0x12220` | Non-ID-5 completion handed to `CNcdBaseOperationProxy::HandleCompletedMessage` | same source, lines 298–302; [base completion ID 3=Error, 4=Complete](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/client/src/ncdbaseoperationproxy.cpp#L318-L330) |

**Decompiler reliability caveat:** Ghidra warned `Removing unreachable block (ram,0x00012a0e)` and omitted the `CompleteCallback(err)` branch from C pseudocode. The preserved *instruction disassembly* still contains that branch. Historical source wraps parsing/continue in `TRAPD(err,...)` and executes the error callback for nonzero error. This likely represents **incomplete Symbian trap/exception flow recovery in the synthetic code-only ELF**, not proof that the original Belle error branch is unreachable. The actual runtime execution of that branch remains unknown. Also, the decompiler's `thunk_EXT_FUN` names are unresolved imports, not reliable original function identities.

**Meaning:** The physical Belle client's ID-5 special path, base-dispatch handoff, expected Continue/progress/error callbacks, and separate observer `CompleteCallback` are now independently corroborated by Ghidra's *actual Thumb disassembly* and historical C++. This is not a complete stack reconstruction or direct E7 IPC/runtime trace. The connection from a child HTTP 404 through the NCD server's `EFailed` and pending IPC message still needs validation.

**Next owner-only offline analysis:** `ncdserver_20019119.exe.flat.bin` already exists in the same private `e7-updater-bytepair-v02` directory; expected SHA256 `c26fc0dea62a0a1a3a26e6bf387ad6dca78a581a7214fb8fc11d8748b407baa5`. Generate a separate analysis ELF with the existing fail-closed converter; expected ELF SHA256 `e81c6fe132922455bff8addb691f342e45be026623c0f5aa6dd53e57593f215d`. Converter seeds `CNcdLoadNodeOperation_DoRunOperationL` at **0x26e94** and `CNcdLoadNodeOperation_RunOperation` at **0x273b2**, allowing read-only Ghidra inspection. **Correction:** `0x2732c..0x2738c` belongs to the `EComplete` state, while the ordinary `EFailed` pending-message gate is near `0x27392..0x273a4`; the wrapper's separate TRAP-error handling begins near `0x273ea`. Separately audited `HandleHttpError` is near **0x25670**; it currently has no converter-predefined ELF function symbol, so don't assume automatic Ghidra discovery. Keep `RunOperation` symbol distinct from its target `DoRunOperationL`. Do not edit the user's verified converter or original image merely to add a label.

Phone untouched, no new synthetic catalogue response, cache/flash/debugger change, or proprietary binaries committed. Draft PR #17 remains open and unmerged.

## Actual Sanctuary NCD server RunOperation exception path, not full state machine (12 October 2026)

Owner verified the *original* preserved `ncdserver_20019119.exe.flat.bin` SHA256 `c26fc0dea62a0a1a3a26e6bf387ad6dca78a581a7214fb8fc11d8748b407baa5` against the earlier audit, and generated its *code-identical* analysis ELF with **449,512 E32 code bytes**, mapped at image base **0x8000**, sourced at E32 file offset **0x9c**. Generated ELF SHA256 exactly matched `e81c6fe132922455bff8addb691f342e45be026623c0f5aa6dd53e57593f215d`; this image is **not a functioning Symbian executable**.

The pinned REA 6.4.0 / Ghidra 12.1.4 `instructions` queries **both succeeded**:

- `CNcdLoadNodeOperation_DoRunOperationL` was recognized at **0x26e94**, but Ghidra's function-manager instruction list contained **only 29** instructions. The owner's earlier address-filter printed "Region not recognized inside this function" because the filter searched **0x27310..0x27395**. This **does not show that those bytes are absent** from the underlying ELF or that the machine-code state machine stops there. Synthetic ELF's missing data/relocation/jump-table mappings may cause Ghidra to split or omit CFG regions.
- `CNcdLoadNodeOperation_RunOperation` was recognized at **0x273b2**, returning **39 decoded Thumb instructions**. A standard exception trap wraps the call at `0x273c6: bl 0x26e94`; after exception handling, the continuation at `0x273ea` reads the trapped error. A nonzero error invokes cancellation, stores **state EFailed=5 at `this+0xfc`** (`0x273f8..0x273fc`) and stores the error at **`this+0x30`** (`0x273fe..0x27400`). It checks **`this+0x6c`** at `0x27402..0x27406`, consistent with `iPendingMessage`. If non-null, it invokes a vtable `+0x54` completion with **completion ID 3** (`0x27408..0x27414`); it then calls `0x24e12` unconditionally after that conditional block (`0x27416..0x27418`), consistent with the server's own `CompleteCallback()`.

These observations align with the *distinct* [original Nokia `CNcdLoadNodeOperationImpl::RunOperation` catch/Leave path, lines 1878–1902](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/server/src/ncdloadnodeoperationimpl.cpp#L1878-L1902). **This observed wrapper path is only executed when `DoRunOperationL` Leaves/throws.** Do **not** mistake its gated ID-3 send for runtime proof of a physical E7 child-HTTP-error callback.

**Address correction to an earlier draft observation:** the confirmed `0x2732c..0x2738c` area lies in `DoRunOperationL`'s **EComplete** path, where code emits completion ID **5** (NodesUpdated) or **4** (Complete), as already described in [V14-4 control-flow audit](V14-4-BELLE-CONTROLFLOW-AUDIT.md). The independent **ordinary EFailed** state within `DoRunOperationL` checks `iPendingMessage` at code-relative `+0x1f392..+0x1f396`, hence absolute **0x27392..0x27396**, and conditionally sends error completion ID 3 around **0x2739a..0x273a4**. That path corresponds to the separate [Nokia `DoRunOperationL` `case EFailed`, lines 2310–2324](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/server/src/ncdloadnodeoperationimpl.cpp#L2310-L2324) and **has not yet been returned by Ghidra's `DoRunOperationL` function body**.

Next safe, nonmutating host step: force explicit **Thumbv5TE** LLVM disassembly in the short `0x27388..0x273b2` code range using the exact fingerprinted ELF. Check error-message conditional and branch destinations against the compiled code and historical source; do not edit ROM images, alter Ghidra's global settings or assume the omitted Ghidra instructions are unreachable.

**No handset connection, catalogue probing, source/ELF upload, runtime callback trace, cached private file mutation, or merge occurred.** The repository PR remains documentation-only, draft and unmerged.

## Actual owner LLVM Thumb confirmation of ordinary EFailed IPC gate (12 October 2026)

Owner installed host-only LLVM 19 tooling and ran `llvm-objdump-19 -D --triple=thumbv5te-none-eabi --start-address=0x27388 --stop-address=0x273b2` on the **exact checksum-verified synthetic** ELF32 ARM `ncdserver_20019119.exe.flat.bin.analysis.elf`, SHA256 `e81c6fe132922455bff8addb691f342e45be026623c0f5aa6dd53e57593f215d`. This direct forced-Thumb disassembly succeeds **even though Ghidra's automatic function body contained only 29 instruction lines for the surrounding state machine**.

Decisive **actual preserved firmware instruction sequence**:

```asm
27388: e7ca          b    0x27320    ; previous state branch, not EFailed entry
2738a: 6820          ldr  r0,[r4]
2738c: 6a81          ldr  r1,[r0,#0x28]
2738e: 0020          movs r0,r4
27390: 4788          blx  r1         ; virtual Cancel, source-correlated
27392: 6ee0          ldr  r0,[r4,#0x6c]  ; candidate iPendingMessage
27394: 2800          cmp  r0,#0
27396: d0c3          beq  0x27320    ; no pending IPC: skip error message send
27398: 6820          ldr  r0,[r4]
2739a: 2203          movs r2,#3      ; ENCDOperationMessageCompletionError
2739c: 6d45          ldr  r5,[r0,#0x54]
2739e: 6b23          ldr  r3,[r4,#0x30]  ; iError
273a0: 9914          ldr  r1,[sp,#0x50]  ; message argument (not yet traced back)
273a2: 0020          movs r0,r4
273a4: 47a8          blx  r5         ; virtual CompleteMessage overload
273a6: e7bb          b    0x27320    ; shared following block not yet independently decoded
```

This is now **independent LLVM reconstruction of the ordinary `DoRunOperationL` EFailed state**, not the separate `RunOperation()` TRAP/Leave error handler at `0x273ea..0x27418`. Both compiled failure variants independently gate the outgoing **client error IPC completion ID 3** on a pending message, as described by original Nokia source [`case EFailed` lines 2310–2324](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/server/src/ncdloadnodeoperationimpl.cpp#L2310-L2324). This substantiates the presence of the gate in the real ROM, **not the runtime contents of `iPendingMessage` during the handset's child HTTP 404**, nor whether the server's own `CompleteCallback` or client observer ran.

Next nonmutating host work:
1. LLVM Thumb disassemble the shared branch destination `0x27320` in a small bounded window to verify the server callback and return behavior.
2. LLVM Thumb disassemble the `MCatalogsHttpObserver` methods around `0x25630` / `0x25670` and verify which instruction blocks belong to the actual `HandleHttpError`. The apparent V20 audit address mismatch was **resolved by later owner LLVM evidence (see below)**: `0x25671` is the Thumb-tagged vtable pointer to an adjusting thunk at 0x25670, which jumps backward to the actual body starting at 0x25634; the state-setting instruction range 0x2565c..0x2566a is therefore correctly within the body. Historical source says `HandleHttpError` sets `iLoadNodeState=EFailed`, copies HTTP error, and calls `RunOperation` [lines 442–465](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/server/src/ncdloadnodeoperationimpl.cpp#L442-L465).
3. Continue without any synthetic phone trials, private-cache modifications, firmware writes or executable uploads. PR remains docs-only, draft, unmerged. **No live E7 callback path has been traced.**

## Owner LLVM resolved HTTP observer adjustment thunk and EFailed tail (12 October 2026)

The owner ran independent `llvm-objdump-19 -D --triple=thumbv5te-none-eabi` against the previously SHA256-verified analysis-only Nokia NCD server ELF, in ranges **0x27320–0x27348** and **0x25630–0x256a0**. These observations explain the apparent method-entry mismatch between the older vtable-audit address and the body that stores the HTTP error and `EFailed` state.

**Confirmed adjusting-thunk relationship:**

```asm
25670: subs r0, #0xf4     ; adjust this for secondary MCatalogsHttpObserver interface
25672: b    0x25634       ; branch into actual HandleHttpError body
25634: push {r4,r5,r6,lr}
...
2564e: ldr  r1, [r0]     ; virtual method dispatch follows
25650: ldr  r1, [r1,#4]
25652: blx  r1           ; operation Release(), historically
25654: movs r0, #0xff
25656: movs r1, #0
25658: adds r0, #0x2d
2565a: str  r1, [r0,r4] ; clear pointer at this+0x12c, consistent with iTransaction=NULL
2565c: movs r1, #5
25660: str  r5, [r4,#0x30] ; store HTTP error as iError
25662: str  r1, [r0,r4]    ; EFailed at this+0xfc (r0 reset at 2565e)
25664: ldr  r0, [r4]
25666: ldr  r1, [r0,#0x6c]
25668: movs r0, r4
2566a: blx  r1           ; vtable RunOperation() entry
2566c: movs r0, #1       ; return ETrue
2566e: pop  {r4,r5,r6,pc}
```

The actual vtable entry **0x25671** has Thumb bit set and dispatches to the thunk at **0x25670**, which subtracts **0xf4** from `this` then branches to the *earlier* implementation at **0x25634**. Hence the earlier V20 vtable/body addresses were **both correct**: there was no impossible source-order, only a secondary-interface C++ thunk. `0x25630` is the tail of an adjacent thunk for another HTTP observer method; `0x25674` begins another function, not the error handler. This confirms the actual compiled Belle `HandleHttpError` shape matches [Nokia source, lines 442–465](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/server/src/ncdloadnodeoperationimpl.cpp#L442-L465), not just static source expectations.

**Confirmed ordinary `EFailed` shared exit:**

```asm
27320: movs r0, r4
27322: bl   0x24e12
27326: b    0x26d2e
```

Both normal EFailed entry paths (pending IPC null and after sending ID 3) converge on the call **0x24e12** with the server operation as `this`. Historically this corresponds to the inherited **`CNcdBaseOperation::CompleteCallback()`**, which [iterates server observers](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/server/src/ncdbaseoperation.cpp#L973-L979). **Exact target at 0x24e12 still needs function-body verification** before its identity can be called independently confirmed. Crucially, a *server observer callback* does not itself guarantee an IPC error was delivered to the *client proxy*.

**Boundary:** the full *static* client notification pipeline's major branch shapes are independently corroborated, but we have **no phone-side evidence** that the live E7's HTTP 404 reached this handler, nor any observed `iPendingMessage`, client `CompleteCallback`, or IAUpdate outstanding-operation count. The synthetic ELF omits data/relocation/import semantics. This is not proof of a phone-side deadlock or a fixed update service.

**Next owner-only offline probe:** disassemble the bounded **0x24e12–0x24e90** server callback code and **0x12220–0x12310** NCD proxy base completion dispatcher with LLVM Thumbv5TE. Compare the first to [`CNcdBaseOperation::CompleteCallback`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/server/src/ncdbaseoperation.cpp#L973-L979), and the second to [`CNcdBaseOperationProxy::HandleCompletedMessage`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/client/src/ncdbaseoperationproxy.cpp#L269-L330), specifically completion ID 3 versus ID 4. Avoid assuming all decoded bytes within these arbitrary windows are a single function.

No handset experiments, source-image change, executable or firmware-file upload to GitHub, or change to `main`. Draft PR remains docs-only and unmerged.

## Actual offline local static results, not yet a Sanctuary Ghidra test

Ran `python3 -m py_compile`, **8/8** local converter tests, and `readelf` and LLVM disassembly checks against the four previously archived owner-provided flattened images, verifying their SHA256 identities and code preservation:

| E32 owner archive | Code-section bytes | Generated analysis ELF SHA256 | Confirmed Thumb labels |
| --- | ---: | --- | ---: |
| `iaupdate.exe.flat.bin` | 56,544 | `fb71ccd263464a133b5e22c01080651d154bae01cf4eab23ddb49310d00fec02` | 1 |
| `iaupdateengine.dll.flat.bin` | 62,780 | `c148868d92d698124f04d68b88603e4682a076e2b71c9dc462e681ba37315e89` | 5 |
| `ncdproxy_20019119.dll.flat.bin` | 180,476 | `95e97a93f2a1a69e62876c699df22cfd9cb6cf6a1c578d7f3163339c93d53c07` | 4 |
| `ncdserver_20019119.exe.flat.bin` | 449,512 | `e81c6fe132922455bff8addb691f342e45be026623c0f5aa6dd53e57593f215d` | 3 |

All constructed ELF headers reported **ELF32, Machine ARM, EABI5**, one RX LOAD starting at virtual `0x8000`, and code bytes equal to the E32 header-specified section. The known `CIAUpdateLoader::OperationComplete` function at **`0x9e7e`** disassembles under LLVM's Thumbv5TE triple to `push {...,lr}`, `sub sp,#8`, `movs r5,r0`, etc. `CNcdLoadNodeProxy::HandleCompletedMessage` at `0x1297c` and `CCatalogsHttpStack::MHFRunL` at `0x1028c` likewise decode as expected Thumb entries.

No REA/Ghidra import of a **generated Nokia ELF** has been demonstrated yet. The next owner-operated, **offline and host-only** test is to locate their preserved `iaupdateengine.dll.flat.bin` on Sanctuary and run the separate utility, then:

```sh
source ~/opt/e7-rea-env.sh
mkdir -p -m 0700 ~/Downloads/e7-rea-elf-work
python3 ~/Downloads/e7_make_ghidra_elf.py \
  --input /ACTUAL/PATH/iaupdateengine.dll.flat.bin \
  --output-dir ~/Downloads/e7-rea-elf-work

ELF=~/Downloads/e7-rea-elf-work/iaupdateengine.dll.flat.bin.analysis.elf
readelf -h -l -s "$ELF"
npx -y rea-agents@6.4.0 analyze "$ELF" --provider ghidra --json
```

Once import and section/language mapping are validated, the **next** research method is `CIAUpdateLoader::OperationComplete`, expected normalized Thumb entry `0x9e7e` (symbol stored with low-bit `0x9e7f`). If Ghidra reports ARM instead of Thumb, wrong address mappings, or a method not matching the audited entry bytes, **stop rather than trust the decompiler**. The converter itself was tested on the authoring host, **not executed by the E7 owner on Sanctuary yet**.

No source E32 blobs, compiled ELF envelopes, private path inventory, HTTP requests or runnable Nokia code were committed; the earlier draft PR remains docs-only, unmerged and does not modify `main`.
