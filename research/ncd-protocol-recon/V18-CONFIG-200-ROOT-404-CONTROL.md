# E7 NCD v0.18: unchanged configuration 200, then root browse 404 (completed)

**12 October 2026 | One owner-operated E7 run completed after host-only verification.**

## What v0.17 established

The owner reports that the E7's Software Update spinner again stopped and displayed its standard unable-to-check error during **v0.17**. Sanctuary's sanitized log independently confirms one correctly shaped E7 `configurationRequest` POST and exactly one flushed **HTTP 200 with `Content-Length: 0`**, no XML body, then server shutdown. This follows **v0.16** (one empty HTTP 404) and **v0.15** (no port-80 listener), both of which also ended with a normal failure UI.

The contrasting **v0.14.5** experiment had a host-completed configuration **200 XML**, root **200 XML**, and child **200 XML** response, with the owner reporting a persistently spinning updater. These are **host socket receipts and UI observations**, not evidence of E7 XML parser acceptance or final HTTP `ESucceeded`.

**Inference:** an HTTP 200 status line alone is not sufficient to reproduce the spinner. The *nonempty configuration XML and subsequent browses* are the next variables to isolate. Retain all uncertainty about actual Belle callback state.

## Exact v0.18 response/control

The separately delivered script `e7-config-then-404-control-v0.18.py` resides only in the chat's generated artifacts, **not in the repository**. SHA256:

`13cea0a225331ebe50cc47c3002cb9847b1675b02bba34bfc6d780607f0e333b`

It must sit in the owner's existing `~/Downloads/e7-ncd-protocol-recon-v0.14.5/` directory alongside the previously verified `ncd_empty_browse_v09.py` and `ncd_installed_probe_v145.py`.

The first and **only eligible HTTP 200** is the original **751-byte v0.14.5 `configurationResponse`**, exact SHA256 `604f72517551adfb6cbe8c687be5f6cba86130846361d8b480c9dfc84e5ef310`. The script reuses the **original `V09Handler.reply` method** for exact status/header/body framing with `server_version` equal to the original v0.14.5, not a new hand-built HTTP encoder. The configuration advertises the same synthetic source `urn:e7-lab:synthetic:catalogue:v09` and its local inert browse endpoint.

After that first config, **only one recognized original-source root browse** can receive an empty **HTTP 404**. Its response has **Content-Length: 0** and **no root XML**, therefore cannot advertise a node or child. Additional, unmatched, out-of-window, child-before-root and retry requests receive empty 404 responses. No body/headers/cookies/phone identifier are logged. The server binds only `10.42.0.1:80` and allows only the known E7 `10.42.0.85` for the config 200. Expected initial configuration request shape, root namespace and request-envelope checks are inherited verbatim from v0.14.5/v0.9.

Limits: configuration 90 s, recognized browse 45 s, post-browse observation 12 s. Requires `--arm-once --acknowledge-cache-risk`. Host `--dry-run` only verifies fixed configuration fixtures and opens no sockets. This carries **no real SIS/SISX, download URI, installer, application metadata, purchase or firmware payload**. It does not change Sanctuary DNS, Wi-Fi or firewall configuration.

## Host verification (2026-10-12)

- Source compiles under Python 3.
- **9/9 unittest checks passed**, including exact original v0.14.5 configuration response **status, all non-Date headers and body bytes** in a socket-level comparison, matching request and root reply 404, config repeat refused, second browse refused, alien peer refused, malformed/wrong-host/wrong-path refused, no-browse timeout, mandatory cache-risk acknowledgement and dry-run opening no listener.
- First host-only test caught a local `V10Handler.reply` accounting-hook mismatch; fixed by using `V09Handler.reply` directly, and reran all 9 tests successfully. This initial bug was discovered entirely in local Python/loopback and did not touch a phone.
- Server errors are counted without printing raw request identifiers or traceback.
- **No user-run E7 result exists yet for v0.18.**

## Optional owner-operated use

```sh
cd ~/Downloads/e7-ncd-protocol-recon-v0.14.5
cp ~/Downloads/e7-config-then-404-control-v0.18.py .
sha256sum e7-config-then-404-control-v0.18.py
python3 e7-config-then-404-control-v0.18.py --dry-run
sudo ss -ltnp '( sport = :80 )'        # MUST show no listener
dig @10.42.0.1 arrowcdb.ncd.nokia.com +short # expect 10.42.0.1
sudo python3 -u e7-config-then-404-control-v0.18.py --arm-once --acknowledge-cache-risk
```

One normal E7 Software Update check only, and note whether its spinner ends or fails. Preserve original device state. **Even an ordinary update check may change unbacked protected NCD/IAUpdate cache. There is no verified rollback.**

## Physical v0.18 result, reported 12 October 2026

The owner operated the guarded v0.18 listener on the existing isolated Sanctuary E7 AP and supplied the sanitized result:

- `configuration_200_attempted=true`; `configuration_200_socket_write_completed=true`; `configuration_xml_identical_to_v145=true`.
- `recognized_root_browse_seen=true`; `recognized_root_http_404_attempted=true`; `recognized_root_404_socket_write_completed=true`; `recognized_root_404_response_body_bytes=0`.
- No child-before-root attempts, extra requests or POSTS, configuration retries, handler failures or other socket-write errors.
- Shutdown reason `post_browse_observation_complete`; listener disarmed normally. No root or child XML, software metadata or installer/download endpoint was served.
- The owner said **"same thing. ;p"** after two immediately preceding experiments in which Spinnyboi *stopped* and displayed the standard unable-to-check error. This is treated as the same stopped-spinner/error outcome by conversational context, **not** an independently transcribed screen message for this run.

**Bounded conclusion:** The E7 received enough of the original v0.14.5 configuration success path to issue the expected root browse, yet when that root returned an explicit 404, the UI was observed to recover into its ordinary unable-to-check failure path. Thus the **configuration 200 alone is not sufficient** to reproduce the indefinite spinner. An HTTP 200 root response and/or the child loads it starts are stronger discriminators.

**Important historical overlap:** in actual previous **v0.14.1**, the host wrote configuration 200, **root 200**, and **then 404 for a distinct child browse** due to an over-strict host matcher, while the E7 *remained spinning*. This strengthens the root-success hypothesis, but differs in the root body contents and time/state of the test, so is not a strict same-fixture control. See [`V14-1-REVIEW.md`](V14-1-REVIEW.md) and [`V14-2-REVIEW.md`](V14-2-REVIEW.md).

**Safer next controlled change (proposed only):** keep the exact v0.18 configuration 200 and all request gating, substitute the byte-identical v0.14.5 root-folder XML **HTTP 200** for the former empty root 404, then **404** the guarded follow-on child browse (no child item data). This isolates the effect of the *root response* more precisely than v0.14.1 and does not invent new software metadata. It still carries private NCD/IAUpdate cache-write risk with no verified rollback. Do not infer anything about handset parser ACKs from host write completion.


## What would the outcomes mean?

- **Root browse matched and answered 404; phone spinner stops/error:** config source is usable enough to issue a subsequent browse; error propagation at *root* can finish. The unresolved difference in v0.14.5 lies **after** an allowed successful root 200 and/or the child metadata processing. Does not prove root 200 response was accepted.
- **Config 200 sent, no root browse seen; phone stops/error:** configuration response may have been rejected or parsed without launching browse. Cannot isolate later root stages.
- **Config 200 sent, root 404 answered; phone still spins:** outstanding config/root/error handling can remain pending under this sequence. Need a readonly client callback trace, not more speculative XML.
- **No config matched, unexpected requests, any host write failure:** inconclusive. Recheck network/host preflight before making claims; **do not loosen protocol gates** to force a positive result.

**Result observed and documented above; no new device change by this PR edit.**

**PR policy:** documentation-only draft [PR #17](https://github.com/sillymotives/Nokia-E7/pull/17), unmerged; `main` unchanged. No phone image, raw request, exploit, installer or runnable responder committed.
