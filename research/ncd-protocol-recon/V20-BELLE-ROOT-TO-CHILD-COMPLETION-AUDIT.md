# Belle E7: root-folder processing to child-load completion, compiled-path audit

**12 October 2026. Entirely offline. No new E7 check, network responder, installation, writable cache access or firmware execution.**

## Main finding: revise the root-wait hypothesis

In the owner's **v0.19** physical test the host wrote:

1. Exact original v0.14.5 configuration HTTP 200 (751-byte XML).
2. Exact original v0.14.5 root HTTP 200 (566-byte XML with two `FolderRef` elements, one `FolderData`).
3. An **empty HTTP 404** for the recognized `offline-root` child metadata browse.

Sanctuary recorded the three completed socket writes and no handler failure. **The E7 spinner persisted.** Contrast **v0.20**, which kept the exact configuration 200 but answered root browse with **HTTP 200, Content-Length 0**: the E7 spinner **stopped** and displayed the ordinary unable-to-check error. That server was manually stopped with Ctrl+C, so there is no evidence for automatic post-browse window expiry. None of these server-local receipts proves E7 HTTP receipt, parse completion, NCD IPC completion or cache safety.

A new code-level implication matters: **the third `offline-root` metadata browse in v0.19 is more consistent with successful progression *past* the initial root load than with that root operation remaining stuck.** Under historical Nokia's IAUpdate loader, `NodesUpdated` is a *no-op*; it cannot schedule a child browse. Only the loader's `OperationComplete` / `NextLoadLoopL` path initiates further children loading after a root operation. The owner-provided actual Belle DLL contains the same dispatch and branch structure.

This is a **strong conditional inference, not a direct phone-side callback trace**. An unexpected concurrent/cached operation or implementation difference could conceivably produce a similar request. Do not claim that root `NodesUpdated/Continue/Complete` was positively observed. But **root-initial-completion** now ranks below **post-root child/error completion or another outstanding loader operation** as the place to investigate.

## Actual firmware and fixture verification

One purpose-built **read-only verifier** ran locally and passed **54/54** assertions, covering:

- Exact SHA256, EPOC header and expanded byte count for all four archived owner-supplied E32 images: `iaupdate.exe`, `iaupdateengine.dll`, `ncdserver_20019119.exe`, `ncdproxy_20019119.dll`.
- Vtable/Thumb method targets and selected instructions in the compiled actual Belle IAUpdate loader, NCD parser observer, NCD error path and NCD proxy.
- Exact v0.14.5 response SHA256s and XML structure, the v0.9 empty browse baseline, and existing v0.12/v0.13 `FolderRef` fixtures.

The checks use `0x9c` E32 code-file offset and `0x8000` image code base; below addresses are **code-section-relative** (not runtime addresses). The tool only reads local binaries and Python response fixtures; no raw firmware, ELF analysis object, runnable responder, test script, request body or device identifier was committed.

## Finding A: actual Belle CIAUpdateLoader ignores NodesUpdated

Actual `iaupdateengine.dll.flat.bin`, SHA256 `f395e88a078d6837823e169c1209d6ad295dad242ef5564b144c97584ec5ab99`:

- Observer `MNcdLoadNodeOperationObserver` secondary virtual table at flattened `0xcf64`, `this` adjustment `-4`, typeinfo `0x13d64`.
- Slots **0, 1, 2** are Thumb `0x9d9f`, `0x9e25`, `0x9fa3`, matching `NodesUpdated`, `QueryReceived` and `OperationComplete` in [historical `CIAUpdateLoader`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/iaupdate/IAD/engine/controller/src/iaupdateloader.cpp#L270-L420).
- **Slot 0 points to actual Thumb code offset `+0x1d9e`: a single `bx lr` (`0x4770`).** Therefore the real Belle loader's `NodesUpdated` callback returns without starting new node loads. This goes beyond assuming historical source parity.
- Slot 2 uses adjusting thunk at `+0x1fa2` into compiled `OperationComplete` at `+0x1e7e`. That routine has branches **both for successful and failed operations** calling compiled `NextLoadLoopL` at `+0x1e28` (`+0x1f24` and `+0x1ee8` respectively). Its `iOperations.Count()==0` test at `+0x1f64..+0x1f66` gates final observer `LoadComplete` at `+0x1f68..+0x1f70`.

The root-type `ELoadRoot=1` branch of `NextLoadLoopL` appears at `+0x1e44` and calls `LoadChildrenOfChildrenL` (`+0x1e74 → +0x1c9c`). The loader's root-child branch invokes `LoadChildrenL` (`+0x1cee → +0x1c7e`); that helper checks `ChildCount()>0` (compiled compare and branch at `+0x1c8c..+0x1c8e`) before issuing an **`ELoadChildren=3`** load at `+0x1c90 → +0x1ac8`.

**Implication:** an observed `offline-root` browse after the initial root response has a strong, firmware-backed causal explanation: an NCD root load finishes, then IAUpdate's operation-completion handler sees `offline-root` as a child container with positive child count and starts the next stage. By contrast, `NodesUpdated` alone cannot initiate it through this Belle loader.

## Finding B: original root XML actually creates a child-loading candidate

Original v0.14.5 configuration XML: **751 bytes**, SHA256 `604f72517551adfb6cbe8c687be5f6cba86130846361d8b480c9dfc84e5ef310`. It declares **one nontransparent content source** with ID `offline-root`.

Original v0.14.5 root XML: **566 bytes**, SHA256 `42e6c84e7644f017e2b108764b320c2cdf40f58dab38255b530056bf990f1050`. Its only `FolderRef` records are `offline-root count=1` and `offline-secondary count=0`. It also contains one `FolderData` for `offline-root`, **no `ItemRef`** and **no remote URI**.

Actual Belle NCD server `MNcdParserEntityObserver` secondary virtual table at flattened `0x64588` uses `this` adjustment `-0xf0`. Its four method pointers `0x25bb1, 0x25e95, 0x260db, 0x26343` match `FolderRefL, FolderDataL, ItemRefL, ItemDataL`, based on [Nokia's observer interface order](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/protocol/inc/ncdparserobserver.h#L70-L93). The `FolderRefL` thunk at code `+0x1dbb0` adjusts `this` and dispatches to compiled `FolderRefL` code at `+0x1d724`.

The [historical NCD `FolderRefL` content-source branch](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/server/src/ncdloadnodeoperationimpl.cpp#L540-L700) creates/records a top-level node through `RefHandlerL`, persists the link and registers it in the content source map. **No positive child-count requirement gates the act of registering a top-level FolderRef.** This explains why older v0.12 (one `count=0` ref) and v0.13 (two `count=0` refs) are meaningful: both previously coincided with the spinner, even though their later child-load behavior may differ. Both are **older nonmatched trials**, not proof that FolderRef parsing alone hangs.

The direct v0.19/v0.20 difference is nonempty root node XML **and the work it triggers**, not status code alone. The real compiled method presence doesn't demonstrate it ran during the live trial.

## Finding C: child-404 error-to-proxy completion has a specific gate

The actual Belle NCD server's `MCatalogsHttpObserver` secondary virtual table at flattened `0x645a0` dispatches `HandleHttpEventL` and `HandleHttpError` (Thumb pointers `0x25631, 0x25671`). Its compiled `HandleHttpError`:

- selects `EFailed=5` at `+0x1d65c`, stores it at `+0x1d662`, and invokes `RunOperation` through virtual dispatch at `+0x1d66a`;
- in the later failed-operation state, **checks the pending proxy-message pointer** at `+0x1f392..+0x1f396`. **Only if it exists** does it send `ENCDOperationMessageCompletionError = 3` through the virtual `CompleteMessage` at `+0x1f39a..+0x1f3a4`.

This agrees with [the historical error branch](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/server/src/ncdloadnodeoperationimpl.cpp#L2310-L2325). The source also performs the server-side `CompleteCallback()` regardless, but that is not itself a proof that the *client proxy* receives an error.

On the client, [`CNcdBaseOperationProxy::HandleCompletedMessage`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/client/src/ncdbaseoperationproxy.cpp#L269-L385) turns completion ID **3** into `CompleteCallback(iStatus.Int())`; [`CNcdLoadNodeOperationProxy::CompleteCallback`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/client/src/ncdloadnodeoperationproxy.cpp#L377-L390) notifies the observer's `OperationComplete`, feeding the IAUpdate loader.

**Important:** The source/compiled gate is real, but we have **no evidence that `iPendingMessage` was null** on the E7's child-404 run. Likewise, a completed Sanctuary HTTP 404 write does not prove `HandleHttpError` ran on the phone. If this error does propagate and no other loader operation remains, the loader can report its final error. If it doesn't, or another operation remains, the spinner can persist.

## Updated hypotheses, ranked by evidence (not by invented probability)

1. **After-root child/error handling or outstanding other load:** supported by the v0.19 child request and the persisted spinner despite a sent child 404. Highest-priority runtime boundary: did the E7's NCD proxy deliver `OperationComplete(error)` for that child, and what was `iOperations.Count()` then?
2. **Error delivery gated on pending IPC message:** an explicit, independently verified Belle branch. Would distinguish NCD server-side failure from an error visible to IAUpdate. The actual runtime value is unknown.
3. **Child HTTP terminal event or asynchronous parser completion never reaches node error/completion:** still possible and not disproven by a server-side socket write.
4. **Initial root operation itself never completing:** **less favored** because the expected `offline-root` follow-on browse was observed, and the real loader's `NodesUpdated` callback is a no-op. Not categorically excluded without a process trace.
5. **Fictional child app UID/MIME/installed version:** **not necessary** for the v0.19 spinner, since v0.19 sent **no child metadata**.

## Practical boundary

This work **does not fix Software Update** or claim the original Nokia service has been restored. It upgrades the fault model. Further meaningful discrimination requires safe, *read-only handset-side evidence* of one of:

- the child's `CCatalogsHttpStack` terminal `ESucceeded/EFailed` event;
- `CNcdLoadNodeOperationImpl::HandleHttpError` and whether an IPC pending message exists;
- client `CNcdLoadNodeOperationProxy::CompleteCallback(error)`;
- `CIAUpdateLoader::OperationComplete` with current `iOperations.Count()`.

The existing E7 Bridge process list cannot observe those private callbacks. No justified handset instrumentation or verified C: private-cache rollback is currently available. **Do not rearm v0.19/v0.20, send v0.21 catalogues, reset caches, install SIS/SISX, modify firmware or assert a precise runtime wait point.**

## Reproducibility and repository scope

54/54 deterministic static assertions passed on the archived offline owner-provided images and frozen test fixtures; the read-only verifier and ELF disassembly wrappers remain private local analysis artifacts, **not** in the repository. No phone network activity or server execution occurred. [Draft PR #17](https://github.com/sillymotives/Nokia-E7/pull/17) remains docs-only, open, unmerged. `main` is unchanged.
