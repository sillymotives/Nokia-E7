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
