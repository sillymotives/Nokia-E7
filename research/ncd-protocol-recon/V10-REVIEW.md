# Nokia E7: NCD protocol recon v0.10 (research review)

**Status: experimental, offline/localhost verified only. Not deployed to an E7.**

This independent NCD research package is NOT E7 Bridge v0.9 or v0.10, and is not a phone OS modification.

## Evidence

- The v0.8 physical test received a configuration request and a follow-up Preminet browse at a synthetic local URI.
- The v0.9 physical test attempted exactly two HTTP 200 responses: synthetic configuration and empty Preminet 2.0 browse. The E7 still displayed an update-check failure. Neither response attempt establishes receipt, parsing, or cache safety.
- The uploaded v0.9 archive contained 23 files and passed **198 tests** on clean extraction.
- A v0.10 local candidate preserved the v0.9 response XML bytes, route, namespace, and strict request matcher, adding sanitized **server-side socket-write completion/failure** counters. It passed **207 offline/localhost tests** after clean extraction. v0.9's responder file was verified unchanged.
- A socket-write completion establishes **only** that Python's HTTP reply function returned without an OSError. It cannot prove delivery to the Nokia process, successful XML parsing, or any particular phone-side error code.
- The v0.9 responder already used `Content-Length`, `text/xml; charset=UTF-8`, and `Connection: close`. There is no demonstrated missing-header root cause.

## Public historical source

- [NCD response parser](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/protocol/src/ncd_parser_pp_response.cpp) recognises a Preminet response with optional children.
- [Node loader](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/server/src/ncdloadnodeoperationimpl.cpp) feeds received HTTP bodies to the XML parser and can complete with no remote folders or pending queries.
- [IA Update loader](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/iaupdate/IAD/engine/controller/src/iaupdateloader.cpp) uses two expected root branches as a cache-expiration heuristic, not an unconditional response-entity minimum.
- [IA Update main view](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/iaupdate/IAD/ui/src/iaupdatemainview.cpp) distinguishes an empty success from a refresh error.

The historical source is older than the phone's reported `s60-iaupdate 2.2.0`; compatibility remains a hypothesis.

## Safety gates

Do not publish captured request XML, IMEI/IMSI, PCAPs, cache files, or user identifiers. The ROM Z: archive does **not** back up writable NCD/IAUpdate caches. No live service should be armed before independent, usable recovery of the phone's writable state is verified. Do not merge diagnostic code into firmware or phone installer paths. Do not serve downloads, catalogue products, update packages, device-management instructions, redirects or cookies.

## Intended next study

Run offline transport/error-path tests first. If and only if the backup gate is met, a separately approved single on-device trial can compare the v0.9 send-attempt counters to sanitized socket-write outcome counters, with exactly the same fixed XML and one-shot allowlist. A continued UI failure after both completed writes is *not* sufficient to identify its cause.

The actual v0.10 source package and its 207 test files were produced and checked independently in the ChatGPT workspace. This GitHub review note **does not contain the full package** and should not be mistaken for a merged or deployed release.
