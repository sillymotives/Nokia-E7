# Sanctuary administrative batches (host v0.8.1)

**Status:** first physical E7 write-capable batch accepted on 2026-10-10; broader interruption and resume hardware tests still pending.

This version works with the *existing* E7 Bridge **v0.8.0 phone agent**. No new
Symbian SIS build or reinstall is required. Keep the same pairing key and trusted
Wi-Fi. The phone still has only `NetworkServices ReadUserData WriteUserData`.

## Commands at `e7>`

- `batch FILE`: existing read-only batch, unchanged.
- `batch --plan FILE`: validate all steps, local source filenames, size limits,
  hashes, and duplicate remote targets **without changing the device**.
- `batch --write FILE`: execute preflighted reads and writes in order, without
  per-step permission prompts. Each step is synchronously acknowledged and
  checkpointed in an owner-only local JSONL receipt.
- `batch --resume JOURNAL FILE`: resume a *same-content* manifest and same-content
  local files after a safe interruption. Previously completed uploads are skipped
  only after confirming remote path and byte count. If the previous upload may
  have committed but no authenticated receipt was logged, **resume refuses**;
  inspect the Nokia manually instead of risking duplicate writes.

`FILE` is local to Sanctuary. Paths inside it resolve **relative to the batch
file's directory**, not the terminal working directory. Quote paths containing
spaces using shell quoting. The journal is printed at the start/end and kept at
`~/.local/share/e7-bridge/batches/`, mode `0600` (directory `0700`).

## Supported write-job steps

```text
# The E7 v0.8.0 phone remains installed, no new SIS needed.
ping
info
verify 0xE94B7002 0.1.0
push ./batch-hello-v081.txt inbox
stat E:/KAI/INBOX/batch-hello-v081.txt
```

See [`examples/admin-write-demo.batch`](examples/admin-write-demo.batch).
Upload targets are `E:/KAI/INBOX/` for `push FILE [inbox]` or `E:/Installs/`
for `push FILE installs`. Each uploaded file is at most 8 MiB, with 32 MiB total
per job, no destination overwrite or path traversal, and at most 40 steps.
Every upload uses the existing session-bound HMAC and checks exact SHA-256.
`verify UID VERSION` must match, or the entire **remaining** job is stopped.
Read-only checks include `ping`, `info`, `drives`, `metrics`, `packages [OFFSET|all]`,
`pkg UID`, `verify UID VERSION`, `ls`, `stat`.

`deploy FILE.sis` can be the **final** job step. It stages a non-overwriting
package and requests Belle's native installer. It **does not prove installation**
or bypass installer prompts. Inspect Belle and run a separate package-registry
batch afterward to confirm success. The controller refuses attempting a bridge
self-upgrade during the active bridge session.

## Why the stop points exist

A batch **is not one atomic transaction**. An individual file upload is staged
atomically on E:, but Belle may disconnect after applying a step. The journal
makes successes and uncertain steps visible. A completed upload may be skipped
on resume after checking its path/size; this is **not** a fresh cryptographic
hash of the remote file. A pending/failed write cannot be automatically resumed.
Installer launches are never blindly replayed.

These operations do not grant filesystem rights the Nokia agent lacks. Normal
`WriteUserData` allows the controlled directories above, **not** protected
`C:/sys`, `C:/private` or ROM/firmware changes. Once we build a separately
verified recovery mechanism and privileged agent, the batch planner can gain
additional explicit operation types with their own preflight and journals.

The transport is still unencrypted TCP with a 16-hex development pairing key.
Keep non-secret fixtures on your trusted LAN; do not transfer private backups,
credentials or keys. For higher-privilege future work, upgrade authentication
and transport first.

## Practical launch on Sanctuary

From an extracted v0.8.1 source directory:

```bash
python3 -m unittest discover -s tests -q
bash ./build/serve-on-sanctuary.sh
```

Connect the existing v0.8.0 phone app. At `e7>`:

```text
batch --plan ./examples/admin-write-demo.batch
batch --write ./examples/admin-write-demo.batch
```

The demo creates `E:/KAI/INBOX/batch-hello-v081.txt`; running it a second time
is **supposed to refuse overwriting that filename**. That is not an error in
the batch mechanism.

## First physical write-batch acceptance (2026-10-10)

The operator used Sanctuary host v0.8.1 with the unchanged, physically installed E7 agent v0.8.0. The five-step demo was first planned and then executed on the real Nokia, with matching plan SHA-256 `fc55a16a99f29093fd6c4efd1cf2d5f31617ed86cad8798f0671a2398461bb25`.

- `ping` returned `PONG`; `info` identified Nokia Belle / Qt 4.7.4 / E7 Bridge v0.8.0.
- `verify 0xE94B7002 0.1.0` returned `VERIFIED`.
- `push ./batch-hello-v081.txt inbox` staged `E:/KAI/INBOX/batch-hello-v081.txt`, exactly **63 bytes** with SHA-256 `20f8e727e1f34e00d9129de563e5b58e9ee636cd2a80346c978209b49f10a6b3`.
- Subsequent `stat E:/KAI/INBOX/batch-hello-v081.txt` returned `file | bytes=63 | path=E:/KAI/INBOX/batch-hello-v081.txt`.
- A private journal was emitted: `e7-batch-20261010T182503Z-dbd81ba5.jsonl`. The controller printed `Batch finished`.

This confirms the positive path for host-side preflight, mixed read/write execution, one atomic staged upload, immediate size readback and durable receipt generation on the physical phone. It does **not** by itself prove an interrupted physical upload can safely resume, nor end-to-end rollback of multi-step changes. Repeating the same demo is supposed to refuse overwrite. A safely completed-job resume test should skip the existing upload after checking its size and logged receipt; uncertain in-progress writes remain blocked for manual inspection.

## Completed-batch resume accepted on physical E7 (2026-10-10)

Using the same Sanctuary v0.8.1 host and the existing JSONL journal, the operator ran:

```text
batch --resume /home/darkstar/.local/share/e7-bridge/batches/e7-batch-20261010T182503Z-dbd81ba5.jsonl ./examples/admin-write-demo.batch
```

All five steps completed again. The authenticated `ping`, `info`, and installed-package version check passed; at step 4, the controller explicitly printed:

```text
Already staged; previous authenticated receipt and current size verified.
```

The upload was **skipped**, not blindly replayed. The final `stat` confirmed `E:/KAI/INBOX/batch-hello-v081.txt` remains 63 bytes, and the same journal was reported with `Batch finished`.

**Accepted scope:** real handset positive-path batch execution and **completed-upload resume** with journal and remote size checks. This is **not** a fresh remote SHA-256 check, proof of interruption recovery, multi-step atomic rollback, or privileged filesystem access. These are separate future requirements. The 122-case host test suite passed during development.
