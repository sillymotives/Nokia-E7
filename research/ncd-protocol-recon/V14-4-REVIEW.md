# Nokia E7 v0.14.4: SISX catalogue identity only

**Status:** Implemented and verified in an isolated host test environment; **no v0.14.4 E7 trial yet**. Draft PR is still **documentation-only**. The complete runnable ZIP is delivered separately to the owner in chat, **not committed here**. No merge, no production deployment, and no changes to `main`.

## Physical result motivating the change

In the single v0.14.3 run, the host successfully wrote its v0.9 config response, its v0.14.3 two-folder root response including one inert `FolderData` for `offline-root`, and the guarded fictional item response. The native E7 still spun indefinitely; on normally leaving it the owner again observed a **blank update directory**. During the stalled spinner an earlier 30-second passive Wi-Fi capture reported zero TCP/UDP packets, without a same-session known-good browser control. None of this is a Nokia parser acknowledgement or proof of cache damage.

## Specific source-backed SISX identity hypothesis

The historical Nokia NCD implementation [`CNcdNodeContentInfo::InternalizeL`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/server/src/ncdnodecontentinfoimpl.cpp) converts the content `id` to an application UID **only** if application-purpose downloadable content has MIME `KMimeTypeMatchSisx`, defined in [`catalogsconstants.h`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/inc/catalogsconstants.h) as `x-epoc/x-sisx-app`. The inherited inert child had `mime=application/octet-stream` and the nonhex `id=e7-lab-not-a-package`, so the historical path leaves its app UID null.

v0.14.4 changes **only those two values** in the child `dataEntity/downloadableContent`:
- `mime`: `application/octet-stream` -> `x-epoc/x-sisx-app`
- `id`: `e7-lab-not-a-package` -> `E7A01444`, an invented eight-digit UID in the development-only `0xE0000000..0xEFFFFFFF` range ([Symbian developer reference](https://cortex.p.gen.nz/nokia/symbian/Nokia%20Symbian3%20Developer%27s%20Library%20v0.8/GUID-380A8C4F-3EB6-5E1C-BCFB-ED5B866136D9.html)). Uniqueness on a handset is not verified.

All other fields, metadata records, static names/description, folder information, `size=0`, response counts/timers, expected IP/host/path and child companion allowlist remain unchanged. The configuration and root XML responses are **byte-identical to v0.14.3**.

**This is not an actual dummy SIS/SISX package.** No `.sis`/`.sisx` binaries, installable file, purchase workflow, URI, download route, signing certificate, firmware image or executable package are present. Even if the item becomes visible, **do not select, download or install it**. The E7 private writable update cache still lacks a verified rollback; therefore a metadata-only live check is optional and owner-operated, not automatic.

## Independent verification (2026-10-11)

- Twelve new TDD tests; against the v0.14.3 fallback there were five expected failures and one absent result-field error; all twelve pass with v0.14.4.
- Localhost exercised exact config 200, root 200, new SISX child 200, repeat and attempted download 404; compared all response statuses/bodies/headers with v0.14.3 and proved only stage-three body/Content-Length differ.
- **318 tests passed across all 17 modules on a clean ZIP extraction**, each module isolated to avoid combined-process fixture interference; every command exited with code 0 and `OK`. Combined discovery previously wrote `Ran 318 tests ... OK`, but other attempts intermittently failed or hung during shutdown, so the independently isolated module passes are the reliable completion evidence.
- ZIP `e7-ncd-protocol-recon-v0.14.4.zip`: **60 members**, **59 SHA256 manifest entries** verified, archive integrity checked, **no binary SIS/SISX members**.
- **All 54 inherited files other than README and checksum manifest byte-for-byte unchanged** from the real v0.14.3 ZIP. Added only the v0.14.4 responder, one test file, release notes and live-read instructions.
- ZIP SHA256: `54e38730adbcac4d9b23d54333d432b03d17d04f2ef78f1a2e452b71cdc1881e`.
- No actual E7 v0.14.4 trial has been performed.

## Experiment boundary

The separately delivered ZIP includes `LIVE-V144.md`; verify the SHA256 manifest and run the dry-run/test suite before optional live use. SIM out, mobile data off, isolated Sanctuary hotspot, 1 check only, **explicit cache-risk acknowledgement**. If the spinner remains, stop mutating metadata and investigate the updater completion path rather than adding a package URI or executable bytes.

No claim of native Belle parser acceptance, successful updater completion, safe cache mutation or genuinely installable SIS is made here.

## First physical v0.14.4 run: SISX identity delivered, spinner persists (2026-10-11)

Owner launched `sudo python3 -u ncd_sisx_identity_v144.py --arm-once --acknowledge-cache-risk` on Sanctuary while E7 Software Update checked. Device UI continued spinning after listener closed ("Spinnyboi"). The report confirms all three 200 responses were successfully written to the host socket:
- `configuration_response_socket_write_completed=1`
- `browse_response_socket_write_completed=1`; `root_folder_data_count=1`; `root_response_includes_offline_root_folder_data=true`
- `child_response_socket_write_completed=1`; `child_200_with_documented_companions=1`; `uses_sisx_catalogue_mime_and_test_uid=true`; `only_child_identity_metadata_changed_from_v143=true`
- `handler_failures=0`, `matching_browse_retries_after_one_shot=0`, `child_metadata_attempts_rejected_by_gate=0`, `rejected_post_root_browse_reasons={}`, `other_post_request_count=0`, `other_preminet_browse_count=0`, zero socket-write errors
- `server_shutdown_reason=post_child_observation_complete`, `no_client_parse_ack=true`, no package/download URI, no SIS/SISX binaries, all further requests remain HTTP 404.

**Result:** The **SISX MIME and development UID alone did not resolve the spinner**. This is a controlled negative result for that symptom, not an E7-side parse/NCD-cache conclusion. **The post-exit update list after v0.14.4 has not yet been reported**, so do not claim it remained blank in this specific trial. Earlier v0.14.3 remained blank.

### Architectural review instead of another blind payload revision

Historical [`CIAUpdateLoader::OperationComplete`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/iaupdate/IAD/engine/controller/src/iaupdateloader.cpp) invokes `NextLoadLoopL` after each completed node operation, and only calls `iObserver.LoadComplete(iErrorCode)` once `iOperations.Count() == 0`. A host-side HTTP 200 socket write is two layers earlier and does not prove the parser completed, the node operation finished or the UI callback fired.

Further inspection of [`CNcdLoadNodeOperationImpl::FolderRefL`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/server/src/ncdloadnodeoperationimpl.cpp) shows a **single nontransparent content source can create several direct root folder children**, while `CIAUpdateLoader::RootExpiredL` checks *child count* equal to two. Thus the prior intuition that one configuration source necessarily means only one root node is **not established**; the host sends two folder refs under the same source. It still does not prove that this represents the intended Arrow-plus-firmware catalogue, or that the Belle implementation behaves identically.

The local v0.14.4 fixture was inspected from the exact previously verified ZIP; it still advertises one nontransparent source, two root FolderRefs, one inert FolderData, one nested ItemRef + ItemData and zero installer/download bytes. **Do not proceed to real dummy SIS bytes, installer routes, unsupported MIME tweaks or a v0.14.5 until there's evidence about the device-side completion path.** Most direct next observation: exit the v0.14.4 spinner normally and note whether the list is blank, has the fictional item or reports an error. A previously reported zero-packet post-child capture had no known-good control, so do not treat it as definitive proof of no other network activity.
