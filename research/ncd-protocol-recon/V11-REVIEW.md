# NCD research: v0.11 root-expiry-only experiment

**Status:** locally implemented and tested; **not yet tested on the physical E7**. This PR is a documentation/experiment review, not a release and not a code deployment.

## Physical baseline

The owner-operated v0.10 E7 experiment saw a one-shot configuration request and matching Preminet browse; both HTTP 200 responses completed their **server-side socket writes**, zero socket-write/handler failures were reported, and the listener shut down automatically. Software Update still displayed the same error. This does not prove client acceptance or cache integrity. See [v0.10 review PR #13](https://github.com/sillymotives/Nokia-E7/pull/13).

## One-variable v0.11 design and offline implementation

Historical Nokia source [`CNcdLoadRootNodeOperation::ConfigurationBeginL`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/server/src/ncdloadrootnodeoperationimpl.cpp) applies the **outer** `configurationResponse expirationDelta` to the root link. [`CNcdNodeLink::ExpiredTime`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/server/src/ncdnodelink.cpp) treats the delta as minutes, so 0 represents immediate expiry under that older implementation. The E7's Belle implementation is not proven identical.

The independent v0.11 research package adds `ncd_expiry_probe_v11.py`, inheriting v0.10's local socket-write audit. It changes exactly one attribute in exactly one response: outer `configurationResponse expirationDelta="0"` -> `expirationDelta="5"`. **Inner** `clientConfiguration configurationExpirationDelta="0"` is deliberately unchanged. The empty browse payload, synthetic URI, namespace, matching logic, two single-use HTTP 200 allowlist, deadlines and privacy redaction all remain as before. Everything else gets 404; no folder, downloadable update, firmware, installer, redirect, cookie, session, or install instruction is served.

- Original v0.9 configuration SHA256: `604f72517551adfb6cbe8c687be5f6cba86130846361d8b480c9dfc84e5ef310`.
- v0.11 configuration SHA256: `50e3392d0dbc99e6d676b8cc47be816a267aab72c9095e462a09ab11d7f23ca9`.
- Original and v0.11 Preminet empty response SHA256: `c9ff885c45472e877cbbbe7f85e7a0cd11bb84a713e8e060323287b5f9a700f5`.
- Packaged v0.11 ZIP SHA256: `11556f9d45a7b518d9c298786e4898695c07139a14f59a0918ee2614dd6fe521`.
- Clean-archive verification: 32 checksummed source/fixture/test/doc files; **215 unittest tests passed** (207 existing + 8 v0.11 new), offline dry-run validated; old `ncd_empty_browse_v09.py` and `ncd_delivery_probe_v10.py` were byte-for-byte unchanged. The ZIP is delivered separately in the owner's ChatGPT conversation, **not committed as part of this GitHub PR**.

## Separate hypothesis: catalogue folder

The owner suggested returning something structural instead of an empty catalogue. The historic [`CNcdLoadNodeOperationImpl::FolderRefL`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/server/src/ncdloadnodeoperationimpl.cpp) creates a root catalogue child from a root-level `FolderRef`. A separately reviewed *possible future* experiment could supply one inert `FolderRef` with `id="offline-root"`, `type="FolderRef"`, `count="0"`, matching the synthetic source ID, with **no** children, remote URI, metadata, download links, or updates, while leaving the v0.10 outer expiry at zero. That variant is **not implemented or served** here. Do not introduce two protocol changes in one trial.

## Risk and operator boundary

The original ROM Z image and mass-memory capture do not restore private writable NCD/IAUpdate caches. Live tests can change internal C: data and no automatic rollback exists; the owner has previously accepted that risk during the separate v0.10 run, but this documentation is not blanket authorization for repeated trials. Public GitHub must not contain raw phone request bodies, identifiers, private file paths, or cached data.

A completed server socket write never proves handset-side receipt, parsing, success or absence of cache damage. If a future physical v0.11 trial again fails, inspect new observations before changing more payload fields.
