# Nokia E7 NCD: v0.12 inert-root-folder experiment

**Status: offline and localhost verified; physical one-shot E7 test has now been reported (UI stayed on checking screen).** This branch is a review note, not a deployed update service. The complete source ZIP was produced separately in the owner's ChatGPT conversation and has SHA256:

`54e6df1199314a9841af884226b2dbdc2d762aabeb92443aaa57a41802d4146c`

## Motivation / v0.11 physical outcome

On 2026-10-11 the user ran the one-variable v0.11 root-expiry trial. Outer root `expirationDelta=5` with the original **empty** browse response still yielded the *same Software Update failure*. Sanctuary saw exactly one matching configuration request and one matching browse, with one completed server socket write for each (no failed writes, no handler errors). The listener disarmed normally. Thus a five-minute expiry does not resolve the observable issue, and no client-side parse acknowledgement has yet been observed. See [draft PR #14](https://github.com/sillymotives/Nokia-E7/pull/14).

## What is proposed and independently tested

Return the configuration **byte-identical to v0.9/v0.10**, including both zero-minute expiry settings. On the second one-shot Preminet browse response, provide *one and only one* synthetic root folder:

```xml
<preminetResponse xmlns="http://nokia.com/preminet/protocol/v/2/0"
                  namespace="urn:e7-lab:synthetic:catalogue:v09"
                  version="2.0">
  <entity type="FolderRef" id="offline-root" count="0"/>
</preminetResponse>
```

The exact `id` matches the `contentSources` source ID and the response namespace matches its configured namespace. No remote `uri`, product metadata, descendants, session, downloads, firmware, installer, updates, redirects or cookies. This **can** cause a new catalogue node to be written to the handset's private NCD cache; calling it "inert" describes its *contents*, not an absence of side effects.

Historical Nokia source grounding:

- [NCD Preminet top-level parser](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/protocol/src/ncd_parser_pp_response.cpp): recognizes top-level entity references.
- [NCD entity ref parser](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/protocol/src/ncd_parser_pp_entityref.cpp): recognizes `FolderRef`, root-level parent and response namespace fallback.
- [NCD content-source loader](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/server/src/ncdloadnodeoperationimpl.cpp): handles and inserts root folder references.

This historic code predates the exact installed Belle IAUpdate version; validation on the handset remains unknown.

## Verification evidence

The independently created v0.12 ZIP was extracted into a clean directory and verified with its `SHA256SUMS.txt` manifest. Then **224 Python `unittest` tests passed**, including nine new folder tests; the offline `--dry-run` completed. Tests assert exact v0.9 configuration bytes, exactly one folder, count zero, identity/namespace match, no active/download features, 200→200→404 over localhost, TCP length/close headers, completed-write receipts, 404 on unrelated requests, sanitized logs and refusal to arm without explicit cache-risk acknowledgement. The frozen v0.9/v0.10/v0.11 responder sources were rechecked byte-identical to the prior package.

- Config SHA256 (unchanged): `604f72517551adfb6cbe8c687be5f6cba86130846361d8b480c9dfc84e5ef310`
- New browse SHA256: `b9a96648668713e4535fab1e32ea42ac7fee21d2ef4c3984e482f6c68da548d5`
- ZIP SHA256: `54e6df1199314a9841af884226b2dbdc2d762aabeb92443aaa57a41802d4146c`

**This PR does not contain or install the independently tested ZIP.** The authoring environment is separate from the GitHub connector. The note is intended as review documentation, not a claim of GitHub-hosted application source.

## Experimental limits

All original one-shot limits remain: at most one synthetic configuration 200 followed by one matching Preminet 200, 404 to all other requests, same bound 90/45/15-second windows. A new sanitized `matching_browse_retries_after_one_shot` counter can indicate a repeated browse. A subsequent request that gets 404 could indicate a deeper client stage; it does **not** imply success. A persistent error screen alone is ambiguous.

Protected writable `C:` NCD/IAUpdate data still lacks a verified backup and restoration route. `Z:` ROM and mass-memory captures do not protect it. **No phone-side rollback exists.** Do not publish raw E7 request bodies, identifiers, packet captures or cache contents. No wider catalogue, download, firmware, modification of phone OS or subsequent live trial is authorized by this documentation.

## Physical v0.12 observation (owner-reported, 2026-10-11)

The E7 was given the original v0.9 configuration and a single `offline-root` `FolderRef` (`count=0`) on a private lab hotspot. The operator reported a **changed UI outcome:** Software Update **remained on the "Checking for improvements" screen** rather than immediately showing the same failure as v0.10/v0.11. The precise duration and eventual outcome have not yet been measured. This is evidence that the folder variant affects observable behaviour, **not proof** the handset accepted or cached it.

Sanitized listener results: `configuration_response_socket_write_completed=1`, `browse_response_socket_write_completed=1`; zero write failures, zero handler failures, zero matching-browse retries and zero other counted browse/POST requests **at this listener**. `server_shutdown_reason=post_browse_observation_complete`. The probe observes **15 seconds after the matching browse** by default; it cannot see later attempts after exiting, another server's traffic, device-side parse errors, or its private database.

The historical [IAUpdate loader](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/iaupdate/IAD/engine/controller/src/iaupdateloader.cpp) chains root loading to container/child handling, and [NCD load-node operation](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/server/src/ncdloadnodeoperationimpl.cpp) separately receives the HTTP body, completes the XML parse, and advances its operation. A completed server socket write alone cannot distinguish a waiting client, broken parser/callback, cache operation, or external follow-up connection.

**Next action should be observation, not adding an installable SIS.** First determine whether the spinner remains after the listener shuts down, the elapsed time, and whether the E7 makes follow-up DNS/TCP requests to *any* destination during the spinner (locally inspect or sanitize packet metadata; never publish raw captures). Then consider a deliberately bounded second-stage catalogue response or metadata-only item **if actual follow-up evidence warrants one**. A dummy `.sis` is a new installation/signature/trust risk and does not diagnose why a catalogue query has failed to complete. No additional live trial is authorised by this note.
