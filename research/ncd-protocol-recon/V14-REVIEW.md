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
