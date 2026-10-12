# E7 NCD v0.20: original configuration 200, empty-root HTTP 200 control (completed)

**12 October 2026 | One owner-operated E7 check completed after host-only verification.**

## The v0.19 result to discriminate

The owner supplied a single actual E7 run of v0.19. Sanctuary wrote the **original 751-byte v0.14.5 configuration** HTTP 200, **the original 566-byte two-folder plus FolderData root browse** HTTP 200, then served an **empty HTTP 404** to the correctly gated child browse. All three socket writes completed, every one-shot gate stayed intact, there were no handler/write failures, and the server disarmed with `post_child_observation_complete`.

**Actual handset report: "spinnyboy kept spinning. :p"** No child item metadata or fake application details were delivered. Host socket writes are **not device parse or operation-completion acknowledgements**. See [the updated v0.19 result](V19-CONFIG-ROOT-200-CHILD-404-CONTROL.md).

Its paired **v0.18** control returned the identical configuration 200 but an **empty HTTP 404** at the root browse; the user reported the normal stopped-spinner/connection-error outcome. The principal root-stage differences between v0.18 and v0.19 were **HTTP status 404→200, nonempty folder XML, and resulting child work**. Earlier v0.14.1 root-200 then child-404 and v0.13's zero-child root-200 experiments also spun, but with different fixtures/conditions, so treat them as corroboration, not strict matched controls.

Historical Nokia [`CNcdLoadRootNodeOperation::DoRunOperationL`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/server/src/ncdloadrootnodeoperationimpl.cpp#L1554-L1652) starts source-specific node-load operations and tracks completed versus failed suboperations. The independent [`CNcdLoadNodeOperationImpl::HandleHttpError`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/server/src/ncdloadnodeoperationimpl.cpp#L442-L465) marks a child operation `EFailed` and resumes processing; its [failure state](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/server/src/ncdloadnodeoperationimpl.cpp#L2310-L2325) attempts an error completion if a proxy message is pending. [`CIAUpdateLoader::OperationComplete`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/iaupdate/IAD/engine/controller/src/iaupdateloader.cpp#L323-L420) sends final `LoadComplete` only when its operations list is empty. These are valid possible wait points **not a device-side trace or an established defect**.

## One-variable wire comparison

The separately delivered owner-facing script, **`e7-root-empty-200-control-v0.20.py`**, derives from the independently verified v0.18 host control. SHA-256:

`9111168336f8a9edb4f94c01ad9237d6140ee77ba40a22e640418d3d9e6f3f91`

| Stage | v0.18 (observed normal error) | v0.20 (proposed) |
| --- | --- | --- |
| Configuration POST | Original v0.14.5 XML HTTP 200, 751 bytes | **Identical** original v0.14.5 XML HTTP 200, 751 bytes |
| First recognized root Preminet browse | HTTP 404, `Content-Length: 0` | **HTTP 200, `Content-Length: 0`** |
| Follow-on child, downloads, retries, unknown traffic | HTTP 404, empty body | HTTP 404, empty body |

**Root response headers and zero-byte body remain identical to v0.18. Only the HTTP status changes from 404 to 200**, aside from transient Date. This intentionally application-invalid **empty successful root** is a diagnostic of the HTTP success status with **no root XML, no FolderRef/FolderData, no child ItemData**, and is not a valid updater feed or a repair. It cannot install anything.

Source IP/Host/path/namespace and envelope checks are copied from v0.18, including the exact original v0.14.5 configuration fingerprint. Bind only `10.42.0.1:80`; expected E7 peer `10.42.0.85`; at most one configuration 200 and one root 200; any further or unknown request receives 404 with no body. Expiry 90-second config gate, 45-second browse gate and 12-second post-browse observation. No request bodies, cookies, headers, phone identifiers or paths are printed. `--dry-run` opens no sockets; arming requires `--arm-once --acknowledge-cache-risk`.

A localhost unit test caught inherited **mislabeling of a child request received *after* root as `child_before_root_attempts`**. That counter is fixed *only in v0.20* so actual post-root requests increment `other_post_browse_attempts`. No request gate, status or response-body behavior changed as a result. This is an accounting-only difference, not an additional network variable.

## Host-only verification

- Python compilation and dry-run passed.
- **16 of 16** dedicated localhost-only tests passed: exact v0.14.5 configuration response, 200/zero-byte root, wire comparison with the original v0.18 response (**same config status/headers/body and same root headers/body, only root status changed**), fixed response gates, pre-root and post-root child 404, repeat/download/wrong-host/wrong-path checks, acknowledgement guard and auto-expiring windows.
- Loopback listener used ephemeral `127.0.0.1` ports only. No E7 check or privileged service binding occurred during host tests.
- The runnable script is **delivered separately**, not committed to the documentation-only PR.

## Optional one-check owner run

The owner may copy the separately delivered file to `~/Downloads` and place it beside the previous `ncd_empty_browse_v09.py`, `ncd_guarded_browse_v142.py` and `ncd_installed_probe_v145.py` in the same v0.14.5 directory:

```sh
cd ~/Downloads/e7-ncd-protocol-recon-v0.14.5
cp ~/Downloads/e7-root-empty-200-control-v0.20.py .
sha256sum e7-root-empty-200-control-v0.20.py
python3 e7-root-empty-200-control-v0.20.py --dry-run
sudo ss -ltnp '( sport = :80 )'
dig @10.42.0.1 arrowcdb.ncd.nokia.com +short
sudo python3 -u e7-root-empty-200-control-v0.20.py --arm-once --acknowledge-cache-risk
```

While `ARMED`, initiate **one** E7 Software Update check only; report the sanitized RESULT and whether the spinner stopped with the old error or remained. No installers, cache reset, retries or follow-up payloads. **Even ordinary update checks can write protected private NCD/IAUpdate cache, with no verified rollback**.

## Physical E7 result supplied 12 October 2026

Owner's sanitized Sanctuary output:

- `configuration_200_attempted=true`, `configuration_200_socket_write_completed=true`, `configuration_xml_identical_to_v145=true`; `configuration_retries_after_one_shot=0`.
- `recognized_root_browse_seen=true`, `recognized_root_http_200_attempted=true`, `recognized_root_200_socket_write_completed=true`, **`recognized_root_200_response_body_bytes=0`**.
- No root XML, FolderRef, FolderData, child metadata, install/download/firmware bytes; zero unallowlisted requests, failures or post-root attempts recorded during the operator-controlled observation.
- `server_shutdown_reason=operator_stopped`: the owner **used Ctrl+C**, so the listener did **not** demonstrate automatic time-window expiry or an automatically completed post-browse observation. No further E7 requests were observed *before* cancellation only.
- **Phone screen observation:** **"Stopped and said can't update :p"**. The checking spinner **stopped** and the E7 displayed its unable-to-check error. This is the owner's visual report; no internal parser or `OperationComplete` callback was captured.

**Key controlled result:** The exact same original configuration 200 followed by a root **200 with no body** causes normal failure UI, whereas v0.19's same configuration followed by root **200 with 566 bytes of two-folder+FolderData XML** left the device spinning (despite later child 404). Thus **root HTTP status 200 alone is insufficient to reproduce the stall**. What differs is the nonempty root structure and resulting node/child processing, **not** merely HTTP success. The empty body is application-invalid, so it does not prove a valid empty catalogue will finish cleanly.

### Historical cross-check predating today's matched controls

The earlier [v0.14 review](V14-REVIEW.md) records **v0.10/v0.11** (configuration + a syntactically empty Preminet browse) showing the familiar normal update error, but **v0.12** (one inert root `FolderRef`) and **v0.13** (two zero-child `FolderRef` elements) showing a persistent spinner. These different, older fixtures are not exact v0.19/v0.20 controls, but suggest the *first reported root folder reference* or the follow-on work it triggers may be relevant **even if that reference reports zero children**.

This aligns with historical [`CNcdLoadNodeOperationImpl::FolderRefL`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/server/src/ncdloadnodeoperationimpl.cpp#L540-L816), which builds/persists root child links and registers the node in the content-source map when the top-level folder reference arrives. The [NCD root operation](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/server/src/ncdloadrootnodeoperationimpl.cpp#L1554-L1740) waits for source-load suboperations and may send `NodesUpdated` updates before a separate final completion; the [IAUpdate loader](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/iaupdate/IAD/engine/controller/src/iaupdateloader.cpp#L323-L420) withholds `LoadComplete` while any tracked node operation remains pending. These are **potential paths, not a proven runtime hang**.

**Next priority is OFFLINE:** audit the first `FolderRef` callback, the root node's `NodesUpdated/Continue/Complete` state machine, and how zero-child folders flow into `CIAUpdateLoader`. The earlier v0.10–v0.13 results may already supply the relevant empty-XML versus folder-reference comparison, so do **not** repeat those physical variants just to get another data point. The E7's private NCD/IAUpdate writable cache has **no verified rollback**. Consider any new live response only if offline analysis identifies a genuinely discriminating, safe variable. Preserve unmodified ROM, network and handset state.

## Interpret the result only after observing it

- **Root 200 zero body, E7 stops/error**: a successful root status alone does not reproduce spinner. The remaining difference from v0.19 is **nonempty root XML and the descendant loading it starts**, which need separate consideration.
- **Root 200 zero body, E7 keeps spinning**: root HTTP success handling alone is enough to reproduce the wait even with no XML. Inspect parser `EndL/ParseCompleteL` and NCD operation completion for empty-body success in read-only Belle code. This does **not** prove the terminal HTTP callback is missing.
- **No root request or write failure**: experiment is inconclusive. Avoid relaxing the expected request guard or drawing causal conclusions.

**One actual E7 observation is recorded above; the listener was manually stopped.** [Draft PR #17](https://github.com/sillymotives/Nokia-E7/pull/17) is unmerged and documentation-only; `main` and E7 firmware are unchanged.
