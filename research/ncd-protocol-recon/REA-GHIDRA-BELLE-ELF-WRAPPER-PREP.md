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
