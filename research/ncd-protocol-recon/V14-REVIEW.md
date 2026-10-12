# Nokia E7 NCD v0.14: fictional software metadata stage

**Status:** implemented, host-only tested and archived; **NOT yet tested on the E7**. This draft is for review of the experiment and safety boundaries. **The full tested source/test ZIP is supplied separately in the owner's ChatGPT conversation, not attached or committed to this GitHub PR**. No service deployed; `main` unchanged.

## New physical observation and motivation

- v0.10/v0.11: a valid synthetic config followed by an **empty** Preminet browse; server socket writes completed but the E7 displayed the familiar update error.
- v0.12: one inert root `FolderRef`; the E7 remained on the Checking for improvements UI after server shutdown.
- v0.13: two zero-child root `FolderRef` nodes; still remained on the checking screen after shutdown, and the operator then **closed the updater and saw a blank update directory rather than the original error wording**. These UI differences may support successful navigation to an empty source, but are **not** proof of successful NCD operation completion.
- Operator reported **0 outbound packets** from a later passive-count command. This is inconclusive without verified concurrent checking and the correct phone IP/hotspot interface. No client-side trace or packet dump is disclosed.

Owner proposed a harmless dummy software item to distinguish “empty catalogue” from “can't load item list”, without installing anything. We are testing a **fictional metadata entry**, **not** sending a `.sis` binary.

## Historical source-backed request stages

Relevant original Symbian code, which predates the precise Belle IA Update build:

1. [`ncdloadnodeoperationimpl.cpp`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/server/src/ncdloadnodeoperationimpl.cpp): root content source first browses folder structure with `metadataDepth=0`, while `EChildren / ELoadMetadata` sends a follow-up `browse` with the **parent folder ID**, `includeMetaData=false` and `metadataDepth=1`. Item refs cannot be direct children of the content-source root.
2. [`ncdrequestbrowsesearch.cpp`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/protocol/src/ncdrequestbrowsesearch.cpp): confirms `browse/entity id`, `includeMetaData`, `responseFilter`, `pageStart`, `pageSize`, `structureDepth`, `metadataDepth` and `metadataPerLevel` serialization.
3. [`ncd_parser_pp_entityref.cpp`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/protocol/src/ncd_parser_pp_entityref.cpp): a root-level `FolderRef` can contain a nested `ItemRef` with an inherited parent.
4. [`ncd_parser_pp_embeddeddata.cpp`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/protocol/src/ncd_parser_pp_embeddeddata.cpp): recognises the matching `ItemData` metadata record.
5. [`ncdnodecontentinfoimpl.cpp`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/server/src/ncdnodecontentinfoimpl.cpp): item content info can be described by `downloadableContent` metadata, but *metadata does not require an actual package URI*.

## Exactly what v0.14 serves

The independent v0.14 package adds `ncd_metadata_probe_v14.py` plus `tests/test_ncd_metadata_probe_v14.py` and documentation. It does **not** modify prior v0.9 through v0.13 responders.

- **200 #1:** original v0.9 configuration **byte for byte**, including one synthetic content source, namespace and URI.
- **200 #2:** v0.13's two root folders, with exactly one changed XML attribute: `offline-root count=0` -> `count=1`; `offline-secondary count=0` unchanged.
- **200 #3:** available only after both previous stages, only to a syntactically validated *child metadata browse* for `offline-root` on the exact previous URI, namespace, source IP and host header. An extra response contains one nested `ItemRef id=e7-lab-fictional-update` and matching `ItemData` with name **E7 Lab Test Update**, `application` purpose, `iatype=SA`, `iaimportance=normal`, and a `size=0`, `application/octet-stream` description. No `.sis` files, binary payloads, package URIs, installer, downloads, firmware, HTTP GET content, purchases or installation endpoints.
- **All unrelated traffic:** 404, including unallowlisted posts, request retries, malformed child filters and any attempt to fetch a binary. Config, root, child and post-child windows are bounded to defaults of 90/45/45/15 seconds respectively. All logs are sanitized, with separate host-side write completion/failure receipts for each response. A host completed write is **not** a client parsing ACK.

## Reproducible host QA

The **16 new tests failed against the v0.13 baseline**, then passed after v0.14 implementation. Complete suite: **252 tests** passed on working copy and **252 tests passed on a fresh extraction**. ZIP integrity and manifest checks passed for **43** files. Original v0.9-v0.13 responder files were independently byte-compared to the prior archive.

- ZIP: `e7-ncd-protocol-recon-v0.14.zip`, separately delivered in ChatGPT; **not present on this GitHub branch**.
- ZIP SHA256: `54433cc016a16d31674bb88c376f65a35094cd08258e812d7b4c29648f48563a`
- Original config SHA256: `604f72517551adfb6cbe8c687be5f6cba86130846361d8b480c9dfc84e5ef310`
- New root response SHA256: `fc767282b8b8d10f18483a3a4ef0cd8767b4f78f1b3ce226b8ed192185c4fb7e`
- New child response SHA256: `16231226e06abd15d9aee680eee5b7b3098a8bc64af334d6b634794a6500d7fd`

## Risk, scope and success criteria

A fictitious catalogue entry might write protected private NCD/IAUpdate cache data on the E7's C: drive, **without an independently verified restore/rollback**. Z: and mass-memory copies do not solve that gap. The owner alone operates the hotspot and decides whether to run one optional physical test with `--acknowledge-cache-risk`; **this PR is not permission to install or execute software**.

The first useful observation is **whether the E7 makes the third, exact child-metadata browse at all**. A third server write only confirms host transmission. A visible entry would be useful evidence of catalogue traversal, but does not establish eligibility, client integrity or installation. A blank list/spinner/error should be recorded, not met with repeated random payload changes. Never publish raw phone request bodies, identifiers or unsanitized packet dumps.

## First attempted live v0.14 run after SIM reboot (owner-reported, 2026-10-11)

The user inserted a SIM and the E7 restarted and registered on a mobile network, then began displaying **"Unable to check for updates"**. The E7 successfully loaded a separate harmless HTTP test page served from Sanctuary at `http://10.42.0.1:8765/`, demonstrating at least basic WLAN/IP reachability, **not** confirming Nokia update-host DNS or application connection choice. The HTTP test server's source-IP log has **not** yet been provided.

The owner then ran `sudo python3 -u ncd_metadata_probe_v14.py --arm-once --acknowledge-cache-risk`, saw `ARMED`, manually stopped with `Ctrl+C`, and supplied the full sanitized result. Key counts:

- `configuration_200_attempted=false`, `configuration_response_socket_write_completed=0`
- `matching_browse_seen=false`, `browse_response_socket_write_completed=0`
- `child_item_metadata_200_attempted=false`, `child_response_socket_write_completed=0`
- `other_post_request_count=0`, `wrong_namespace_probe_browse_count=0`, `other_preminet_browse_count=0`, `handler_failures=0`, `configuration_retries_after_one_shot=0`
- `server_shutdown_reason=operator_stopped`

Source inspection of `V14Handler.do_POST` confirms that unmatched inbound POSTs reaching this listener increment `other_post_requests`, so **no HTTP POST requests were observed at the listener during the armed interval**. No synthetic v0.14 configuration, catalogue, or fictional application metadata was delivered in this run. The result cannot diagnose existing private cache state from earlier physical trials; it does not show that v0.14 harmed cache on this run.

**Next investigation, without rearming the NCD responder:** confirm the handset's current private IP using the successful browser test log, the hotspot's active interface/IP and port-53 DNS forwarding/override for `arrowcdb.ncd.nokia.com`, and whether Software Update's connection destination is WLAN rather than the cellular access point. The responder hard-codes expected E7 source IP `10.42.0.85`, binding IP `10.42.0.1` and port 80. Preserve private cache state, don't factory reset or guess XML changes. Passive captures must distinguish no relevant traffic from a wrong capture filter/interface and must not disclose private phone identifiers.

## Second physical v0.14 attempt without SIM (operator report, 2026-10-11)

The operator powered down/removed the SIM and returned to a Wi-Fi-only experiment. Unlike the earlier *with-SIM* run, the E7 once again sent requests to Sanctuary. Independent browser proof had previously shown hotspot source IP `10.42.0.85`, Nokia hostname `arrowcdb.ncd.nokia.com` mapped to `10.42.0.1`, and port 80 reachable. Removal coincided with a reboot, so this contrast does not isolate the SIM itself from connection settings or fresh process state.

The operator says “Unable to check for updates” appears immediately. The latest sanitized v0.14 RESULT and events:

- `configuration_200_attempted=true`, `configuration_response_socket_write_completed=1`
- `matching_browse_seen=true`, `browse_response_socket_write_completed=1`, `two_folder_preminet_200_attempted=true`
- **One additional matching endpoint/namespace browse was rejected with HTTP 404:** `matching_browse_retries_after_one_shot=1`. Host log text: `OBSERVED: extra/mismatched root browse; HTTP 404.`
- `child_item_metadata_200_attempted=false`, `child_response_socket_write_completed=0`, `child_metadata_attempts_rejected_by_gate=0`
- `handler_failures=0`, `wrong_namespace_probe_browse_count=0`, `other_post_request_count=0`, `server_shutdown_reason=operator_stopped`.

**Interpretation correction, source-inspected:** In `ncd_metadata_probe_v14.py` `V14Handler.do_POST`, `matching_browse_retries_after_one_shot` increments whenever `v09.request_kind` returns `preminet_matching_browse`, `is_child_metadata_request(body)` is false, and the root one-shot gate is already consumed. `v09.request_kind` validates path/namespace/operation but does **not** verify an exact root `entity id` or `responseFilter`. Thus the counter DOES NOT establish a byte-for-byte retry. It may be a legitimate second-stage browse whose filter/id differs from our strict expected child metadata format. Our intentional 404 may itself be contributing to the immediate updater failure. The fabricated item metadata has *not* been served.

**Next step:** preserve the two-stage response fixtures. Before more live writes or broadening the 200 whitelist, create a privacy-preserving diagnostic which classifies the rejected browse by local structural features only (root/other entity ID category, `includeMetaData` presence/value, responseFilter names/presence, pageStart, metadataDepth, permitted ranges, repeated-shape equality), without printing any device identifiers, raw XML, SIM info, cookies or full URLs. Test the diagnostics host-only first. Use one bounded live run if the owner elects to continue with private-cache risk. Do not assume cache corruption or alter the payload based only on these counters.
