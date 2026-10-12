# E7 Belle: folder-reference boundary and pending-operation hypothesis

**12 October 2026 | Offline review after owner-operated v0.20. No new handset trial, firmware modification, or responder.**

## Experimental boundary

| Trial | Config | Root catalogue | Child | User-visible updater state |
| --- | --- | --- | --- | --- |
| v0.18 | Exact v0.14.5 HTTP 200 XML | Empty HTTP 404 | none | Stops with standard error (owner's "same thing") |
| v0.19 | Exact v0.14.5 HTTP 200 XML | Exact 566-byte v0.14.5 two `FolderRef` + one `FolderData`, HTTP 200 | Guarded empty HTTP 404 | **Indefinitely spins** |
| v0.20 | Exact v0.14.5 HTTP 200 XML | **Empty HTTP 200, Content-Length 0** | none observed before operator manually stopped server | Stops with standard error |

All intended host response socket writes completed. These are **not** phone-side HTTP terminal events, parse acknowledgements or private NCD callbacks. The v0.20 server ended by user **Ctrl+C**, `server_shutdown_reason=operator_stopped`; no automatic expiry inference is valid.

**What is separated:** HTTP **200 status alone** on the root browse is not sufficient to make the updater hang. The v0.19 difference is the root's **nonempty node XML plus the follow-on operation(s)** it can create. Two variables change together, so we cannot assert that XML bytes alone or an internal node callback caused the actual hang.

## Crucial older negative controls

The [v0.14 historical review](V14-REVIEW.md) records that:

- v0.10 and v0.11: configuration 200 followed by **empty Preminet catalogue browse** ended with the normal updater error.
- v0.12: adding **one inert root `FolderRef`** coincided with persistent checking after server shutdown.
- v0.13: sending **two root `FolderRef` nodes, both advertising zero children**, still left the E7 spinning. The owner manually exited the checking screen and saw a blank update list.

These older trials varied in time and fixture, and the precise E7 internal acceptance of `FolderRef` was not traced. Their strong practical implication is **do not repeat empty-root XML and FolderRef-count experiments blindly; these contrasts have already been run**.

## Source-level mechanism to prioritize

1. In historical Nokia [`CNcdLoadNodeOperationImpl::FolderRefL`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/server/src/ncdloadnodeoperationimpl.cpp#L540-L700), when loading a nontransparent *content source*, a top-level `FolderRef` is processed by `CNcdNodeManager::RefHandlerL`, added to the content source map through `AddNodeToContentSourceL`, and its link persisted. **This path exists even when the advertised child count is zero.** This is more than an XML-token variation: it can change node hierarchy and later loader work. `FolderRefL` on this branch does **not by itself** prove the operation notified the proxy or appended a loaded-node identifier; do not conflate it with the later `FolderDataL` path.
2. [`CNcdLoadRootNodeOperation::EBrowseRequest` and `EReceiveBrowse`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/server/src/ncdloadrootnodeoperationimpl.cpp#L1554-L1650) start one load-node suboperation per configured content source, count completed and failed suboperations, and can issue `NodesUpdated` when a client message and loaded nodes are waiting. Its [`EComplete` phase](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/server/src/ncdloadrootnodeoperationimpl.cpp#L1653-L1743) can send node updates **instead of** the final completion while loaded node IDs remain; those updates require later client/proxy interaction. The already recorded [actual Belle IPC audit](V14-4-BELLE-CONTROLFLOW-AUDIT.md) confirms completion IDs **NodesUpdated=5**, **Complete=4**, and client **Continue=3** exist in the user's E7 binaries. It has **not** proved any such IPC event was missed live.
3. The historical [`CIAUpdateLoader::OperationComplete`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/iaupdate/IAD/engine/controller/src/iaupdateloader.cpp#L323-L420) removes each finished operation, possibly launches deeper child loads with `NextLoadLoopL`, and **only calls `LoadComplete` when the operation array is empty**. Its [`NextLoadLoopL`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/iaupdate/IAD/engine/controller/src/iaupdateloader.cpp#L799-L882) traverses new root child containers. [`LoadChildrenL`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/iaupdate/IAD/engine/controller/src/iaupdateloader.cpp#L548-L558) checks `ChildCount() > 0` before requesting metadata, so **zero advertised children is meaningful**, but does not by itself settle whether the outer root or container load completed.
4. The actual E7 [loader/UI binary control-flow audit](V14-5-BELLE-LOADER-UI-COMPLETION-AUDIT.md) independently validates the zero-outstanding-operations gate and dispatch into `RefreshComplete`. The exact **stuck operation** remains unidentified.
5. An HTTP 404 during child loading normally enters [`CNcdLoadNodeOperationImpl::HandleHttpError`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/server/src/ncdloadnodeoperationimpl.cpp#L442-L465), then [`EFailed`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/server/src/ncdloadnodeoperationimpl.cpp#L2310-L2325). **v0.19 does not establish that this callback fired on the phone**, only that its host server wrote a response. Thus a broken failure callback or a still-pending *other* operation remain possible.

## Next engineering priority (without a handset probe)

The research should now target the **root-success to node/proxy completion** sequence, not new item identities or browse metadata:

- Annotate actual Belle `FolderRefL`, `CNcdLoadRootNodeOperation::EReceiveBrowse/EComplete`, `NodesUpdated(5)/Continue(3)/Complete(4)`, and `CIAUpdateLoader::NextLoadLoopL` entry/exit branches against the preserved owner E32 images.
- Determine which exact event would leave an operation in `iOperations` when both the root 200 socket response and the subsequent child 404 have been written. This is a **hypothesis-ranking task** until a legitimate read-only device-side trace exists.
- **No v0.21 hardware test by default.** The user has already tested empty Preminet and zero-child FolderRefs; repeating those cannot justify additional private-cache risk without a new decision point.
- Do not delete/update protected C: cache, factory reset, install a test SIS, or claim that `host_socket_write_completed` confirms parser/IPC completion. No verified cache rollback exists.

[Draft PR #17](https://github.com/sillymotives/Nokia-E7/pull/17) remains docs-only, open, unmerged; `main` unchanged.
