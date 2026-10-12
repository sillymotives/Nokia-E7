# E7 Belle: compiled NCD HTTP terminal events and timeout gap

**11 October 2026. Offline forensic evidence only. Not a physical E7 runtime trace. No phone, server, install, private cache or firmware changes.**

## Confirmed behavior of actual Belle NCD HTTP stack

The owner's analysis-only, expanded `ncdserver_20019119.exe.flat.bin` (SHA256 `c26fc0dea62a0a1a3a26e6bf387ad6dca78a581a7214fb8fc11d8748b407baa5`) contains the real C++ `CCatalogsHttpStack` RTTI and code-backed `MHTTPTransactionCallback` vtable. Its `MHFRunL` method uses the same event semantics as [Symbian HTTP `THTTPEvent`](https://github.com/SymbianSource/oss.FCL.sf.mw.netprotocols/blob/cc43765893d358f20903b5635a2a125134a2ede8/applayerprotocols/httptransportfw/inc/http/thttpevent.h#L111-L164):

| HTTP event | ID | Byte-verified Thumb method target (code-section relative) | Outcome |
| --- | ---: | --- | --- |
| EGotResponseHeaders | 4 | `+0x82ac` | Process headers/status |
| EGotResponseBodyData | 5 | `+0x838a` | Pass body; rearm NCD timeout |
| **EResponseComplete** | **6** | **`+0x8386`** | **Return, without notifying RequestCompleted or rearming timeout** |
| EGotResponseTrailerHeaders | 7 | `+0x841a` | Other-event branch |
| **ESucceeded** | **8** | **`+0x83e4`** | **Call observer RequestCompleted(KErrNone), except if special error header seen** |
| EFailed | 9 | `+0x8408` | Call observer RequestCompleted(error) |

**How verified:** Four actual E32 hashes and `EPOC` signatures independently matched owner-supplied `e7-bytepair-summary.json`. `CCatalogsHttpStack` RTTI at `0x5c728` points to code-backed `MHTTPTransactionCallback` secondary vtable at flat offset `0x62298`, offset-to-top `-28`. The MHFRunL target is Thumb `0x1048d` with an adjusting thunk into code `+0x828c`. Thumb code at `+0x82a0` invokes ARM switch helper at `+0x4f634`; that helper is precisely `ldrb r12,[lr,#-1]`, `cmp r3,r12`, `ldrblo`, `ldrbhs`, `add r12,lr,r3,lsl #1`, `bx r12`. The following switch bytes at `+0x82a4` are `06 04 73 71 bb a0 b2 bb`. Computing the branch destinations from these bytes yields the event targets listed above. The event-6 case lands directly on the function epilogue (`+0x8386`: `add sp,#0x44; pop {...,pc}`). Event-8 calls the observer's virtual slot `+0x10` at code `+0x8404`; event-9 has a distinct error dispatch.

## Narrow potential wait: a cancelled timer without a terminal event

At MHFRunL entry (`+0x8294`), the binary calls imported `CActive::Cancel`, corresponding to historical `CancelTimeoutTimer()`. The body event calls `SetTimeoutTimer()` at code `+0x80a8`, which in turn cancels the previous timeout, schedules a new timeout with the compiled literal **60,000,000 microseconds (60 s)**, records timer-active state, and calls `SetActive()`. `EResponseComplete` dispatches directly to the epilogue and **does not rearm this NCD wrapper timeout**.

Therefore **if** Belle's HTTP framework reports `EResponseComplete` but fails to issue its expected terminal `ESucceeded` or `EFailed`, the wrapper could be left with neither a pending NCD timeout nor the `RequestCompleted` notification that lets the parser call `EndL`. This is a source- and firmware-backed **possible failure mechanism**, not an observation of the actual handset. The [Symbian event header](https://github.com/SymbianSource/oss.FCL.sf.mw.netprotocols/blob/cc43765893d358f20903b5635a2a125134a2ede8/applayerprotocols/httptransportfw/inc/http/thttpevent.h#L109-L116) states a final `ESucceeded` **or** `EFailed` should always be delivered; a failure to deliver either would be exceptional. Other HTTP-framework watchdogs, NCD asynchronous parser waits, queued node operations, IPC continuations and the IAUpdate callback chain have not been ruled out.

Source links: [Nokia `CCatalogsHttpStack::MHFRunL`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/engine/transport/src/catalogshttpstack.cpp#L469-L805); [`SetTimeoutTimer` and `CancelTimeoutTimer`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/engine/transport/src/catalogshttpstack.cpp#L938-L1030); [60-second timeout constant](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/engine/transport/inc/catalogshttpstack.h#L27-L34).

## Responder and inference boundary

The unmodified v0.14.4 host `V09Handler.reply()` advertises `Content-Length` and `Connection: close`, calls `end_headers()`, sets `close_connection=True`, and does **not** emit Nokia's special `catalogs-client-error-number` header. The compiled HTTP handler compares to catalog-error sentinel **1234** on its success branch, but that header was never supplied by the synthetic host. So an obviously missing length header, intentionally persistent host socket, or explicitly flagged Nokia catalog-error header is **not supported by host source**. A completed server socket write still gives **no proof** that the E7 actually received `EResponseComplete`, terminal success/failure, the NCD parser callback, or IAUpdate `LoadComplete`.

The physical v0.14.4 observation remains: configuration/root/child server socket writes completed, the E7 spinner persisted, and the post-exit directory was blank. Its zero-packet 30-second passive summary lacked a same-session known-good capture. **Do not infer actual terminal-event loss from these facts.**

## Verification and next boundary

An offline assertion script was run against the real owner-provided flat E32 files: **all checks passed** for the four fingerprints, RTTI/vtables, ARM dispatch helper, Thumb case targets and instruction values, 60-second timer literal, and original v0.14.4 host reply framing. A sanitized, more detailed Markdown copy is provided privately to the owner; neither the ROM nor executable code are committed to this documentation-only PR.

Next genuinely discriminating evidence would be whether the **physical E7's child HTTP transaction** emitted its final success/failure event. Existing E7 Bridge can collect process names, not private HTTP/NCD event traces. A separately considered, known-good-controlled packet capture could test on-wire TCP completion but could **not** observe `THTTPEvent` inside Symbian. No new SIS, HTTP responder, cache reset, binary patch, extra phone trial, merge, or deployment is proposed.
