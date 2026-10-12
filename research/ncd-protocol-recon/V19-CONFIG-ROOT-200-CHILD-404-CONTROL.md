# E7 NCD v0.19: original configuration + root 200, guarded child 404

**12 October 2026 | Prepared and host-tested ONLY. No v0.19 E7 check has been run.**

## Interpretation from the actual owner-operated v0.18 result

During v0.18 on Sanctuary, the owner provided a sanitized result with:

- Original v0.14.5 configuration XML returned once as HTTP 200 (`configuration_200_socket_write_completed=true`; fixture equality reported true).
- The E7 sent a recognized subsequent root `preminet` browse (`recognized_root_browse_seen=true`); that browse received a **zero-body HTTP 404** (`recognized_root_404_socket_write_completed=true`).
- No follow-on requests, retries, handler failures or extra writes in the bounded observation. Server ended normally with `post_browse_observation_complete`.
- Owner's direct UI report was **"same thing. ;p"**, following v0.16/v0.17 where the spinner stopped and the normal unable-to-check error appeared. Record this as a **contextually inferred normal-error UI outcome**, not a verbatim handset transcript or parser acknowledgement.

Earlier **v0.14.1** already delivered two host-side 200 responses (configuration and **root**) followed by a **404 for the child request** that the host gate rejected; the E7 remained spinning. It had an older root fixture and additional confounds. See [`V14-1-REVIEW.md`](V14-1-REVIEW.md). The clean contrast with v0.18 is now **the root response itself**, not the existence of an installed test package or child ItemData.

## Proposed v0.19 one-stage substitution

A standalone owner-facing **host-only** script was built and tested but **not committed** to this docs-only PR:

`e7-root-200-child-404-control-v0.19.py`

SHA-256: `1ba6828659e12a66677549436a6fb714d01f5e49b430dc1f372c322831c0c438`

It is intended to live alongside the original v0.14.5 modules in `~/Downloads/e7-ncd-protocol-recon-v0.14.5/`. It imports `ncd_empty_browse_v09`, `ncd_guarded_browse_v142` and `ncd_installed_probe_v145` and checks the full original v0.14.5 fixture validator before binding.

| Stage | v0.18 already tried | v0.19 proposal |
| --- | --- | --- |
| Configuration POST | 200 with **original 751-byte configuration XML** | **Byte-identical 200** with same headers/source |
| Root Preminet browse | Empty HTTP 404 | **200 with original v0.14.5 566-byte two-folder root + FolderData XML** |
| Guarded child metadata browse | Not reached/expected | **Empty HTTP 404 only**, no `ItemRef`, `ItemData` or application package |
| Unknown/repeated/downloading requests | Empty HTTP 404 | Empty HTTP 404 |

Exact original fixed-body fingerprints:
- Configuration: SHA256 `604f72517551adfb6cbe8c687be5f6cba86130846361d8b480c9dfc84e5ef310` (751 bytes).
- Root: SHA256 `42e6c84e7644f017e2b108764b320c2cdf40f58dab38255b530056bf990f1050` (566 bytes).
- **No third-stage successful response whatsoever.** The owner-created installed test package's UID, SISX MIME, download URI, ZIP content and bogus `ItemData` are **not served in v0.19**.

The successful response serialization is explicitly `v09.V09Handler.reply()` with v0.14.5's original Server header. Localhost compared both initial responses to a real locally running original v0.14.5 handler: **HTTP status, body and all headers except the time-dependent `Date` match**.

Safety and strict one-shot gates are inherited from v0.18: only `10.42.0.1:80`; the known E7 peer `10.42.0.85`; exact known configuration and Preminet request shape/Host/path/namespace; at most **one configuration 200 and one root 200**; one recognized safe-companion child request may receive a **zero-body HTTP 404**, while all other operations are 404. The script never logs raw client requests, cookies, device identifiers or headers. It does not perform DNS, hotspot, firewall, device registry or private-cache operations, and has explicit bounded windows (90 s for config, 45 s root, 45 s child, 12 s post-child) with no background daemon.

## Offline verification

- `python3 -m py_compile` and `--dry-run` passed, with SHA256 preflight and **no socket binding in dry-run**.
- **14 of 14** dedicated localhost-only unit tests passed, covering: exact config/root payloads and headers; original v0.14.5 live-handler comparison; child 404 with zero body; repeat configuration/root/child and download request rejection; child-before-root rejection; malformed child filter rejection; wrong host/path exclusion; mandatory cache-risk opt-in; illegal timeouts; and automatic timeout in each phase.
- Host code was **not executed on the phone**, and no E7 packet, XML parser event, NCD completion callback or UI outcome was gathered for this proposed v0.19 test.

## Optional owner-operated single E7 check

On Sanctuary, place the separately delivered script in `~/Downloads`, then:

```sh
cd ~/Downloads/e7-ncd-protocol-recon-v0.14.5
cp ~/Downloads/e7-root-200-child-404-control-v0.19.py .
sha256sum e7-root-200-child-404-control-v0.19.py
python3 e7-root-200-child-404-control-v0.19.py --dry-run
sudo ss -ltnp '( sport = :80 )'       # no listener allowed
dig @10.42.0.1 arrowcdb.ncd.nokia.com +short # expect 10.42.0.1
sudo python3 -u e7-root-200-child-404-control-v0.19.py --arm-once --acknowledge-cache-risk
```

**Only one normal Software Update check**, after `ARMED`; no downloads or installations. Even a standard check with 200 XML could change the E7's **unbacked protected NCD/IAUpdate cache**. **No verified rollback exists.** The experiment is optional, lower-risk than inventing new application metadata, but **not risk-free**.

## Interpreting a physical result, not precommitting to one

- **Root 200 sent, guarded child 404 observed, and spinner *persists*:** the **root 200 XML/success path or the child operation it creates** differs from v0.18's root-error completion path. v0.14.1 already suggested this, but v0.19 would make the comparison cleaner. It does not establish a specific missing HTTP event, parser acceptance, or malfunctioning cache.
- **Root 200 sent, child 404 observed, and spinner *stops* with error:** root response and child creation can potentially drain through an error path here; the earlier persistent spinner may require successful child-200 metadata parsing, alternate content source/topology or an unrelated pending operation. It does not prove any item was accepted.
- **Root 200 sent but no child matched:** the root did not provoke the expected guarded child request within the observation. Classifier, root acceptance and cache state remain open; do not infer a callback or keep randomly mutating XML.
- **Configuration didn't match / write fails / unexpected requests:** no valid interpretation; do not broaden the request allowlist or change network settings reflexively.

**Scope:** documentation only on draft [PR #17](https://github.com/sillymotives/Nokia-E7/pull/17), never automatically armed; `main` unchanged.
