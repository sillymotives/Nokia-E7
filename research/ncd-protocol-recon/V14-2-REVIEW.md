# Nokia E7 NCD v0.14.2: guarded child-browse companion elements

**Status:** Built and host-tested. **No E7 v0.14.2 physical test has been performed.** Documentation-only GitHub PR; runnable source/tests ZIP delivered separately in chat. No merge or deployment requested.

## Observed physical evidence, v0.14.1
The E7 received configuration HTTP 200 and first root-browse HTTP 200, then sent a distinct second browse to offline-root. Its sanitized shape: includeMetaData=false; metadataDepth=1; metadataPerLevel=1; pageStart=0; structureDepth=1; pageSize greater than one; one or more additional direct request-root elements. The listener rejected this second browse with HTTP 404; no fictional metadata was sent and the E7 continued spinning. The diagnostic did not reveal exact companion tag names or numerical page size.

## Source-based hypothesis and narrow change
The v0.14 is_child_metadata_request required exactly one root child, browse, rejecting all optional siblings. Historical Nokia source in CNcdRequestBase::CreateRequestL and CNcdRequestConfigurationData permits optional configuration, cookies and queryResponse ahead of browse. The new standalone ncd_guarded_browse_v142.py admits only documented passive siblings in their corresponding Preminet or configuration namespaces, in limited counts, with known nested tag names; it then calls the **unchanged v0.14 child matcher** on an in-memory stripped request to preserve namespace, folder ID, metadata depth, pagination, and child filter guards. A single final browse is required. Unknown/active/extra operations and invalid structures remain HTTP 404. A pageSize above 100 still receives 404, because the handset diagnostic only reported greater_than_one, not the actual number.

Historical references:
- https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/protocol/src/ncdrequestbase.cpp
- https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/protocol/src/ncdrequestconfigurationdata.cpp
- https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/server/src/ncdloadnodeoperationimpl.cpp

## Host verification on 2026-10-11
- New TDD tests had six behavior failures against the inherited v0.14 responder; all new tests passed after implementation.
- 24 added tests; **291 tests passed** from a fresh ZIP extraction.
- 51 SHA256SUMS entries verified, 52 ZIP files, integrity check passed; no SIS/SISX members.
- All 31 previously released Python/XML files byte-for-byte unchanged.
- Configuration, initial root, and fictional child response bodies reused unchanged from v0.14. Normal HTTP status/headers and one-shot gates compared against real localhost v0.14 requests; only versioned Server header differs.
- ZIP delivered in ChatGPT: e7-ncd-protocol-recon-v0.14.2.zip. SHA256: c4854e15e4569199fd448242bd2f2168187c5f1e35b847d5c21b87e9d136a4a1.
- Config response SHA256: 604f72517551adfb6cbe8c687be5f6cba86130846361d8b480c9dfc84e5ef310.
- Root response SHA256: fc767282b8b8d10f18483a3a4ef0cd8767b4f78f1b3ce226b8ed192185c4fb7e.
- Child response SHA256: 16231226e06abd15d9aee680eee5b7b3098a8bc64af334d6b634794a6500d7fd.

## Safety and next evidence
No actual package bytes, download URI, installer, firmware or executable update is served. Unknown operations, retries and all download paths receive 404. The E7's protected writable C: private NCD/IAUpdate cache has no verified backup/restore; metadata-only trials can modify it. The owner may elect one isolated no-SIM physical run after reading LIVE-V142.md in the ZIP and explicitly acknowledging the risk. Report only sanitized RESULT and the UI state, never device identifiers, raw requests or phone cookies. A host socket-write receipt is not a phone-side parse ACK; v0.14.2 might still reject the E7 if its actual companion is not on the documented whitelist or its page size exceeds 100.

**This GitHub PR remains documentation-only. Full runnable source ZIP is not committed here, and main is unchanged.**