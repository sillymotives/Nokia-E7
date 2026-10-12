# Belle NCD client/server completion handshake: code-level evidence

**11 October 2026. Offline static forensics only. No E7 runtime trace or filesystem/cache changes.**

## Finding

The owner supplied four expanded analysis-only E32 firmware images and their `e7-bytepair-summary.json`. Their flat-image SHA256 checksums were independently verified, along with their `EPOC` headers. We recovered Thumb instructions for two NCD classes and checked the C++ RTTI, primary vtables, virtual dispatch offsets, and original Nokia enum definitions.

**The real Belle server and client implement the same two-phase NCD node-load completion handshake seen in the historical code:**
- Server sends **completion ID 5** (`ENCDOperationMessageCompletionNodesUpdated`) when it has loaded-node metadata to report.
- Client receives ID 5 and dispatches its inherited **`SendContinueMessageL`** function, issuing an asynchronous **function ID 3** (`ENCDOperationFunctionContinue`) if not already active.
- Server, when no loaded-node records remain and a pending client message exists, sends **completion ID 4** (`ENCDOperationMessageCompletionComplete`) and marks its operation complete.
- Separate client error/progress callbacks and a server error path exist.

These are **compiled code-path facts**, not proof these branches were reached in the v0.14.4 physical trial. The root cause of the spinning/blank E7 update screen remains unknown.

## Original Nokia source definitions

The historical [`ncdoperationfunctionids.h`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/client/inc/ncdoperationfunctionids.h#L25-L58) explicitly defines:
- `ENCDOperationFunctionContinue = 3`
- `ENCDOperationMessageCompletionError = 3`
- `ENCDOperationMessageCompletionComplete = 4`
- `ENCDOperationMessageCompletionNodesUpdated = 5`

The relevant source routines are [`CNcdLoadNodeOperationProxy::HandleCompletedMessage`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/client/src/ncdloadnodeoperationproxy.cpp#L258-L306), [`CNcdBaseOperationProxy::SendContinueMessageL`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/client/src/ncdbaseoperationproxy.cpp#L392-L418), and [`CNcdLoadNodeOperationImpl::DoRunOperationL`'s `EComplete` path](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/server/src/ncdloadnodeoperationimpl.cpp#L2239-L2305). The older source explicitly notes that the non-suboperation **waits for another proxy message before completing**.

## Binary provenance and conventions

Both images have E32 codebase `0x8000` and code section offset `0x9c`. Below, Thumb virtual addresses are **pre-relocation E32 addresses**; the code-section offsets are derived by subtracting `0x8000`. These are **not actual process addresses observed on the handset**.

| Binary | Actual owner-provided flat-image SHA256 | E32 UID3 |
| --- | --- | --- |
| `ncdproxy_20019119.dll` | `09994060128754da1fe0bcfb6ce4c4766c8607eb978fc96768f623f9d9afda38` | `0x20019116` |
| `ncdserver_20019119.exe` | `c26fc0dea62a0a1a3a26e6bf387ad6dca78a581a7214fb8fc11d8748b407baa5` | `0x20019119` |

Disassembly used `llvm-objdump` v17 with `--triple=thumbv5te-none-eabi` on a **synthetic analysis-only ELF object** containing the unchanged E32 code-section bytes. The firmware was **not** executed. The other two owner-supplied IAUpdate flat binaries were also independently SHA256-verified against the summary.

## Compiled NCD proxy evidence

The C++ RTTI name `26CNcdLoadNodeOperationProxy` resolves through the primary virtual-table header at flat offset `0x28be0`, with RTTI at `0x239d8`.

| Slot | Thumb address | Code-section offset | Identified function |
| ---: | --- | --- | --- |
| 9 | `0x1297d` | `0xa97c` | `HandleCompletedMessage` |
| 10 | `0x12389` | `0xa388` | inherited `SendContinueMessageL` |
| 12 | `0x12a23` | `0xaa22` | `ProgressCallback` |
| 14 | `0x12b55` | `0xab54` | `CompleteCallback` |

The base proxy's separate primary table (`0x1c48c`) has a **different** slot 9 (base handler, `0x12221`) but the **same** slot 10 (`0x12389`), supporting the derived override/inherited Continue mapping.

The compiled handler compares the incoming ID against **5** at code `+0xa986`, dispatches virtual offset `+0x28` (slot 10) after handling updated nodes, and dispatches `+0x30` (slot 12) or `+0x38` (slot 14) on progress/error paths. The continuation routine checks active state and uses **async function ID 3** at `+0xa3d0`. The `CompleteCallback` at `+0xab54` has the expected observer-iteration and virtual-callback shape.

## Compiled NCD server evidence

The C++ RTTI name `25CNcdLoadNodeOperationImpl` resolves through the primary virtual-table header at flat offset `0x64460`, with RTTI at `0x5d044`.

| Slot | Thumb address | Code-section offset | Identified function |
| ---: | --- | --- | --- |
| 20 | `0x2551d` | `0x1d51c` | `CompleteMessage` overload (simple completion) |
| 21 | `0x2553f` | `0x1d53e` | `CompleteMessage` overload (error) |
| 22 | `0x2555d` | `0x1d55c` | `CompleteMessage` overload (node list) |
| 27 | `0x273b3` | `0x1f3b2` | `RunOperation` |

The base `CNcdBaseOperation` table at `0x61d2c` has a placeholder at slot 27, while the derived class supplies real code. Derived `RunOperation` branches into the large state-machine routine at code `+0x1ee94`, just as the historical `RunOperation → DoRunOperationL` relationship requires.

In the actual state machine, code `+0x1f32c` checks the pending client-message pointer. Code `+0x1f348` sends **ID 5** through the node-list `CompleteMessage` virtual slot `+0x58`. Code `+0x1f378` sends **ID 4** through the simple `CompleteMessage` slot `+0x50`, and code `+0x1f384` writes complete-state value 4. The wrapper's separate failure path dispatches **ID 3 (`Error`)**. This ordering and these constants match the historical `EComplete` case.

## Methodology, limitations and next target

The selected RTTI names, offset-to-top zeroes, typeinfo pointers, vtable entries, and key Thumb halfwords (ID compares, dispatch slot loads, state stores) were checked **directly against the uploaded byte streams**. Both relevant binaries were independently disassembled; no method identity is based solely on a nearby unreferenced class-name string.

**Still unproven:** Whether the E7's child HTTP transaction reached `ECatalogsHttpOpCompleted`, whether `ParseCompleteL` ran, whether ID 5 was ever emitted, whether Continue IPC reached the server, whether final Complete/IAUpdate `LoadComplete` fired, or why the E7 remained spinning with a blank list. This is **static correspondence**, not a runtime trace or a diagnosis of a broken callback.

**Next offline boundary:** Correlate Belle's compiled HTTP completion handler and NCD parser-completion method with the historical [`HandleHttpEventL` and `ParseCompleteL`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/server/src/ncdloadnodeoperationimpl.cpp#L395-L533). Another synthetic catalogue revision, real SIS installation, private-cache cleanup or widening of E7 Bridge permissions is not justified.

**GitHub scope:** Research documentation only; owner-supplied E32 images and disassembly objects remain private, and no runnable code was committed. PR stays draft, unmerged, and `main` unchanged.
