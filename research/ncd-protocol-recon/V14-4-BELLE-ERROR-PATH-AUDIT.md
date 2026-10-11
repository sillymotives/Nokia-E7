# Nokia E7 Belle: HTTP timeout windows and normal error propagation

**11 October 2026 | Offline static audit only.** No E7 access, no network responder, no cache change, no package installation, and no merge to `main`. These are possible machine-code paths, **not observed E7 events**. The still-spinning v0.14.4 physical result remains undiagnosed.

## What is newly established

The prior [terminal-event audit](V14-4-BELLE-HTTP-TERMINAL-AUDIT.md) correctly proved that `EResponseComplete` (6) does not itself complete NCD HTTP transport. This follow-up finds that the wrapper's **header event (4) also has no direct timer rearm**; and verifies that ordinary transport/parse errors have explicit routes into NCD's failure state, rather than inherently leaving the request pending.

The actual Belle `CCatalogsHttpStack::MHFRunL` cancels its 60-second NCD timeout **at entry for every event**. Its switch then behaves as follows (code offsets relative to E32 code section, **not runtime addresses**):

| `THTTPEvent` | ID | Actual handler offset | NCD-wrapper timer / completion |
| --- | ---: | --- | --- |
| `EGotResponseHeaders` | 4 | `+0x82ac` | Timeout cancelled on entry; status/header callbacks, **no direct SetTimeoutTimer() call** in this case |
| `EGotResponseBodyData` | 5 | `+0x838a` | For a normal 200-206 response with observer, passes body and calls `SetTimeoutTimer()` at `+0x83de` |
| `EResponseComplete` | 6 | `+0x8386` | Direct epilogue; **neither timer rearm nor RequestCompleted** |
| `ESucceeded` | 8 | `+0x83e4` | Calls observer's `RequestCompleted(KErrNone)`, except for Nokia's special catalogue error header |
| `EFailed` | 9 | `+0x8408` | Calls observer's `RequestCompleted(iLastError)` (an error path at the transaction layer) |

**Consequence:** If the HTTP framework stops producing events *after response headers but before a body or terminal event*, the NCD wrapper timer may already be cancelled. Likewise, after `EResponseComplete` there is no further wrapper timeout if a terminal event is never delivered. These are **conditional timeout gaps**, not evidence that the firmware framework failed in the live trial. Other HTTP/protocol watchdogs remain possible. The [Symbian HTTP event contract](https://github.com/SymbianSource/oss.FCL.sf.mw.netprotocols/blob/cc43765893d358f20903b5635a2a125134a2ede8/applayerprotocols/httptransportfw/inc/http/thttpevent.h#L108-L156) explicitly says exactly one final `ESucceeded` or `EFailed` will always be delivered. Absence of both would be exceptional.

One additional ordering detail: the successful body branch calls the body observer first, conditionally releases data when `iRunning` remains true, **then** rearms the timeout (compiled branch at `+0x83cc..+0x83e0`). Synchronous observer cancellation can thus change the release-data path while the timer rearm site remains reachable. This is a static control-flow nuance **not evidence of cancellation, a dangling object, or a spinner cause**.

Source comparison: [`CCatalogsHttpStack::MHFRunL`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/engine/transport/src/catalogshttpstack.cpp#L469-L779), [timer methods](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/engine/transport/src/catalogshttpstack.cpp#L937-L1030).

## Actual Belle failure handling, not just older source

All methods below were cross-checked against the same owner's decompressed `ncdserver_20019119.exe.flat.bin` (SHA256 `c26fc0dea62a0a1a3a26e6bf387ad6dca78a581a7214fb8fc11d8748b407baa5`); E32 UID3 `0x20019119`, file code offset `0x9c`, code base `0x8000`, code length `449512`. Thumb pointers include their low-bit indicator. The binaries were **not executed**.

| Belle callback/error route | Compiled evidence | Interpretation and limit |
| --- | --- | --- |
| `CCatalogsHttpStack::MHFRunError` | Actual `MHTTPTransactionCallback` secondary vtable at flat `0x62298`: slot 1 `0x104a3`, thunk to routine `+0x8490`. Checks observer at `+0x8492`; invokes observer virtual slot `+0x10` at `+0x849c`; returns 0 at `+0x849e`. | A caught `MHFRunL` leave reports `RequestCompleted(error)` **when an observer is present**. Does not prove that a leave happened or that later completion succeeded. |
| `EFailed` and negative HTTP events | `+0x8408` closes and invokes observer via `+0x8454`; negative default event takes `+0x8484` then the observer failure path. | Normal explicitly reported transport failures need not hang silently at the HTTP wrapper. They can still hit downstream problems. |
| `CNcdLoadNodeOperationImpl::HandleHttpError` | `MCatalogsHttpObserver` secondary vtable flat `0x645a0`, slot 1 `0x25671` (adjusting thunk `+0x1d670` to method `+0x1d634`). Writes `EFailed=5` and error around `+0x1d65c..+0x1d662`, invokes virtual operation processing at `+0x1d66a`. | An NCD HTTP error has an explicit state-machine failure path. It conditionally marks a content source broken and releases the transaction. |
| `CNcdLoadNodeOperationImpl::ParseError` | `MNcdParserObserver` secondary vtable flat `0x64578`, slot 0 `0x256cf` (thunk `+0x1d6ce` to method `+0x1d674`). When receiving and not already handling an error, stores `EFailed=5` at `+0x1d686`, records error, optionally cancels transaction and advances via the trapped continuation call at `+0x1d6aa`. | A parser error is not intrinsically a silent pending state; handling is conditional on operation state, and later callbacks still matter. |
| `CNcdLoadNodeOperationImpl::ParseCompleteL(nonzero error)` | Compiled branch `+0x1d6de` sets `EFailed=5` and advances the operation. | Explicit parser-finished-with-error is distinct from **parser never finished**. |

Historical implementation correlates with [NCD load-node HTTP, parse-error and parse-complete callbacks](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/server/src/ncdloadnodeoperationimpl.cpp#L395-L535) and [`CCatalogsHttpTransaction::RequestCompleted/DoRequestCompletedL`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/engine/transport/src/catalogshttptransaction.cpp#L791-L890). The direct Belle [HTTP-to-parser audit](V14-4-BELLE-HTTP-PARSER-AUDIT.md) separately establishes that **success**, not merely response-body receipt, calls parser `EndL()`.

## What this does and does not discriminate

1. **More strongly characterized, not confirmed:** A missing or indefinitely deferred *terminal child HTTP event* can escape this NCD wrapper's timeout, including a header-only gap. The HTTP framework promises a terminal event, so do not assume such loss is routine.
2. **Less compelling as a standalone spinner explanation:** An ordinary HTTP `EFailed`, negative framework error, or parser's delivered nonzero error normally enters a failure-notification path. If the spinner persists because of an error, a subsequent operation/IPC/UI completion may also have failed.
3. **Still open:** A child transport completion not delivered to NCD; parser `EndL` never invoked or asynchronous parser never draining; `NodesUpdated`/`Continue` handshake remaining pending; an IAUpdate load operation that never reports completion; or an omitted UI `RefreshComplete` callback.
4. **Observed only at the host:** v0.14.4 wrote configuration/root/child HTTP 200 responses on its sockets, but the handset continued spinning and the post-exit list was blank. The verified v0.14.4 ZIP SHA256 `54e38730adbcac4d9b23d54333d432b03d17d04f2ef78f1a2e452b71cdc1881e` contains an `HTTP/1.1` responder with `Content-Length`, `Connection: close`, `end_headers()` and `close_connection=True`. This rules out an *intentionally* lengthless or keep-alive response in host source, **not** downstream reception or callback loss.
5. **Not discriminating:** A prior post-response 30-second zero-packet Wi-Fi summary lacked a same-session known-good control and cannot show an internal Symbian HTTP/parser/IPC event.

## Verification and disposition

Owner-supplied four flat E32 images were recovered privately and **all four SHA256 digests matched** `e7-bytepair-summary.json`; EPOC headers and relevant RTTI/vtable pointers matched. A private host-only verifier asserted **37 of 37** independent expected digest/header/table/instruction facts. An LLVM 17 Thumb disassembly of an *analysis-only ELF wrapper* confirmed the listed branch targets; the ARM switch-table event mapping was previously independently established. The offline verifier, synthetic ELF, extracted ROM and binary bytes are **not committed**. These are static checks, **not 37 runtime tests**.

**Stop condition:** no more synthetic HTTP request, package/URI, altered SISX identity, E7 Bridge privilege change, protected cache reset or physical check on this evidence alone. Current E7 Bridge does not see NCD private parser state or HTTP terminal callbacks. The next truly decisive information would be a legitimate read-only **device-side event/completion trace** covering child transport, parser, proxy IPC and UI refresh. Until available, retain multiple conditional causes and do not diagnose the real handset by inference.

**PR policy:** documentation-only draft, `main` unchanged, no firmware or runnable responder committed, and E7 untouched.
