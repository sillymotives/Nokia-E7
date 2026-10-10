# E7 Bridge v0.6: begin owner-controlled remote administration

Status: **v0.6 physical acceptance passed and merged** on 2026-10-10. v0.7 installer-launch extension also passed on-device acceptance. v0.8 registry queries have passed physical acceptance.

## Product goal

Restore the Nokia E7 to modern practical use, while letting Sanctuary act as its
administration console. Intended scope ultimately includes application upgrades,
file management, native services and carefully reviewed firmware patches. The
old vendor support policy is not a requirement; the handset owner's recovery
ability is.

## Privilege map

1. **Now / Basic Symbian signing:** NetworkServices, ReadUserData,
   **WriteUserData**. This candidate performs signed session-bound uploads to
   E:/KAI/INBOX and E:/Installs. These are ordinary data areas, not protected
   binaries. There is no extra on-phone approval per upload after Connect.
2. **Next:** remotely inspect the staged data, support explicit versioned
   replacements/backups within writable data roots, launch approved native
   applications and investigate the Symbian installer APIs. Installation may
   still show system prompts; copying a SIS to E: does not install it.
3. **Privileged owner-controlled research:** evaluate the existing working
   ROMPatcher configuration and a narrowly scoped elevated agent, rather than
   pretending adding AllFiles/TCB to a self-signed .pro grants privileges.
   Verify signing, UID/capability changes, the exact recovered stock variant,
   ROM backups and a functioning dead-USB recovery route *before* touching
   C:/sys, private user stores or Z:/ firmware resources.

## v0.6 command protocol

The existing E7-initiated outbound socket and mutual HMAC handshake are retained.
Successful Connect authenticates the session. Administrative commands add
`ADM <sequence> <payload> <hmac>` and signed replies
`ADMREPLY <sequence> <result> <hmac>`; the HMAC covers a fresh handshake nonce,
the strictly incrementing counter, and the ASCII command/reply. Replays or
modified payloads are rejected. There is **no network encryption**.

Supported payloads are `BEGIN <inbox|installs> <simplefilename> <bytes> <sha256>`,
`CHUNK <offset> <base64>`, `FINISH`, and `CANCEL`. Data are capped at 8 MiB,
chunks at 2048 bytes, and the recipient filename at 64 plain ASCII characters
with no path separators or traversal. Existing filenames never overwrite.

The phone writes a same-directory staging file and verifies the declared
SHA-256 of all received bytes before final rename; partially received files
are removed on network disconnect/cancel. This is not a crash-safe filesystem
transaction guarantee, especially on FAT; abrupt power loss can leave a stale
`.part` file for manual examination/removal. Package staging is not silent
installation; a future upgrade orchestrator must be designed separately.

## Acceptance gate before PR merge

- Source tests (`python3 -m unittest discover -s tests -v`) and bash syntax pass.
- Build under the pinned Symbian SDK; verify executable UID and SIS signing.
- Install signed SIS on **C: phone memory**; note installer capability prompt.
- On Sanctuary in the v0.6 host controller, use `push fixture.txt` (non-private)
  to send a small test file. Verify the file exists in `E:/KAI/INBOX` on phone
  through File Manager; compare bytes with original, not just status text.
- Re-send the same name and verify `ERR EXISTS`, preserving the original.
- Push a small disposable `.sis` sample to E:/Installs; **do not install it**
  during this first upload test.
- Disconnect mid-upload if practical and verify no published partial file.
- Verify old `ping`, `metrics`, `pull probe`, `capture`, pairing persistence,
  music, Wi-Fi and standby continue working.

v0.6 was merged only after the operator confirmed actual staging and no-overwrite behaviour. Protected system changes remain gated on independent recovery evidence.

## v0.7 continuation

v0.6 physical staging and duplicate-write checks were operator-confirmed on
2026-10-10. v0.7 extends the **existing** authenticated admin session with a
single installer-launch request restricted to a verified staged SIS package;
see [DEPLOYMENT.md](DEPLOYMENT.md). Neither a launch-request acknowledgement
nor staged SIS presence proves a successful Symbian software installation.

## v0.6 final physical acceptance (2026-10-10)

The operator built/installed v0.6 and reported authenticated upload, the
`ls`/`stat` readback, and rejection of a second upload with the same filename.
They also reported post-test phone behaviour working. This is operator-observed
hardware evidence alongside 65 host-side tests, not proof of future privileged
system operations or silent installs. PR #5 was merged into main.

## Sanctuary host v0.8.1 write-batch extension

The host now supports explicitly requested, bounded, audited `batch --write`
jobs composed of existing authenticated `push`, `deploy` and read-only checks.
This **does not** change Nokia-side capabilities. See `ADMIN-BATCHES.md` for
preflight, journal, safe resume and scope details.
