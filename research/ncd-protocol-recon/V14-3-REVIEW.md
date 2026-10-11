# Nokia E7 NCD v0.14.3: initialize the synthetic root folder

**State as of 2026-10-11:** v0.14.3 built and tested **host-only**. The E7 has **NOT** been tested with this new response. The PR remains **documentation-only**; runnable Python/tests/ZIP were delivered separately in the owner's ChatGPT conversation. Do not confuse the review note with committed source. No deployment, no merge, and no changes to `main`.

## Why v0.14.3 exists

In the physical v0.14.2 run, the E7 issued three synthetic update requests and the host completed one HTTP 200 socket write for each: configuration, two-folder root browse, and a permitted metadata child browse. The device continued displaying a spinner and, when the owner left it normally, showed a **blank update directory**. This proves neither successful client parsing nor cache damage.

A source audit of older Symbian NCD/IAUpdate code found a structural defect in our fixed response: v0.14.2 emitted two `FolderRef` but **no** `FolderData` in either browse. `CNcdLoadNodeOperationImpl::FolderRefL` creates folder link state; `FolderDataL` attaches metadata via `CNcdNodeManager::DataHandlerL`. `CNcdNode::State` treats missing metadata as `EStateNotInitialized`, and `CIAUpdateController::LocalContainerLoadL` skips uninitialised folders without traversing their children. This supplies a precise, testable explanation for **the blank list**, conditional on the E7 Belle parser following the historical code and not having previous metadata. It does **not** explain the spinner or prove actual phone-side parse acceptance.

Source references:
- [Original Preminet response parser](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/protocol/src/ncd_parser_pp_response.cpp)
- [Original embedded data parser](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/protocol/src/ncd_parser_pp_embeddeddata.cpp)
- [Original FolderRefL / FolderDataL](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/server/src/ncdloadnodeoperationimpl.cpp)
- [Original node initialization state](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/server/src/ncdnodeimpl.cpp)
- [Original IAUpdate folder traversal](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/iaupdate/IAD/engine/controller/src/iaupdatecontrollerimpl.cpp)

## Exactly one response change

The new separately delivered `ncd_folder_metadata_v143.py` subclasses the v0.14.2 server and adds one small fixed passive `embeddedData/entities/dataEntity` entry, **type=FolderData, id=offline-root**, with a harmless name and description **after** the two old `FolderRef` elements in the initial root response.

It retains the original:
- configuration XML (SHA256 `604f72517551adfb6cbe8c687be5f6cba86130846361d8b480c9dfc84e5ef310`);
- fictional child item XML (SHA256 `16231226e06abd15d9aee680eee5b7b3098a8bc64af334d6b634794a6500d7fd`), still inert octet-stream size zero, no package URI;
- two root folder reference records byte-for-byte, `offline-secondary` without metadata, one configured synthetic source;
- v0.14.2 guarded child companion matcher, fixed source-IP and host/path/namespace allowlist, three total one-shot HTTP 200 slots, time windows, privacy-preserving counters, 404 fallback for all other operations, and no binary response/download/installer endpoints.

The new stage-2 root browse hash is `42e6c84e7644f017e2b108764b320c2cdf40f58dab38255b530056bf990f1050` versus old `fc767282b8b8d10f18483a3a4ef0cd8767b4f78f1b3ce226b8ed192185c4fb7e`. `Content-Length` for this response necessarily changes. A fixed-body fail-closed validation prevents unknown or active elements or package/download addresses.

## Tests, packaging and independent QA (2026-10-11)

- **TDD:** 15 new tests written first; **six** failed against the real inherited v0.14.2 baseline (absent `FolderData`). All 15 passed after implementing the new fixed response.
- Complete suite: **306 tests passed** (including all 291 previously released tests) on the final ZIP **fresh extraction** in `python3 -m unittest discover -s tests -q` (26.324 seconds).
- First full working-copy suite had one intermittent inherited v0.14 HTTP test failure; that test passed alone and the complete suite passed on rerun. This was not concealed as an immediate green and no inherited source/test file was edited.
- Archive integrity OK; **56 members**; SHA256SUMS verifies **55 entries**.
- All **33 inherited Python/XML files** byte-for-byte unchanged against the actual v0.14.2 ZIP. **50 of 52** old ZIP members unchanged, with only README and SHA256SUMS appropriately updated.
- Localhost comparison verifies HTTP statuses 200, 200, 200, 404, matching non-size/non-version headers, old stage-1 and stage-3 bodies unchanged; only stage-2 body and associated Content-Length differ.
- Packaged ZIP: `e7-ncd-protocol-recon-v0.14.3.zip` SHA256 `8b5951ee83c5dba5916dd7324a9a11debd021f50a2ec34c73c626c82606cee3d`, delivered separately to owner in chat.

## Physical trial boundary

Read `LIVE-V143.md` from the separate ZIP. Optional trial is a single E7 check with SIM absent and isolated Wi-Fi, **only if owner accepts risk**. Earlier live runs proved metadata-only tests may touch writable protected C: caches; no independently verified full recovery path exists. Do not clear the phone's cache, factory reset, install or download anything, expand the allowlist or run repeated unchanged tests. Share only sanitized `RESULT` and UI state.

This is a test of folder initialization, **not** an assertion that the E7 should display the fictional item or finish its check. No v0.14.3 phone-side result exists yet. The existing v0.14.2 active spinner may originate from a separate topology or completion issue.

**PR policy:** keep documentation-only until the owner explicitly asks to change that scope; do not merge or deploy.

## First physical v0.14.3 trial: folder metadata transmitted; E7 remains spinning (2026-10-11)

Owner ran the separately delivered `ncd_folder_metadata_v143.py --arm-once --acknowledge-cache-risk` on Sanctuary, with the handset on the isolated hotspot. **The E7 was still spinning after the one-shot listener ended**, so the sole v0.14.3 folder-data modification **did not resolve the checking spinner**. Owner has **not yet reported the post-cancel directory state for v0.14.3**.

The sanitized host result shows:
- `configuration_200_attempted=true`, `configuration_response_socket_write_completed=1`, zero write failures.
- `matching_browse_seen=true`, `browse_response_socket_write_completed=1`, zero write failures.
- `root_response_includes_offline_root_folder_data=true` and `root_folder_data_count=1`. **These are fixture/server assertions, not a handset parser acknowledgement.**
- `child_200_with_documented_companions=1`, `child_item_metadata_200_attempted=true`, `child_response_socket_write_completed=1`, zero write failures.
- `matching_browse_retries_after_one_shot=0`, `configuration_retries_after_one_shot=0`, `child_metadata_attempts_rejected_by_gate=0`, `rejected_post_root_browse_reasons={}`, `other_post_request_count=0`, `wrong_namespace_probe_browse_count=0`, `handler_failures=0`.
- `configuration_and_child_payloads_unchanged_from_v142=true`, `only_root_browse_xml_changed_from_v142=true`, `unknown_operations_rejected=true`, `server_shutdown_reason=post_child_observation_complete`. Listener closed normally; **no additional HTTP request hit the listener within the bounded observation window**. This does not establish that the phone did not try other destinations or protocols outside this listener/window.
- `no_client_parse_ack=true`, `does_not_establish_update_service_success_or_phone_cache_safety=true`.

**Interpretation:** The host's stage-2 FolderData payload was delivered, and the stage-3 matcher continued to accept the Nokia request. This falsifies the narrow claim that *missing root FolderData alone explains the persistent checking spinner*. It does **not** disprove a separate effect on post-cancel item visibility; that outcome hasn't been observed in this trial. Do **not** infer from socket completion that any XML was parsed or persisted to the private E7 cache.

**System-level next boundary:** The historical [`CIAUpdateLoader::OperationComplete`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/iaupdate/IAD/engine/controller/src/iaupdateloader.cpp) starts follow-up loading work via `NextLoadLoopL`, then invokes `LoadComplete` only when `iOperations.Count() == 0`. An unfinished internal operation, parsing failure or request to another destination is still plausible, but **none established**. The source predates Belle and is not a client runtime trace.

**Conservative next evidence collection:** Do **not** arm v0.14.3 again. While the E7 is still spinning, a brief **passive packet-metadata-only** capture on the isolated hotspot (no XML reply, no connection stimulus) can discriminate additional network activity versus local-only waiting; protect any public endpoints/IPs before sharing. After that, exit Software Update normally once and note whether the directory is blank, displays the fictional item, or shows an error. No cache clearing, factory reset, real package, forged installation URL or broad-response implementation. Avoid a v0.14.4 until the completion path is better understood.
