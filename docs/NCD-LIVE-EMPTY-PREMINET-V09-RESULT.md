# Nokia E7: v0.9 empty Preminet response live result

**Date:** 2026-10-11
**Status:** Physical-device experiment completed; HTTP two-stage exchange confirmed from server logs. Parser acceptance, catalogue completion, cache safety and real update availability are **NOT proven**.

## Experiment and safeguards

The standalone v0.9 conversation artifact `e7-ncd-protocol-recon-v0.9.zip` provided `ncd_empty_browse_v09.py`, which was independently tested offline with **198 successful unit tests** before the operator ran it on the E7 lab hotspot.

The server was armed for a maximum of two fixed HTTP 200 responses:

1. A matching E7 Configuration 1.0 `configurationRequest` received a synthetic, isolated single-content-source `configurationResponse`.
2. A matching Preminet 2.0 `preminetRequest/browse` at the v0.9 probe path and namespace received an **empty** `preminetResponse` envelope.

All other requests while listening were configured to receive HTTP 404. No entity, catalogue item, download URL, SIS package, FOTA payload, actionRequest, cookie, redirect, message, or firmware was served. The lab software does not implement a rollback of the phone's writable NCD cache; backup coverage remains unverified from this log.

## Sanitized physical E7 results (operator-provided)

- `configuration_200_attempted: true`
- `matching_browse_seen: true`
- `empty_preminet_200_attempted: true`
- `preminet_response_contained_no_entities_or_downloads: true`
- `all_other_requests_while_listening_receive_http_404: true`
- `configuration_retries_after_one_shot: 0`
- `other_post_request_count: 0`
- `other_preminet_browse_count: 0`
- `preminet_nonbrowse_request_count: 0`
- `wrong_namespace_probe_browse_count: 0`
- `no_device_identifiers_or_raw_requests_logged: true`
- `server_shutdown_reason: operator_stopped`

The Nokia screen **still displayed "Unable to check for updates"** (operator description: "Same unable to get update").

The server's `200_attempted` fields are instrumentation of attempted responses, **not a client-side parse acknowledgement**. The observed browse at the exact synthetic path is strong evidence that the configuration source was processed. The empty browse response is not independently acknowledged by the Nokia client; the same screen message admits multiple causes.

## Historical-source follow-up

Original [NCD node loader](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/server/src/ncdloadnodeoperationimpl.cpp):
- `CNcdLoadNodeOperationImpl::ParseCompleteL` transitions to `EComplete` when there is no parser error, pending query or remote folder. **The historical node loader does not explicitly require at least one entity merely to complete this stage.**
- `HandleHttpError` marks a failed content source as broken; `ParseError` moves to `EFailed`. Thus an empty 200 and a browse-stage 404 have potentially different internal effects, even if both show the same UI message.

Original [IAUpdate loader](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/iaupdate/IAD/engine/controller/src/iaupdateloader.cpp):
- `CIAUpdateLoader::RootExpiredL` contains the explicit comment **"2 here means arrow CGW and firmware CGW"**, and regards an initialized root with a child count other than two as expired, prompting another refresh.
- This makes v0.9's **one synthetic source, zero data entities** insufficient evidence of a successful update-catalogue workflow. It **does not** conclusively establish why the actual E7 displayed its error, nor whether the v0.9 response parsed correctly.

**Source-version caveat:** The source corresponds to older IAUpdate (2.1.0 in its constants), whereas the real handset's configuration request reports `s60-iaupdate 2.2.0`. Do not equate every source branch with proven handset behavior.

## Recommendation before v0.10

1. Do not repeat the v0.9 live test merely to seek a different screen message.
2. Investigate offline the two-gateway assumption and whether a sterile folder reference would be required to establish root children without metadata, package links or downloads.
3. Before attempting any further potentially state-changing response, verify that writable NCD data and other important phone data are backed up and that restoration is possible. The existing ROM image alone is not enough.
4. Any future live harness must stay one-shot, local-IP-bound, explicitly acknowledged, expiry-controlled, deny-by-default, and privacy-preserving. Keep real installable content out of scope.

**GitHub scope:** Draft PR #10 research branch only; no main merge, no deployment, no raw private XML or identifiers.
