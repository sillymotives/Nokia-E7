# E7 NCD v0.8: one-shot synthetic content-source discovery

**Status:** Standalone harness packaged and locally tested. The new physical E7 content-source response has NOT yet been tested. In the earlier v0.7 live test, one source-free configurationResponse was delivered with HTTP 200, and the E7 displayed "Unable to check for updates". That did not establish parser acceptance.

## Objective

Test whether Belle IAUpdate 2.2.0 progresses from a Nokia NCD Configuration 1.0 configurationRequest to a Preminet 2.0 browse POST after receiving one synthetic contentSources descriptor. [Historical NCD root loader](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/server/src/ncdloadrootnodeoperationimpl.cpp) loads one node operation per configuration content source; [Preminet browse code](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/protocol/src/ncdrequestbrowsesearch.cpp) constructs subsequent browse requests.

Version caveat: the public source is IAUpdate 2.1.0, while the real E7 reports 2.2.0.

## Safeguards

- Exactly one configuration response (HTTP 200) after a valid request from 10.42.0.85, directed to the original master host and POST /.
- Exactly one synthetic content source: namespace urn:e7-lab:synthetic:catalogue:v08 and URI http://10.42.0.1/__sanctuary_e7_v08_content_probe. This is a private numeric address, not a public Nokia endpoint.
- All subsequent requests, including a matching Preminet browse at the probe path, receive HTTP 404. There are NO catalogue entries, downloads, packages, firmware, redirects, actionRequests, cookies, queries, messages or serverDetails.
- The one-shot disarms before transmitting. It auto-exits after a 90-second initial arming window or 45 seconds of follow-up observation.
- Sanitized, allowlist-only logging avoids IMEI, XML body, phone identifiers, arbitrary URLs and session data.
- Explicit --acknowledge-cache-risk flag required to arm. --dry-run has no network activity.
- IMPORTANT: Nokia's writable NCD cache can be altered during an update check. The test has no automatic phone-side rollback; a verified independent writable-data backup is required. A ROM dump does not cover this.

Standalone experiment: e7-ncd-protocol-recon-v0.8.zip (conversation artifact, NOT stored in this repo). Contains ncd_catalogue_probe_v08.py, LIVE-V08.md and earlier read-only inspectors. **135 offline/localhost tests passed after a clean ZIP extraction**, plus successful privacy-preserving classification of the owner's previously captured E7 configuration request. The v0.8 live test was subsequently performed; see the physical-device result below.

## Interpretation

- Initial configuration POST receives the single 200: a matching physical request reached the harness.
- E7 follows with a Preminet 2.0 browse at the lab path (receiving 404): would demonstrate the live configuration-to-browse transition.
- E7 does not browse: inconclusive; could be caching, response rejection, a different endpoint or Belle-specific differences.
- A phone message "Unable to check for updates" is unsurprising because no real catalogue is served, but does not on its own prove a specific parser outcome.

This is a draft research checkpoint. Do not merge to main or deploy anything to production based solely on these tests. Preserve only sanitised logs and observed UI text; keep private request XML and PCAP files out of GitHub.

## Physical E7 result (operator report, 2026-10-11)

**Result: live configuration-to-browse transition confirmed.**
The operator ran `ncd_catalogue_probe_v08.py` on Sanctuary's lab AP
and provided the **sanitized server terminal output**, which reported:

- `MATCH: real E7 configurationRequest; one synthetic source response (HTTP 200).`
- `DISARMED: every later request gets HTTP 404 until auto-shutdown.`
- `OBSERVED: E7 Preminet 2.0 browse at isolated probe path; returning HTTP 404.`
- `one_synthetic_configuration_response_sent: true`
- `preminet_browse_seen: true`
- `preminet_browse_at_exact_probe_path: true`
- `configuration_retries_after_one_shot: 0`
- `preminet_nonbrowse_requests: 0`
- `other_post_requests: 0`
- `other_requests_and_all_followups_received_only_404: true`
- `source_parameters_or_private_identifiers_logged: false`
- `update_payloads_or_catalogue_entries_served: false`
- `server_shutdown_reason: operator_stopped`

The E7 screen still displayed **"Unable to check for updates"**.

### Interpretation

The exact synthetic probe path, which was supplied only in the crafted
configuration response, was used for a subsequently recognized Preminet
browse request. This strongly confirms that the physical E7 processed
the `contentSources` description and attempted the follow-on
Configuration 1.0 -> Preminet 2.0 transition. It is substantially stronger
evidence than the earlier empty-envelope HTTP 200 experiment.

The on-screen error is consistent with the intentionally hardcoded
**HTTP 404 on the browse stage**. It is not a failed configuration-to-browse
test and does not tell us whether Nokia would accept an empty or populated
Preminet browse response.

**No content catalogue, package, application installer, or firmware was
offered.** No on-phone cache backup or restoration is inferred from this
log; local cache safety has NOT been established. Only the observed
protocol transition is confirmed.

### Next cautious gate

After confirming a usable backup of the phone's **writable** NCD data,
the next experiment could use a single-use, strictly validated **empty**
Preminet 2.0 `preminetResponse` for the matching browse request, rather
than a 404. This is a **new potential cache-mutating live experiment** and
must be reviewed separately with one-shot, bound-source, safe-logging,
and expiry tests. Do not interpret the screen message as proof of
successful update service restoration. Avoid any actual catalogue
entities, embedded data, downloads, cookies, action requests, redirects,
or installable payloads.
