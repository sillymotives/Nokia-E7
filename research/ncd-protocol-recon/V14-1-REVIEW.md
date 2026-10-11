# Nokia E7 NCD v0.14.1: classify the rejected second browse without changing the responder

**State:** built and host-tested from the previous v0.14 ZIP; **no v0.14.1 test on the handset has occurred**. This is a **documentation-only review file**, not the runnable archive. The full source, tests, documentation, and verifiable ZIP are supplied separately in the owner's ChatGPT conversation; GitHub `main` is not touched.

## Observed phone behaviour (2026-10-11)

- With a SIM inserted and the E7 restarted, Software Update produced an immediate "Unable to check for updates" screen. The physical v0.14 listener's counters remained entirely zero.
- Wi-Fi IP, DNS and browser HTTP connectivity all checked out independently: `10.42.0.85` -> Sanctuary hotspot `10.42.0.1`, Nokia update hostname resolved to Sanctuary; the browser reached an isolated HTTP 200 at port 80.
- After SIM removal and another restart, the v0.14 server received **configuration (200 written)** and **root browse (200 written)** again. It then logged **`OBSERVED: extra/mismatched root browse; HTTP 404.`** and `matching_browse_retries_after_one_shot=1`, with **zero** child-metadata 200 attempts. The counter does **not** distinguish an actual replay from a different second-stage browse. This change is confounded by the reboot, so SIM alone is not a proved root cause.
- No observation proves E7 parsing or safe protected writable C: updater cache. Do not delete the caches or invent a factory reset.

## What v0.14.1 adds

`ncd_browse_diagnostic_v141.py` imports **unmodified v0.14**, installs a transparent one-read POST observer on top of `V14Handler`, and delegates all HTTP statuses, response bytes, headers, one-shot gates, timeouts and fallback 404 logic to the original handler.

Once the original root browse is accepted, otherwise-matching additional browse requests that the old policy would reject are classified into **fixed local categories only**:

- Known synthetic folder vs other/missing/multiple entity reference, never the actual arbitrary ID.
- `includeMetaData` true/false/missing/other.
- Page/filter fields categorized only as missing/zero/one/more than one/invalid, unexpected field presence, child filter type, and other structural flags.
- `byte_identical_to_first_root` is boolean only, comparing against an **in-memory digest never printed or returned**; `same_sanitized_shape_as_first_root` compares only the coarse categories.
- `matches_v14_exact_child_gate` reveals whether the old parser would recognise the exact child request shape; it **does not authorise** another HTTP 200.
- Only the **first eight** additional summaries appear in the result, accompanied by total count and a truncation flag.

No HTTP POST bodies, client-provided values, identifiers, cookies, URLs or request hashes are logged. No binaries, SIS/SISX packages, firmware, purchase, download or installation endpoints are added. Do not infer that a fictional item is safe for installation.

## Verification (October 11, 2026)

- TDD: diagnostic tests failed against v0.14, then passed after implementing v0.14.1.
- **15 added tests** pass, including real localhost HTTP comparison of the new handler and v0.14 with byte-identical response bodies and status/headers across allowed stages and rejected paths.
- **267 complete-suite tests pass** in the working tree and independently on a **clean ZIP extraction**.
- SHA256 manifest verifies **47 file entries**, plus the manifest makes **48 archive members**.
- All **23 previously released Python and test files** were byte-compared to their originals in the v0.14 ZIP and remain unchanged.
- The ZIP contains no SIS/SISX files and passes archive integrity.
- ZIP: `e7-ncd-protocol-recon-v0.14.1.zip` (delivered separately; not attached to this PR)
- **ZIP SHA256**: `d2f7c22418c6edf2f457a85cd5929ec008a95e25574cc6d83c56600aa59fb3fc`
- Config response SHA256: `604f72517551adfb6cbe8c687be5f6cba86130846361d8b480c9dfc84e5ef310`
- Root response SHA256: `fc767282b8b8d10f18483a3a4ef0cd8767b4f78f1b3ce226b8ed192185c4fb7e`
- Child response SHA256: `16231226e06abd15d9aee680eee5b7b3098a8bc64af334d6b634794a6500d7fd`

## Optional owner-operated observation

Read `LIVE-V141.md` from the separate ZIP. Use the isolated Sanctuary hotspot, E7 without SIM and mobile data off; verify the E7 source IP and DNS still match. Only then consider `sudo python3 -u ncd_browse_diagnostic_v141.py --arm-once --acknowledge-cache-risk`. The owner alone elects whether to accept cache risk. Perform **one check only**. Stop the test on unexpected conditions and supply only the sanitized `RESULT` and UI text.

The only intended diagnostic outcome is identifying how the *second browse* differs, if at all, from the root request. No new 200 responses and no phone-side cache recovery are part of this version.

## First physical v0.14.1 result: metadata browse blocked by an over-strict shape gate

**E7 operator report (2026-10-11):** The device was back to a persistent checking spinner. Configuration HTTP 200 and initial root browse HTTP 200 were each transmitted with completed host-side socket writes. One **additional, different** browse reached the listener, received HTTP **404** and was diagnosed. No synthetic child item metadata was served. The limited run ended with `server_shutdown_reason=child_window_expired` and no handler/diagnostic failures.

Sanitized first-vs-second request comparison:

| Feature | First accepted root browse | Second rejected browse |
| --- | --- | --- |
| `entity_id_class` | `offline_root` | `offline_root` |
| `include_metadata` | `true` | `false` |
| `metadata_depth` | `zero` | `one` |
| `metadata_per_level` | `one` | `one` |
| `page_size` | `one` | `greater_than_one` |
| `page_start` | `zero` | `zero` |
| `structure_depth` | `one` | `one` |
| `request_other_direct_operations` | `true` | `true` |

The second browse has `expected_filter_keys_only=true`, `filter_children=none`, `entity_has_children=false`, `entity_unknown_attributes=false`, `entity_timestamp_present=false`, `browse_unexpected_attributes=false`, `browse_unexpected_children=false`, `filter_count=one`, `parse_status=recognized_browse`, `same_sanitized_shape_as_first_root=false`, `byte_identical_to_first_root=false`, and `matches_v14_exact_child_gate=false`. `additional_browse_observation_count=1`. The diagnostic contains no raw request or identifier.

### Identified host-side incompatibility

**Source inspection** of the archived v0.14 `is_child_metadata_request` confirms it unconditionally refuses any parsed request-root where `len(r) != 1` or the sole child isn't `browse`. The E7's second request has `request_other_direct_operations=true`, proving another direct element is present, so that guard alone suffices to reject the exact observed request. The `page_size=greater_than_one` value is **not, by itself, proof of a second mismatch**: the v0.14 gate accepts integers 1 through 100, but the sanitized class does not disclose whether the observed value exceeds 100.

Historical Nokia source corroborates normal additional root elements:

- [`CNcdRequestBase::CreateRequestL()`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/protocol/src/ncdrequestbase.cpp) appends optional **configuration, cookies, query responses**, and then the `browse` request element.
- [`CNcdLoadNodeOperationImpl::CreateRequestLC()`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/server/src/ncdloadnodeoperationimpl.cpp) gives the folder's metadata ID, `includeMetaData=false`, `metadataDepth=1` for the child metadata load.
- [`CNcdRequestBrowseSearch::CreateRequestL()`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/protocol/src/ncdrequestbrowsesearch.cpp) writes response-filter properties matching the handset's observed child-browse shape.

Minimal **host-only reproduction**, no product-code change: an otherwise valid child request with `pageSize=2` yields `is_child_metadata_request=True`; prepending one benign `configuration` root element yields `False`, even while `v09.request_kind` classifies it as `preminet_matching_browse`. This reproduces the type of rejection without assuming which *actual* extra element(s) the E7 sent.

**Consequence:** Current evidence identifies a real v0.14 protocol gate too strict for Nokia-originated browses. It does NOT prove that sending the fictional child 200 will cause the UI to finish or that the private cache is healthy. No physical v0.14.2 experiment yet.

**Safest next design:** a bounded v0.14.2 matcher that accepts a single valid offline-root metadata `browse` with only **historically documented, explicit, harmless** companion request elements and refuses unrelated or active operation types, plus a fixed limited page-size policy justified by the browser. Continue one-shot 200 and fixed unchanged inert XML. Red/green host tests first, preserving existing v0.14.1 as baseline. Because the diagnostic does not reveal the companion element types, the live matcher must fail closed on unknown tags, log only a safe category of why it rejected, and never print client values/IDs or send active software.

No cache reset, package bytes, installer, firmware, unconstrained POST handling, uncontrolled retries or deployment recommended.
