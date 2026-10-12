# E7 NCD v0.17: one-shot HTTP 200, **empty body** control (owner-run)

**12 October 2026. One owner-operated E7 test completed, after prior host-only verification.**

## Evidence that motivates this control

The owner ran two bounded no-catalogue controls on the isolated Sanctuary AP, with E7 address `10.42.0.85` and Sanctuary DNS/HTTP gateway `10.42.0.1`:

| Previous test | Host-side observation | Physical E7 observation |
| --- | --- | --- |
| v0.15 (no TCP listener) | Two SYN/FIN/RST-filtered packets, 142 us apart. Quiet output `tcp 0` did not expose actual flag letters. | Spinner stopped and displayed the standard unable-to-check error. |
| v0.16 (one HTTP 404, `Content-Length: 0`) | Exactly one valid configuration POST matched, host flushed response, zero other requests and zero response bytes. | Spinner stopped and displayed the same error. |
| v0.14.5 (three HTTP 200, XML bodies) | Host wrote configuration, root and child XML HTTP 200 replies; no socket-write errors. | Spinner remained; no handset parse ACK or UI callback trace. |

Both **TCP refusal** and a **real HTTP 404 response** therefore permit visible failure completion. The 200/XML path differs, but an HTTP status change, nonempty XML parser input and subsequent root/child operations were confounded.

Pinned Nokia source [`CCatalogsHttpTransaction::ResponseReceived`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/engine/transport/src/catalogshttptransaction.cpp#L621-L653) explicitly marks `>=400` responses `ECatalogsHttpOpFailed` and invokes `HandleHttpError`. A `200` response instead enters `ECatalogsHttpOpInProgress` and observer notification, with parser input/completion afterward. The actual E7's internal events were **not observed**. This source-level split supports a direct controlled test.

## One-change response

The separately delivered host-only script **`e7-http-200-empty-control-v0.17.py`** derives from v0.16. **SHA256 `b64db899cabf694c8704638de7ece2eb578d5908725fb7118116cbfb19eadcf8`.** It is intentionally **not committed to GitHub** because PR #17 is documentation-only.

Its one server response differs from v0.16 in **HTTP status line only**:

```http
HTTP/1.1 200 OK
Content-Length: 0
Connection: close
Content-Type: text/plain
Cache-Control: no-store

```

The `Content-Type: text/plain` is **deliberately retained** from the 404 control to avoid changing two variables. Unlike a full valid NCD configuration, this is an intentionally **empty and application-level invalid success reply**. The goal is to distinguish HTTP 200 success handling with *no XML bytes* from the earlier fully populated configuration/root/child responses. It is **not a fix** for Nokia's update service.

Same known request-shape validator from `ncd_empty_browse_v09.py`: only a POST `/` with correct `arrowcdb.ncd.nokia.com` Host, Content-Length, bounded Preminet `configurationRequest` root, and exact E7 client IP `10.42.0.85` may receive a response. All others are dropped with no HTTP reply; maximum one HTTP 200; server binds only `10.42.0.1:80` and stops after one match or a default 90-second window. No logging of request bodies, cookies, headers, raw paths or phone identifiers. No app, installer, URI, download, firmware image, cache-clearing action, firewall change or automatic on-device command.

## Host test results (not E7 results)

- `python3 -m py_compile` passed; `--dry-run` opens no listener.
- **4/4** dedicated tests passed: dry-run configuration, mandatory cache-risk acknowledgement, exact guarded configuration matching including unrelated Host drop, and a live localhost HTTP 200 exchange with exactly zero body bytes.
- Comparison against original unmodified v0.16 host script: **headers byte-for-byte semantically identical**, `Content-Length: 0`, `Connection: close`, `Content-Type: text/plain`, `Cache-Control: no-store`, no automatic Server/Date; only status is 404 versus 200.
- Local tests use loopback `127.0.0.1` only; they do not address the Nokia or alter Sanctuary's hotspot.

## Optional user-operated test, if explicitly chosen

Copy the script into the existing `~/Downloads/e7-ncd-protocol-recon-v0.14.5/` folder alongside `ncd_empty_browse_v09.py` and confirm E7 still uses `10.42.0.85`:

```sh
cd ~/Downloads/e7-ncd-protocol-recon-v0.14.5
cp ~/Downloads/e7-http-200-empty-control-v0.17.py .
python3 e7-http-200-empty-control-v0.17.py --dry-run
sudo ss -ltnp '( sport = :80 )'
dig @10.42.0.1 arrowcdb.ncd.nokia.com +short
sudo python3 -u e7-http-200-empty-control-v0.17.py --arm-once --acknowledge-cache-risk
```

Initiate **at most one** ordinary update check after `ARMED`, observe the exact UI behavior and share the **sanitized RESULT**. Because a 200 response may trigger parser/cache actions, **private NCD/IAUpdate state can still change and has no verified rollback**. There is no installable payload.

## Owner's live result (12 October 2026)

The owner ran the optional `--arm-once --acknowledge-cache-risk` command in Sanctuary and reported "**Same result**" directly after the earlier v0.16 run, where the spinner stopped and the ordinary "unable to check for updates" message appeared. This is recorded as **the spinner stopped and the normal failure UI appeared**, based on that conversational comparison, not as a newly captured photograph or exact on-phone quotation.

Sanitized host result independently confirms:
- `configuration_request_shape_matched=true`.
- `one_empty_http_200_attempted=true`, `response_body_bytes=0`, and `response_socket_write_completed=true`.
- `other_requests_discarded_without_http_response=0`; server shutdown reason `one_configuration_200_attempted`.
- `no_client_parse_ack_or_ui_completion_trace=true`. The result is **not evidence of client XML acceptance**. No XML, catalogue, installer, download URL or payload was sent.

**New discrimination:** both an empty-body HTTP 404 and an empty-body HTTP 200 trigger ordinary visible error completion on the E7. A `200` **status alone is insufficient to reproduce** the earlier nonterminating spinner. The distinguishing variables in v0.14.x are **nonempty configuration XML** and whatever additional network requests or asynchronous operations it starts; root/child catalogue data need not yet be involved. A successful socket write still does not prove phone-side parser completion.

For future work, prefer **one valid/previously used configuration HTTP 200, with all later requests refused or given explicit 404**. Comparing this bounded *configuration-only* test with v0.17 and the three-stage v0.14.5 flow could distinguish configuration parsing/discovery from subsequent browse loading without inventing any new metadata. This is a **proposed** experiment only and requires separate consent and cache-risk acknowledgement; normal updates can mutate private state, with no verified rollback.

## Interpretation after a physical run, not before

- **Spinner ends in error:** a zero-body HTTP 200 can propagate to normal error completion. The earlier spinner is then more associated with *nonempty XML*, NCD source discovery or child load/IPC processing. It does **not** prove 200-success completion works for valid XML.
- **Spinner persists:** entering the 200 success path even with zero XML bytes can leave pending parser/NCD work, making **configuration-stage success/empty-parser completion** a stronger focus. Does **not** prove HTTP terminal `ESucceeded` was absent.
- **No match / no 200 write:** inconclusive on phone-side behavior. Verify isolated IP/DNS/host port, without relaxing the request gate.
- **200 socket write completed:** this is **not handset parser or callback acknowledgement**.

**Owner-run E7 outcome is recorded above.** PR #17 remains draft, unmerged, documentation-only. `main` and private E7 software state are not changed by preparing this host script.
