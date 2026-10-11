# E7 NCD v0.13: two inert root-folder references

**Status:** built and independently tested on the ChatGPT Linux host, **not yet tested on the Nokia E7**. This PR is a public-safe review document only. It does not contain the source ZIP, does not merge software into `main`, and does not arm a listener or install a package.

## Physical observation that motivated the experiment

Owner-operated E7 tests:

- v0.10: original synthetic configuration and *empty* Preminet browse; both server-side HTTP socket writes completed; Software Update displayed an error.
- v0.11: changed only outer config expiry to five minutes; still displayed the same error.
- v0.12: restored original configuration, returned **one** inert root `FolderRef` (`offline-root`, `count=0`). Sanctuary sent one configuration 200 and one folder-browse 200 with completed server-side writes, no reported handler failures and normal one-shot shutdown. **Phone remained on the 'Checking for improvements' screen**, including more than a minute after the listener stopped. The owner eventually closed the application. No passive packet capture took place while the spinner was active. No client-side parsing/completion status was obtained.

[Historical open-source IA Update loader](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/iaupdate/IAD/engine/controller/src/iaupdateloader.cpp) contains an expiry heuristic expecting **two root gateway branches** (software and firmware). **Two folders under one synthetic source are not the same as two genuine gateways**. The historical source may also differ from the installed Belle build. This is a narrowly defined hypothesis, not a confirmed diagnosis.

## Exactly one protocol change compared with v0.12

The configuration response remains **byte-identical to v0.9/v0.10/v0.12** (including root `expirationDelta=0` and unchanged client expiry). The original v0.12 folder remains. Only a *second sibling* root `FolderRef` is added:

```xml
<preminetResponse xmlns="http://nokia.com/preminet/protocol/v/2/0"
                  namespace="urn:e7-lab:synthetic:catalogue:v09"
                  version="2.0">
  <entity type="FolderRef" id="offline-root" count="0"/>
  <entity type="FolderRef" id="offline-secondary" count="0"/>
</preminetResponse>
```

There are **no** downloads, links to packages, installers, `.sis` files, firmware, install instructions, sessions, remote catalogue URIs, metadata, children, cookies or redirects. Same private lab endpoint/path/namespace, strict request matcher, one configuration 200 plus one matching browse 200, all subsequent requests HTTP 404, same 90/45/15-second arm/browse/post windows. A second root reference may nevertheless mutate the phone's persistent private catalogue cache.

## Host verification (fresh extraction)

- Actual offline package: `e7-ncd-protocol-recon-v0.13.zip`, delivered separately in the associated ChatGPT conversation; **not pushed to this GitHub branch**.
- ZIP SHA256: `dd1c27bc099f52ea9e82807b7f9bf26c5316ed09ae3d9a4646ac5b9b8ec40973`
- Configuration SHA256 (original): `604f72517551adfb6cbe8c687be5f6cba86130846361d8b480c9dfc84e5ef310`
- New browse SHA256: `ab9d02049f17161b17b478c521cd11902d8e718ae70e9bf614e251c8e73f92bf`
- ZIP archive integrity: passed. Every one of **39** manifest-listed package files verified on a clean extraction. `python3 -m unittest discover -s tests -q` reported **236 tests passed**, comprising 224 inherited and 12 new v0.13 tests, including one-shot HTTP delivery and refusal of unapproved reply bodies.
- Independent comparison confirmed the archived v0.9, v0.10, v0.11 and v0.12 responder source files were byte-for-byte unchanged. The new `--dry-run` reported exactly two inert folders and no live network access.

## Safety and evidence limits

A socket-write completion says only that the host write function returned successfully, not that the phone parsed, accepted or successfully processed the payload. A spinner does not prove progress or a completed transaction.

**No verified backup/restoration route exists for the protected writable NCD/IAUpdate caches on the handset's C: drive.** ROM Z: and mass-memory preservation images are insufficient. No rollback function is provided. Any physical trial must be independently chosen by the owner with this risk understood; the package requires explicit `--acknowledge-cache-risk`. A passive outbound-packet metadata counter is described in `LIVE-V13.md` inside the separately delivered ZIP, to be started **while Software Update is actually checking**, not after it has been closed. Do not post raw phone requests, packet captures, identifiers or protected cache contents.

**Interpretation plan:** Observe exact screen state and whether there are additional phone-originated network connections beyond the two laboratory HTTP requests. If unchanged, do not keep retrying the same responder or introduce a dummy installer. Investigate callback, cache and gateway-model differences before changing further payload fields.

## Physical E7 v0.13 outcome (operator report, 2026-10-11)

Operator ran the previously distributed v0.13 two-inert-folder listener and reported: **the server ended normally, while Nokia Software Update was still spinning**. The operator has now supplied the sanitized v0.13 `RESULT` counters; **no contemporaneous passive traffic count has been supplied**. Do not invent counters or assume a successful parse. This is the same **observable symptom** as the one-folder v0.12 trial: the extra sibling folder **did not resolve** the persistent checking UI in this trial.

The historical “two root children” heuristic is not the same as two root references served by one synthetic content source. The fact that this variant also spins neither proves nor excludes different gateway topology as a later dependency; it provides no basis for adding a dummy SIS. The immediate diagnostic is a brief **passive-only traffic count while the spinner remains active**; verify that the previously known phone DHCP address and hotspot interface are still correct before interpreting zero packets. A lack of observed traffic during one short window can support, but cannot prove, an internal outstanding callback/cache/operation hypothesis. No further arming or payload mutation is recommended until this boundary is understood.

### Sanitized v0.13 listener outcome (additional owner-provided evidence)

- `configuration_200_attempted=true`, `configuration_response_socket_write_completed=1`, `configuration_response_socket_write_failed=0`.
- `two_folder_preminet_200_attempted=true`, `folder_preminet_200_attempted=true`, `browse_response_socket_write_completed=1`, `browse_response_socket_write_failed=0`.
- `preminet_response_contained_two_inert_folders_without_downloads=true`, `preminet_response_contained_one_inert_folder_without_downloads=false`, `empty_preminet_200_attempted=false`.
- `handler_failures=0`, `other_response_write_failures=0`, `configuration_retries_after_one_shot=0`, `matching_browse_retries_after_one_shot=0`, `other_post_request_count=0`, `other_preminet_browse_count=0`, `preminet_nonbrowse_request_count=0`, `wrong_namespace_probe_browse_count=0`.
- `server_shutdown_reason=post_browse_observation_complete`; `no_client_parse_ack=true`, `socket_completion_is_not_phone_parse_ack=true`.

**Scope:** This excludes reported host socket-write failures and unmatched requests to the *armed listener during its bounded observation*, but does **not** establish a parsed catalogue, complete update refresh, absence of other network traffic, or cache safety. The E7 UI still spun after shutdown. Next discriminator remains passively observing outbound packets while the spinner is active, on the confirmed phone IP and hotspot interface. No v0.14 payload change is justified yet.
