# Nokia E7: NCD configuration-response reconnaissance

Physical capture + historical Symbian source investigation on 2026-10-11.
**Read-only protocol research only.** No Nokia DNS, FOTA, installation
policy, client configuration or firmware state is changed by this document.

## Observed on real Nokia E7

- The original updater resolves `arrowcdb.ncd.nokia.com` on an owner-only
  laboratory Wi-Fi and sends `POST / HTTP/1.1` to the locally substituted
  address. An inert HTTP 404 was observed in reply.
- A private 2,085-byte POST body parses as XML root
  `configurationRequest` in namespace
  `http://nokia.com/preminet/protocol/configuration/v/1/0`, with
  `version="1.0"` and `type="preminet"`.
- The request advertises `s60-iaupdate` version `2.2.0`,
  `installationReport` and `downloadReport` capabilities,
  and a second `vanilla` software descriptor.
- **The raw XML includes an IMEI and other identifying attributes.** Never
  commit the raw POST body, private PCAPs, client identifiers or credentials
  to public GitHub.

## Historical upstream code found

Original Symbian code survives in
[SymbianSource/oss.FCL.sf.mw.appinstall](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall)
at commit `760927eba63e3324cceee974b9ed582da90cb9a3`:

1. [Top-level parser](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/protocol/src/ncdtoplevelparser.cpp):
   selects the configuration parser for `configurationResponse`, and a
   different Preminet parser for `preminetResponse`.
2. [Configuration-response parser](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/protocol/src/ncd_parser_cp_response.cpp):
   root attributes `version`, `expirationDelta`; recognized immediate
   children `clientConfiguration`, `message`, `details`,
   `actionRequest`, `error`, `serverDetails`. This list reflects parsing
   code, not a formally published XML schema or guaranteed requirements.
3. [Client configuration parser](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/protocol/src/ncd_parser_cp_clientconfiguration.cpp):
   processes `cookies` and recursively nested `details`.
   [Detail parser](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/protocol/src/ncd_parser_cp_detail.cpp)
   reads `id`, `value`, `groupId`, `label` and `content` pairs.
4. [NCD root loader](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/server/src/ncdloadrootnodeoperationimpl.cpp):
   checks `detail id="contentSources"`, nested `detail id="namespace"`
   and `detail id="uri"`. Without any content sources or bundle folders,
   the initial root-load path fails with `KNcdErrorNoContentSources`.
5. [IAUpdate loader](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/iaupdate/IAD/engine/controller/src/iaupdateloader.cpp):
   Software Update itself obtains NCD root nodes and starts NCD root loads.
6. [Default protocol observer](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/protocol/src/ncdprotocoldefaultobserverimpl.cpp):
   can persist a changed master-server address after certain
   `actionRequest` responses. Do not include actions or cookies in a
   harmless response-shape experiment.

**Version caveat:** this public [IAUpdate source](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/iaupdate/IAD/engine/controller/inc/iaupdatectrlconsts.h)
reports client version **2.1.0**, but the owner's E7 reports **2.2.0**.
Treat parser and loader findings as historical design evidence, not
automatically identical behavior on the Belle binary.

## Experimental sequence, not executed

Captured `configurationRequest` -> source-supported
`configurationResponse` envelope -> client-specific source/catalogue
discovery -> separate Preminet browsing protocol -> package metadata.
Only the **first** network transition has been proven on the E7.
The remaining arrows are architectural hypotheses informed by older code.

An empty `configurationResponse` XML envelope is suitable only as an
**offline fixture**: it would not supply a catalogue to the historical
root loader, and its effect on the physical Belle client is unverified.

**Next gate:** inspect the source's full response and content-source parsing
rules, create static privacy-safe fixtures, test them offline, then plan an
explicitly approved, reversible isolated-network experiment. Do not
enable automatic updates, issue redirects, offer SIS packages, modify FOTA or
change installer certificate checks.

## Offline fixture milestone (2026-10-11, v0.3)

The v0.2 privacy-preserving request/response-shape inspector completed all
six local unit tests and correctly summarized the owner's E7 request without
printing sensitive values. The v0.3 standalone offline lab package retains
the same inspector, adds a source-backed synthetic `contentSources` tree,
and passes **11 local standard-library unit tests**.

The canonical, synthetic fixture and its independent static tests are now
in this draft branch:

- [Fixture: ncd-config-response-OFFLINE-ONLY.xml](../bridge/e7-bridge/tests/fixtures/ncd-config-response-OFFLINE-ONLY.xml)
- [Fixture tests](../bridge/e7-bridge/tests/test_ncd_response_fixture.py)

The nested structure follows
`configurationResponse/clientConfiguration/details/detail[id=contentSources]/detail[id=namespace]/detail[id=uri]`,
with parser-defined `content` pairs (`provider`, `id`,
`alwaysVisible`, `transparent`). The catalogue hostname is deliberately
`catalogue.invalid`. It contains **no raw device identifiers**, server
actions, cookies or package payloads.

`candidate_source_entries = 1` is only a static source-shape result.
Even this seemingly inert fixture would be **potentially state-changing if
served to a real client**. **Do not serve it to the Nokia.** The local HTTP
404 remains the safe baseline until a separate, explicitly approved,
reversible protocol-response experiment is designed.

**Remaining uncertainties:** Nokia's authentic server response, whether
Belle IAUpdate 2.2.0 matches the older 2.1.0 source, the actual catalogue
addressing conventions, the subsequent Preminet browse request and any
firmware-package policy.
