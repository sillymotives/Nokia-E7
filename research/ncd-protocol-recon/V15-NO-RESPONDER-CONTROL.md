# E7 NCD v0.15: no-responder transport-failure control (proposed)

**12 October 2026 | Planned, NOT executed on the E7 at the time of writing.**

## Research question

Is the indefinitely spinning Nokia Software Update UI specific to the synthetic HTTP 200 catalogue/metadata path, or does it also occur if a connection fails **before** any HTTP status or body reaches the NCD stack?

After v0.14.5, the owner's E7 remained spinning even though the server accepted a guarded configuration, root and child request and completed socket writes for all three. This does not establish handset-side receipt, parser completion, or `OperationComplete`. The source- and actual-firmware-backed [loader audit](V14-5-BELLE-LOADER-UI-COMPLETION-AUDIT.md) shows that `CIAUpdateLoader` only forwards `LoadComplete` when its outstanding NCD operations array is empty, and the UI only transitions via `RefreshComplete` when that operation finishes.

The next experiment should **not serve new XML**. The user has explicitly requested a new attempt on 12 October, but private E7 updater state still lacks a verified rollback. A no-responder baseline is less invasive than changing the catalogue or spoofing an installed application.

## Controls and prerequisites

1. The host's isolated NetworkManager AP `E7-Sanctuary-Lab` remains up on `wlxf0a7314bcc29`, with `10.42.0.1/24` and the E7 previously observed at `10.42.0.85`.
2. The already verified private DNS override resolves `arrowcdb.ncd.nokia.com` to `10.42.0.1`. Confirm again just before checking; if E7 DHCP address changed, adjust the passive observer's target IP.
3. **TCP port 80 must have NO listener.** Never start the prior `ncd_installed_probe_v145.py` or another v0.8-v0.14 responder. The only intended HTTP outcome is the host kernel's normal **TCP RST to a SYN** addressed to a closed local port. No synthetic status, HTTP body, metadata or download URI is served.
4. One manually initiated E7 Software Update check, with SIM/cellular data off and no installed-package selection. Observe whether the spinner ends and whether a clear connection/refresh error appears. Stop without further refreshes.
5. The Sanctuary observer captures **only TCP SYN, FIN and RST flags** for port 80 between the E7 and the hotspot gateway. No `-w` PCAP output, no `-A` or `-X`, no XML, headers, cookies, device IDs or user data captured or saved. Capture automatically times out at 130 seconds.

The user-facing host-only script for this planned probe is named `e7-updater-refusal-control-v0.15.sh` (created and tested outside the GitHub repo). Its `bash -n` syntax, mocked success preflight, mocked closed-port handling, and mocked positive refusal case passed locally. It is **not deployed**, automatically run, or committed to this docs-only PR. The script has no network-modification operations.

For manual inspection of the exact same essential passive behavior:

```sh
sudo ss -ltnp '( sport = :80 )'    # MUST show no listener
dig @10.42.0.1 arrowcdb.ncd.nokia.com +short   # expect 10.42.0.1
sudo timeout --signal=INT 130s tcpdump -i wlxf0a7314bcc29 -nn -l -q -tttt -s 96 \
 'host 10.42.0.85 and host 10.42.0.1 and tcp port 80 and (tcp[13] & 0x07 != 0)'
```

Run the manual updater check **only while the observer is running**.

## Outcomes and honest limits

| Captured TCP evidence and observed UI | What it tells us | What it does not tell us |
| --- | --- | --- |
| E7 `SYN` to gateway port 80, host `RST`, and a bounded connection error/UI stops refreshing | The immediate transport failure can propagate to visible UI completion under these conditions; prior 200 content/transport path deserves more focused passive study. | Does not prove an XML parsing bug or a missing `ESucceeded` in the previous trial. |
| E7 `SYN`, host `RST`, spinner continues past ~120 s | Network refusal alone did not produce visible completion; general NCD/IAUpdate completion/error state merits focus. | Does not distinguish HTTP-stack timeout, NCD parser, IPC or UI callback without a live internal trace. |
| No TCP port-80 SYN from E7 during an attempted refresh | This run did not reach the expected private listener; investigate whether updater used cache, another domain/port or skipped network. | Cannot attribute spinner to the former synthetic body. |
| Non-refusal TCP response or unexpected requests | A server, redirection or configuration state does not match the control; stop and correct only the host-side environment. | Do not infer phone acceptance. |

Neither peer ACKs nor Symbian internal HTTP events can be inferred from a SYN/RST-only capture. A normal update check might independently mutate protected E7 cache, so this is **lower risk, not risk-free**.

**No result is recorded yet.** Do not report success, an error popup, retry pattern or handset behavior until the owner supplies an actual observation. If no decisive result emerges, preserve the E7 and pursue read-only instrumentation rather than synthesizing more update records.

**Branch policy:** documentation-only draft [PR #17](https://github.com/sillymotives/Nokia-E7/pull/17), unmerged; `main` untouched.
