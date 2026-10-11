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

## Offline Preminet 2.0 browse-stage reconstruction (v0.4)

**User verification:** the standalone v0.3 package completed 11 unit
tests, and its offline synthetic `configurationResponse` produced one
candidate content source with no actions, cookies, or errors.
**This is not evidence that Belle accepted a server response.**

Source tracing now identifies a distinct follow-on protocol:

- [Preminet request constants](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/protocol/inc/ncdrequestconstants.h):
  `http://nokia.com/preminet/protocol/v/2/0`, version `2.0`.
- [Browse request generator](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/protocol/src/ncdrequestbrowsesearch.cpp):
  `preminetRequest` with `browse`, optional `entity` references, and
  `responseFilter` / `entityFilter`.
- [Content-source node operation](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/server/src/ncdloadnodeoperationimpl.cpp):
  for an ordinary, nontransparent content source, sets
  `pageSize=1`, `pageStart=0`, `structureDepth=1`,
  `metadataDepth=0`, `metadataPerLevel=1`.
- [Preminet response parser](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/protocol/src/ncd_parser_pp_response.cpp):
  `preminetResponse` recognizes immediate `entity`, `embeddedData`,
  `purchase`, `subscriptionReport`, `information`, `error`.
- [Entity reference parser](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/protocol/src/ncd_parser_pp_entityref.cpp):
  interprets `FolderRef`, `ItemRef` and `ActionRef`.

Three **offline-only synthetic fixtures** and seven independent static
tests now live alongside the configuration fixture:

- [Browse](../bridge/e7-bridge/tests/fixtures/ncd-preminet-browse-OFFLINE-ONLY.xml)
- [Empty response](../bridge/e7-bridge/tests/fixtures/ncd-preminet-empty-response-OFFLINE-ONLY.xml)
- [Folder reference response](../bridge/e7-bridge/tests/fixtures/ncd-preminet-folder-response-OFFLINE-ONLY.xml)
- [Tests](../bridge/e7-bridge/tests/test_ncd_preminet_fixture.py)

A self-contained v0.4 downloadable lab package also extends the
privacy-preserving inspector to recognize both NCD Configuration 1.0 and
Preminet 2.0 documents. It has **22 passing tests in the assistant's
offline container**, including regressions protecting against disclosure
through invented element names. No real E7 Preminet traffic has yet been
seen, and no response has been served to the E7.

The fake folder and content-source data **would potentially modify client
state or trigger network lookups if served**. Keep the laboratory endpoint
returning HTTP 404 until there is a separately agreed, reversible live
test. No updates, signing-policy changes, redirects, or client actions
were performed in this stage.

## Offline metadata-stage reconstruction (v0.5)

**Owner verified v0.4:** All 22 standalone tests passed on Sanctuary.
The synthetic browse request was reported as one `browse`, one entity and
one response filter. The synthetic folder reply was reported as one
`FolderRef`. No on-device response was attempted.

Subsequent source tracing identified richer metadata in the Preminet
response's `embeddedData` child:
- [Embedded-data parser](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/protocol/src/ncd_parser_pp_embeddeddata.cpp):
  routes `dataEntity` and `actionEntity` to the data-entity parser.
- [Data-entity parser](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/protocol/src/ncd_parser_pp_dataentity.cpp):
  distinguishes `FolderData` and `ItemData` and handles `name`,
  `description`, `downloadableContent` and `details`.
- [Content metadata parser](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/protocol/src/ncd_parser_pp_dataentitycontent.cpp):
  reads `mime`, `id`, `size` and `version` attributes.
- [IAUpdate protocol constants](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/iaupdate/IAD/engine/controller/inc/iaupdateprotocolconsts.h):
  interprets `iaimportance`, `iatype`, `iasearchcriteria`,
  `iadependencies`, firmware version keys and reboot flags, plus
  distinctive service-pack/FOTA/widget MIME types.
- [IAUpdate node factory](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/iaupdate/IAD/engine/controller/src/iaupdatenodefactory.cpp):
  uses content info MIME to distinguish firmware and service-pack nodes.

The synthetic metadata fixture, at
[**ncd-preminet-metadata-OFFLINE-ONLY.xml**](../bridge/e7-bridge/tests/fixtures/ncd-preminet-metadata-OFFLINE-ONLY.xml),
contains a fake `FolderData`, a fake `ItemData`, **zero-byte**
`downloadableContent` metadata, and purely illustrative
`iaimportance=normal`, `iatype=SA`. There is **no URI, SIS, update
payload, purchase, redirect or executable action**.
Eight [standalone static tests](../bridge/e7-bridge/tests/test_ncd_preminet_metadata_fixture.py)
check this GitHub fixture's shape and privacy constraints.

The accompanying standalone v0.5 privacy-preserving inspector recognizes
this metadata without echoing arbitrary names, IDs, URI values or contents.
**32 standalone tests passed in the assistant's offline container**
(including the previous 22 tests plus 10 new metadata/privacy cases).
It was separately regression-tested against the original private E7
configuration request. That private request is **not** in the ZIP/repo.

As before, all reported classifications concern **historical source
syntax and local fixtures**, not authenticated modern server traffic or
Belle IAUpdate 2.2.0 acceptance. In particular,
`downloadableContent` XML metadata **does not prove a downloadable or
installable package exists**. Do not serve any fixtures to the real phone.

## Offline IAUpdate eligibility-gate investigation (v0.6, 2026-10-11)

**User verified v0.5** on Sanctuary: 32 tests passed; the metadata
fixture reported `FolderData=1`, `ItemData=1`, one synthetic
`downloadableContent` metadata block and **zero URI attributes**.

Further investigation of the original **IAUpdate 2.1.0** source:

1. [NodeContainer: `AddNodeL`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/iaupdate/IAD/engine/controller/src/iaupdatenodecontainer.cpp) requires:
   no duplicate, acceptable platform, installed-state/version check,
   no degrading embedded dependencies, and a valid package type.
2. [Platform dependency](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/iaupdate/IAD/engine/controller/src/iaupdateplatformdependency.cpp):
   optional `S60` platform name and **inclusive major/minor** bounds;
   the platform comparison ignores build number.
3. [`InstallCheckL`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/iaupdate/IAD/engine/controller/src/iaupdatenodecontainer.cpp):
   installed version newer than candidate is rejected; equal-version
   ordinary candidates are retained, but force-hidden for dependency
   information. MIME-defined service packs are handled separately.
4. [`PackageTypeAcceptedL` and `ReplaceRecommendedL`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/iaupdate/IAD/engine/controller/src/iaupdatenodecontainer.cpp):
   `SA`, MIME-defined service packs and widgets skip the installed-base
   upgrade requirement. `PU` and `SP` require a **same-UID installed base**
   satisfying a declared dependency version interval. For matched,
   accepted ordinary candidates the preferred version is newer; at equal
   version and when the new leaf-distance is no longer, the packet
   preference is `PU > SP > SA`. Do **not** conflate `SP` packet type
   with service-pack MIME `application/x-arrow-metapackage`.
5. [Recursive dependency resolution](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/iaupdate/IAD/engine/controller/src/iaupdatenodecontainer.cpp):
   installed nodes and eligible candidate nodes can satisfy dependencies;
   recursive cycles and unsatisfied requirements fail; broken candidates
   are removed when the head list is built. Bundle/self-update special
   cases are **not** represented in the toy model.
6. [Embedded downgrade check](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/iaupdate/IAD/engine/controller/src/iaupdatenodedetails.cpp):
   a newer installed embedded component can block a candidate.
7. [UI `MarkFilterNodeL`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/iaupdate/IAD/ui/src/iaupdatenodefilter.cpp):
   without caller-specific search/UID filters, normal-priority entries
   are not preselected while non-normal visible entries normally are.
   **Selection is not eligibility**, and it never establishes that a
   package is safe or installable. Device-management/FOTA handling is
   a different conditional path.

For reproducibility, the draft branch now contains a standalone,
**offline-only fictitious-candidate illustration**
[`iaupdate_eligibility_recon.py`](../bridge/e7-bridge/tools/iaupdate_eligibility_recon.py)
and its [unit tests](../bridge/e7-bridge/tests/test_iaupdate_eligibility_recon.py).
The associated self-contained standalone v0.6 lab bundle carries the
earlier privacy-preserving NCD/Preminet inspector, 17 invented
eligibility scenarios and **68 passing tests on a clean extraction**
(32 older + 36 new). It also passed a local privacy regression against the
owner's original private configuration request without exposing
identifying attributes.

**Scope limits:** The simulator does not accept phone data, contact a
network, serve protocol responses, resolve arbitrary dependency graphs,
emulate firmware updates, or install anything. Its `hypothetical_head_stage`
is a reasoned *illustration* of selected historical code paths, not a
prediction of the physical E7's update list. The actual device reports
`s60-iaupdate 2.2.0`, while the archived source identifies version
`2.1.0`. The original private XML remains outside this repository.
Continue returning HTTP 404 from the lab server.
