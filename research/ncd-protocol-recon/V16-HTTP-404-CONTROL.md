# E7 NCD v0.16: one-shot HTTP 404 response-control plan

**12 October 2026 | Prepared and locally tested ONLY; the E7 has NOT run this test.**

## Reason for the control

On the same isolated Sanctuary access point, E7 native Software Update behaves differently for two prior scenarios:

- **v0.14.5:** the host completed socket writes for three guarded HTTP 200 responses (configuration, root and child catalogue metadata); the E7 **continued spinning**. Host socket writes do *not* prove phone-side HTTP/parse/operation ACKs.
- **v0.15:** with **no HTTP server on port 80**, the updater **stopped spinning** and displayed **"unable to check for updates please try again later"**. A passive capture recorded only two packets: E7 `10.42.0.85:36752` to Sanctuary `10.42.0.1:80` and back, 142 microseconds apart, no dropped packets. The `tcpdump -q` printing `tcp 0` suppresses explicit flags, so the exchange is *consistent with* SYN/RST refusal but **does not prove flags from the printed output alone**.

A useful **v0.16** discriminator is to **accept the TCP connection and issue an ordinary well-framed HTTP 404 with `Content-Length: 0`**, once and only to the exact E7 configuration POST already recognized by v0.9/v0.14.5. This distinguishes immediate connection refusal from a completed HTTP error response, without introducing more fictional software, purchase/download URIs or XML parsing content.

## Host-only script

Owner-facing file produced separately, **not committed to GitHub**: `e7-http-404-control-v0.16.py`

SHA256: `27f685c6851d3745de6bc04a262b220a8c574814d67472307c6a4047a9046bad`.

The script is intended to be copied into the owner's **existing** `~/Downloads/e7-ncd-protocol-recon-v0.14.5/` directory alongside `ncd_empty_browse_v09.py`. It **imports and reuses** that vetted configuration-envelope recognizer; it is not a new protocol response generator.

Host restrictions:
- Binds **only** `10.42.0.1:80`, not all interfaces.
- Permits the known E7 IP `10.42.0.85` (check DHCP first).
- Only accepts a bounded POST to `/` with `Host: arrowcdb.ncd.nokia.com`, exactly one Content-Length, no Transfer-Encoding and valid Preminet `configurationRequest` root. Reads at most 65,536 request-body bytes to verify the shape **in memory**, without printing or persisting request body, cookies, headers, path or device identifiers.
- **One** qualifying response maximum, then disarms/closes; all other requests are immediately dropped without any HTTP response. User-visible status/result contains only aggregate booleans and counters.
- Sends `HTTP/1.1 404 Not Found`, `Content-Length: 0`, `Connection: close`, `Content-Type: text/plain`, `Cache-Control: no-store`, no body. Unlike a connection refusal, this lets the phone receive a real HTTP status.
- Requires `--arm-once --acknowledge-cache-risk`, runs for at most 90 s by default, and has `--dry-run` which opens no sockets. No firewall, DNS, NetworkManager, responder configuration, registry, SIS/SISX, package, firmware or phone-side mutations are implemented.

Host-only verification: Python compile succeeded; **4/4 local tests passed**, including `--dry-run`, missing-ack refusal, exact configuration request-shape classification, and a real loopback POST with a clean 404 zero-length body and no request-body logging. No live E7 or Sanctuary network probe occurred in these tests.

## Owner-operated run, if chosen

```sh
cd ~/Downloads/e7-ncd-protocol-recon-v0.14.5
cp ~/Downloads/e7-http-404-control-v0.16.py .
python3 e7-http-404-control-v0.16.py --dry-run
sudo ss -ltnp '( sport = :80 )'   # must be empty
dig @10.42.0.1 arrowcdb.ncd.nokia.com +short  # must return 10.42.0.1
sudo python3 -u e7-http-404-control-v0.16.py --arm-once --acknowledge-cache-risk
```

Start one ordinary Software Update check while it prints `ARMED`. The listener will stop after the first qualifying response or within 90 s. Observe whether the spinner ends and the exact error message, and share **only the sanitized RESULT**. No need to select/install/download anything. An ordinary update check may still change the phone's private NCD/IAUpdate caches; **no verified rollback exists**, even though this script serves no XML or app payload.

## Interpretation, without overclaiming

- **HTTP 404 produces visible error and stops spinner:** handling an HTTP error can drain to UI, while the prior three HTTP 200 catalogue responses did not. Concentrate on 200 terminal-success and parser/NCD completion boundary. **Does not by itself establish a parser bug.**
- **HTTP 404 also spins indefinitely, but matching POST was observed:** TCP refusal completes while the real HTTP response path may remain pending. The HTTP stack's HTTP-error path, terminal event and higher-level callbacks require inspection.
- **No matching POST:** the control did not reach its intended envelope; do not infer about HTTP completion. Recheck DHCP/host routing and any local cache path; do **not** relax request allowlist automatically.
- **Socket write completed:** confirms only host `wfile.flush`, never an E7 parser ACK or end-to-end completion.

**As of this note: no phone outcome, no extra experiment performed and no app installer/payload produced.** Keep [draft PR #17](https://github.com/sillymotives/Nokia-E7/pull/17) open and unmerged. All current writes are documentation-only on its research branch; `main` remains untouched.
