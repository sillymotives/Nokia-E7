# E7 Belle: offline proof of the loader-to-UI refresh-completion gate

**11 October 2026 | Read-only, owner-supplied Belle firmware images | Physical cause not yet identified.**

## The owner-operated v0.14.5 outcome

Sanctuary's one-shot v0.14.5 responder wrote three allowlisted HTTP 200 replies: configuration, two-folder root, and guarded child metadata. **All three host socket writes completed**; the server recorded no failed writes, retries, handler exceptions, unknown requests, or additional POSTs during its bounded post-child observation period. It disarmed normally.

**The E7 continued spinning.** No end-of-spinner, XML parser acknowledgement, child NCD final callback, UI refresh completion or post-exit list result was established. Because the only child metadata change from v0.14.4 was to reuse the owner's pre-installed data-only test-probe UID and advertise a newer version, **matching an already installed test package did not fix the observed spinner**. This does **not** prove the handset saw or accepted that metadata, nor prove whether its registry match succeeded.

This is the declared stop point for active synthetic NCD HTTP trials. Writable E7 private update caches have no verified rollback.

## Main source-level clue

Nokia's [`CIAUpdateLoader::OperationComplete`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/iaupdate/IAD/engine/controller/src/iaupdateloader.cpp#L319-L421) keeps each outstanding NCD node load operation in `iOperations`. For every completed operation it removes that entry, potentially schedules subsequent child work via `NextLoadLoopL`, then calls `iObserver.LoadComplete(iErrorCode)` **only when `iOperations.Count() == 0`**. Hence a child transport or NCD operation that never fires its final `OperationComplete` can leave the user interface waiting without further HTTP traffic. Errors *which do deliver* their operation-complete callbacks can still reach a final `LoadComplete` with a nonzero error.

[`CIAUpdateController::LoadComplete`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/iaupdate/IAD/engine/controller/src/iaupdatecontrollerimpl.cpp#L848-L874) then assembles local results and invokes `iObserver.RefreshComplete(iNodes, aError)`. [`CIAUpdateUiController::RefreshComplete`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/iaupdate/IAD/ui/src/iaupdateuicontroller.cpp#L1226-L1256) transitions its own state to idle and forwards success or failure through the UI refresh-completion path. **Node filtering is a later step, separate from completion of outstanding operations**. An absent update item alone should not keep the operation array nonempty.

These older source statements are backed below by **original Belle compiled control flow**, not merely guessed from historical source.

## Belle binary chain verified by RTTI, vtables and Thumb branches

Two owner's **original, flattened, read-only E32 code images** were independently SHA256-verified against the supplied manifest:

| File | SHA-256 (uncompressed analysis copy) |
| --- | --- |
| `iaupdateengine.dll.flat.bin` | `f395e88a078d6837823e169c1209d6ad295dad242ef5564b144c97584ec5ab99` |
| `iaupdate.exe.flat.bin` | `951319e0dcb0a56380f848711ace717b0636e763020ae92722fcf6c480cdbadd` |

The companion `ncdserver_20019119.exe` and `ncdproxy_20019119.dll` SHA256s and EPOC headers were rechecked too; their **already documented** NCD node IPC completion handoff is in [`V14-4-BELLE-CONTROLFLOW-AUDIT.md`](V14-4-BELLE-CONTROLFLOW-AUDIT.md). The following offsets are **relative to the image's E32 code section** (file offset `0x9c`, code base `0x8000`), except explicitly named **flat-file** offsets. Pre-relocation Thumb vtable pointers have the low bit set. We did **not** execute phone firmware; synthetic ELF wrappers were disassembly-only.

### 1. `CIAUpdateLoader::OperationComplete` gates on outstanding NCD operations

- Actual `CIAUpdateLoader` RTTI/name association: typeinfo flat `0xbe00`, name `15CIAUpdateLoader` flat `0xc2ef`; RTTI-associated primary table at flat `0xcf48`; `MNcdLoadNodeOperationObserver` secondary table has offset-to-top **-4** at flat `0xcf64`.
- Secondary observer slot 2, flat `0xcf74`, is Thumb pointer `0x9fa3`, whose adjusting thunk at code `+0x1fa2` enters the actual `OperationComplete` routine at code `+0x1e7e`. The historical observer interface order is `NodesUpdated`, `QueryReceived`, `OperationComplete`.
- At code `+0x1f5e` the method loads the `iOperations` vector, calls its count helper at `+0x1f60`, compares zero at **`+0x1f64`**, and at **`+0x1f66` branches past the observer call if nonzero**.
- The **zero outstanding operations** route at **`+0x1f68..+0x1f70`** loads `iObserver`, passes the recorded `iErrorCode`, and makes the virtual `LoadComplete` call. The binary has an additional post-callback success-conditioned action, so do not assume the precise ordering of peripheral firmware bookkeeping is identical to the pinned historical source.

This is a concrete compiled **no-final-notification-if-any-operation-remains** branch. It does not reveal the E7's live `iOperations.Count()`.

### 2. The loader observer dispatches into `CIAUpdateController::LoadComplete`

- Actual `CIAUpdateController` typeinfo flat `0xbe98` (class name `19CIAUpdateController`); source inheritance includes `MIAUpdateLoaderObserver`.
- The corresponding secondary interface table has offset-to-top **-32** at flat `0xd1c4`; first virtual entry flat `0xd1cc` is Thumb pointer `0x923f`. Its adjusting thunk at code **`+0x123e`** enters the controller's `LoadComplete` implementation at **`+0x11d6`**.
- In that body, the eventual observer dispatch at **`+0x122e..+0x123a`** loads the UI-controller observer and calls virtual slot **+4**. [`MIAUpdateControllerObserver`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/iaupdate/IAD/engine/inc/iaupdatecontrollerobserver.h) defines slot 0 `StartupComplete` and **slot 1 `RefreshComplete`**. This matches the historical controller source.

### 3. Actual `iaupdate.exe` implements the UI's refresh-completion callback

- Actual `CIAUpdateUiController` typeinfo flat `0xbd38`; named class RTTI `21CIAUpdateUiController` at flat `0xc03c`.
- `MIAUpdateControllerObserver` secondary virtual table at flat **`0xcabc`** has offset-to-top **-4**; slot 1, flat **`0xcac8`**, is Thumb pointer `0xdb6f`. Its adjusting thunk at code **`+0x5b6e`** calls into the real `RefreshComplete` body at **`+0x5aa8`**.
- At code **`+0x5ab8..+0x5ac2`**, the method clears the refreshing state and tests the prior state. The resulting branches implement the historical `EUiRefreshing` vs other-refresh handling, forwarding the result or error. A completed callback therefore enters the UI's state-reset path. The compiled class also supports a distinct UI-refresh route; do **not** assume all instances call identical observer methods.

**Internal static verifier:** **36/36** checks passed: the four supplied firmware digests and EPOC signatures; both E32 code-section offsets and code bases; exact RTTI/vtable pointers and adjusting thunks; both loader gate and observer dispatch instructions; controller observer virtual-slot offset; and actual UI callback entry/state test. This is **36 static checks, not 36 live trials**. No original binaries, code section, verifier-generated ELF or sensitive captures were committed.

## End-to-end hypothesis and limits

```text
Actual network byte delivery                     [NOT OBSERVED ON E7]
   -> CCatalogsHttpStack ESucceeded/ EFailed     [NOT OBSERVED]
      -> CCatalogsHttpTransaction completion    [NOT OBSERVED]
         -> NCD child ParseL / EndL / ParseCompleteL  [NOT OBSERVED]
            -> NCD server NodesUpdated(5), Continue(3), Complete(4) [NOT OBSERVED]
               -> NCD proxy OperationComplete   [NOT OBSERVED]
                  -> IAUpdateLoader removes pending operation
                     -> if iOperations.Count() == 0, LoadComplete
                        -> IAUpdateController RefreshComplete
                           -> IAUpdateUiController RefreshComplete
                              -> UI refresh state cleared/result shown
```

The **binary-backed last three stages** establish a credible conditional explanation for a persistent spinner: if any final NCD operation callback never arrives, the loader deliberately withholds its completion notification. **The observed physical run alone does not prove this happened**. Conversely, ordinary completed errors generally drain into a failure result, and a correctly completed refresh can legitimately contain no visible eligible nodes.

**Practical next discriminator:** permission-respecting, read-only *live E7* trace (if ever available) of the child transaction terminal event, NCD parser completion, NCD proxy completion and IAUpdate loader operation-count transitions. The current E7 Bridge process/registry inventory does not provide such private callbacks.

## End-of-night stop decision

No v0.14.6; no synthetic response mutations, cache reset, app reinstall, SIS/SISX downloads, privileged instrumentation, or second physical test. The host responder is disarmed. Preserve existing private updater state rather than attempting a risky rollback. Documentation-only draft [PR #17](https://github.com/sillymotives/Nokia-E7/pull/17) remains unmerged. This note closes the current evidence-limited campaign without pretending to have located the exact live failure.
