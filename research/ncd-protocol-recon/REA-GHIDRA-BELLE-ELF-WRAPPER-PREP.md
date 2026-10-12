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
