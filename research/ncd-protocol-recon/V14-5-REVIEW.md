# E7 NCD v0.14.5: installed-owner-test-probe metadata-only hypothesis

**11 October 2026. Host-verified candidate only. No handset run has occurred.** This is a **documentation-only GitHub review note**. The independently tested full responder ZIP was delivered to the owner in ChatGPT, **not committed here**, and contains no executable Symbian package, installed app data, private registry inventory, ROM image, personal identifiers, or update/download payload.

## Question and evidence

Could the still-blank, permanently checking E7 Software Update screen be because the fictional catalogue entry is **not an update to an installed application**?

Historical Nokia IAUpdate source argues against that requirement as a universal rule. [`CIAUpdateNodeContainer::AddNodeL`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/iaupdate/IAD/engine/controller/src/iaupdatenodecontainer.cpp#L83-L129) evaluates platform acceptance, installed-version criteria, package type, duplicate and embedded dependency conditions, **but an SA package does not inherently require a prior installation**. [`InstallCheckL`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/iaupdate/IAD/engine/controller/src/iaupdatenodecontainer.cpp#L1050-L1105) excludes candidates *older* than installed, forces *equal* versions hidden, and permits *strictly newer* versions through that gate. Other metadata and dependency/UI gates remain.

[`IAUpdateUtils::IsAppInstalledL`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/iaupdate/IAD/engine/controller/src/iaupdateutils.cpp#L267-L297) calls [`AppPackageUidL`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/iaupdate/IAD/engine/controller/src/iaupdateutils.cpp#L169-L263), which first tries SID-to-package lookup then a direct package UID registry lookup. Thus an installed **data-only SIS test package** can satisfy the historical installed-version check without an executable SID. This is historical source, not an actual Belle `IsAppInstalledL` trace.

A **read-only saved native SIS registry inventory** from 2026-10-11 identifies the previously deployed owner-created `E7 Deployment Probe`, **package UID `0xE94B7002`, version `0.1.0`**. Its installed identity and version must be reconfirmed by the owner before any hardware trial. We deliberately do **not** use an essential app, Bridge, a Nokia system package, or any third-party identity.

## Controlled v0.14.5 change

Compared with **exact** v0.14.4 stage-three `preminetResponse` XML, the v0.14.5 child `downloadableContent` changes **two attributes only**:

| Field | v0.14.4 | v0.14.5 |
| --- | --- | --- |
| `id` | `E7A01444` invented development UID | `E94B7002` owner's already installed data-only deployment probe |
| `version` | `0.0.1` | `0.1.1`, deliberately newer than installed `0.1.0` |

**Byte-identical:** v0.14.4 config and two-folder root with one inert `FolderData`, and every child XML element/attribute other than the two above. The child remains `x-epoc/x-sisx-app`, **size zero**, `application` content purpose, package type `SA`, importance `normal`, fixed fictional title, and **no installation/download/purchase endpoint, SIS/SISX binary, URI, signature, or executable**. The class name and one-shot handler version change host-side only; authorization gates, host/source allowlist, time bounds, HTTP framing, and reply counts are inherited unchanged from v0.14.4.

Only one allowed HTTP 200 each for configuration, root, and guarded child metadata; retries, downloads and all other paths get 404. **The source does not make an installed package updatable**, and this research variant is not installable.

## Host verification (2026-10-11)

- Final clean ZIP name: `e7-ncd-protocol-recon-v0.14.5.zip`; SHA-256: `2acf5f93493066b300568ad46634046ca55da6abfa058e059b967cce641d419b`.
- **331 individual tests passed across 18 independent test modules** (318 inherited + 13 new), including strict XML allowlist, wrong UID/version/size/URI rejection, socket-level status/body/header comparison with v0.14.4, attempts to download resulting in 404, required explicit risk/identity confirmations and fixed request acceptance.
- ZIP has **64 files**, including **63 SHA256SUMS entries**. CRC check passed and extracted SHA256SUMS all matched. An independently fresh extraction passed the 13 new tests and 12 inherited v0.14.4 tests.
- All **58 inherited Python/XML/documentation files except intentionally extended README** remain byte-for-byte unchanged from the verified v0.14.4 ZIP. Only v0.14.5 source, tests, release notes, live instructions, README and checksum manifest differ.
- Configuration and root 200 response bytes match v0.14.4; only stage-three 200 body and its required `Content-Length` differ.
- Child body SHA-256: `ffc79b6ad07ae18b37653f7833135596b3cb40dc503b217e0c1889cc4f14785b`. This is a host byte fingerprint, **not a handset parser ACK**.

## Physical-risk and stop gates

An optional **single** owner-operated E7 test is described in the separately delivered `LIVE-V145.md`, requiring exact installed-test-probe identity confirmation, explicit acknowledgement that protected writable NCD/IAUpdate caches **can change with no verified rollback**, an isolated hotspot, SIM removed and mobile data disabled. The server is one-shot/bounded and no true installer is served. This note **does not document a completed hardware result**.

A matching installed UID/version may plausibly change *visibility eligibility*, but **is not a proven prerequisite** and does not by itself supply `THTTPEvent::ESucceeded`, NCD parser `EndL`, `NodesUpdated/Continue` IPC, `CIAUpdateLoader::LoadComplete` or UI `RefreshComplete`. If the still-spinning blank list persists after the owner's voluntary test, **stop further synthetic-catalogue changes** and retain the offline completion-path analysis. If a fictional item appears, **do not select, download or install** it.

**PR scope:** docs only, draft/open/unmerged, no changes to `main`, no new device operations by the author.
