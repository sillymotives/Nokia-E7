# Nokia E7 Belle: HTTP completion to asynchronous NCD parser (11 October 2026)

**Static evidence only, not a device callback trace.** The owner-provided actual Belle flat E32 images were inspected offline and matched their SHA256 entries in `e7-bytepair-summary.json`. No E7 network access, installer, firmware execution, cache changes, or responder edits occurred.

The actual Belle `ncdserver_20019119.exe` implements the historical Nokia path:
`CCatalogsHttpTransaction::RequestCompleted -> DoRequestCompletedL -> NotifyObserver -> CNcdLoadNodeOperationImpl::HandleHttpEventL -> MNcdParser::{ParseL, EndL} -> CNcdParserImpl::{EndL, RunL} -> CNcdLoadNodeOperationImpl::ParseCompleteL -> ContinueOperationL`. Later `NodesUpdated (5) -> Continue IPC (3) -> Complete (4)` was covered in [the earlier direct Thumb audit](V14-4-BELLE-CONTROLFLOW-AUDIT.md).

## Grounding

Analyzed flattened E32 image: `ncdserver_20019119.exe.flat.bin`, SHA256 `c26fc0dea62a0a1a3a26e6bf387ad6dca78a581a7214fb8fc11d8748b407baa5`, UID3 `0x20019119`, E32 code base `0x8000`, code file offset `0x9c`. Addresses below are **code-section-relative** and **pre-relocation**, not runtime handset addresses. LLVM 17 inspected unchanged code-section bytes in an analysis-only ELF, without executing Nokia firmware. An assertion script cross-checked all four uploaded SHA256 digests, RTTI/vtables, instruction halfwords, and branch/slot relations. Its final run reported **zero failures**.

### Transport to HTTP observer

The RTTI-linked `CCatalogsHttpTransaction` has an `MCatalogsHttpStackObserver` secondary virtual table at flattened offset `0x641b0` (adjustment `-8`); slot 4 is `RequestCompleted` (thunk at code `+0x78da`, real routine `+0x784c`). The success path in `DoRequestCompletedL` at code `+0x77b0` writes HTTP operation **state 4** at `+0x77f6` (`ECatalogsHttpOpCompleted`) and progress **16** at `+0x77fa` (`ECatalogsHttpDone`), then calls `NotifyObserver` at `+0x7528`. Observer virtual slot 0 is invoked at `+0x7548`; the source calls this `HandleHttpEventL`. Error handling takes a distinct path.

Source: [historical HTTP transaction](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/engine/transport/src/catalogshttptransaction.cpp#L752-L890), [operation/progress enum](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/engine/transport/inc/catalogshttptypes.h#L33-L225).

### NCD HTTP handler to parser

`CNcdLoadNodeOperationImpl`'s `MCatalogsHttpObserver` secondary vtable at flattened offset `0x645a0` (adjustment `-0xf4`) points to `HandleHttpEventL` thunk `0x25631` at code `+0x1d630`, entering the method at `+0x1d5a6`. The actual instructions:
- code `+0x1d5ea`: `cmp r6,#1`, the **InProgress** operation-state branch;
- code `+0x1d5f0`: `cmp r6,#4`, the **Completed** state branch;
- code `+0x1d614`: `cmp r0,#10`, the **ResponseBodyReceived** progress event;
- code `+0x1d626`: parser virtual offset `+0x24`, **ParseL(response body)**;
- code `+0x1d60a`: parser virtual offset `+0x2c`, **EndL()** on HTTP completion.

See [historical load-node HTTP handler](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/server/src/ncdloadnodeoperationimpl.cpp#L395-L432).

### Actual asynchronous parser

`CNcdParserImpl` RTTI (`0x64298`) resolves to the `MNcdParser` secondary vtable at flattened offset `0x6162c` (adjustment `-0x1c`). Interface slot 9 is `ParseL(const TDesC8&)` (target `0x43a7f`, actual code `+0x3ba32`); slot 11 is `EndL()` (target `0x43ae5`, actual code `+0x3baa6`). The actual `EndL` checks whether parsing is synchronous or asynchronously idle with an empty buffer. When ready, it calls XML `ParseEndL`, tests cancellation, and dispatches the parser-complete observer. Otherwise it sets a deferred-finish flag at code `+0x3bade..+0x3bae0`. The parser active-object `RunL` at `+0x3b8b8` checks this flag after input-buffer exhaustion and dispatches `EndL` via its own virtual table. Thus an asynchronous parser can remain locally pending without further HTTP packets, but **we have not observed this on the E7**.

See [historical parser EndL, ParseL and RunL](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/protocol/src/ncdparserimpl.cpp#L173-L332).

### Node parse-complete callback

The `MNcdParserObserver` vtable at flattened offset `0x64578` (adjustment `-0xec`) identifies slot 1 `ParseCompleteL`: thunk `0x25721` -> actual code `+0x1d6d2`. The compiled method handles a nonzero error by selecting state **EFailed=5** (`+0x1d6de`). With no error it checks pending queries, then remote folders. Remote folder work selects **ERemote=2** (`+0x1d710`); otherwise it selects **EComplete=4** (`+0x1d71c`), stores state at `+0x1d712`, and continues the operation. These are *possible control-flow branches*, not proof of pending queries or remotely loaded folders on the user's phone.

See [historical ParseError / ParseCompleteL](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/server/src/ncdloadnodeoperationimpl.cpp#L464-L535).

## Physical and host-test boundary

The unchanged v0.14.4 host response code uses HTTP/1.1, emits exact `Content-Length`, `Connection: close`, and `close_connection=True`. **The hypothesis that the host accidentally omitted content length or deliberately held its socket open is not supported by this static check.** Host socket writes alone do *not* confirm `RequestCompleted(KErrNone)` on the handset, `EndL()`, `ParseCompleteL`, child-load completion, the NCD continuation IPC, or IAUpdate's UI refresh. V0.14.4 still spun forever and left a blank update directory. The previously reported 30-second zero-packet capture lacks a same-session known-good control.

The narrowed unknowns are (1) child transport successful completion, (2) NCD observer/end-of-input dispatch, (3) asynchronous parser drain and callback, (4) queries/remote folders and `NodesUpdated/Continue/Complete`, (5) final IAUpdate loader/UI callback. **Static method recovery cannot distinguish which runtime stage was missed.**

**Safe next investigation:** host-only tracing of `CCatalogsHttpStack`'s conditions for invoking `MCatalogsHttpStackObserver::RequestCompleted`, or read-only handset diagnostics if an appropriate legitimate method exists. Do not rearm synthetic NCD responses, introduce a real SIS, clear private caches or widen bridge permissions based on this audit alone.

Full sanitized report was delivered privately as `e7-belle-http-parser-completion-audit-20261011.md`; **no extracted firmware bytes or disassembly objects committed**. This PR is documentation-only and remains draft/unmerged, with `main` untouched.
