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

Standalone experiment: e7-ncd-protocol-recon-v0.8.zip (conversation artifact, NOT stored in this repo). Contains ncd_catalogue_probe_v08.py, LIVE-V08.md and earlier read-only inspectors. **135 offline/localhost tests passed after a clean ZIP extraction**, plus successful privacy-preserving classification of the owner's previously captured E7 configuration request. No v0.8 crafted response has yet been sent to the real phone.

## Interpretation

- Initial configuration POST receives the single 200: a matching physical request reached the harness.
- E7 follows with a Preminet 2.0 browse at the lab path (receiving 404): would demonstrate the live configuration-to-browse transition.
- E7 does not browse: inconclusive; could be caching, response rejection, a different endpoint or Belle-specific differences.
- A phone message "Unable to check for updates" is unsurprising because no real catalogue is served, but does not on its own prove a specific parser outcome.

This is a draft research checkpoint. Do not merge to main or deploy anything to production based solely on these tests. Preserve only sanitised logs and observed UI text; keep private request XML and PCAP files out of GitHub.
