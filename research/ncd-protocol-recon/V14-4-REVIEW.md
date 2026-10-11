# Nokia E7 v0.14.4: SISX catalogue identity only

**Status:** Implemented and verified in an isolated host test environment; **no v0.14.4 E7 trial yet**. Draft PR is still **documentation-only**. The complete runnable ZIP is delivered separately to the owner in chat, **not committed here**. No merge, no production deployment, and no changes to `main`.

## Physical result motivating the change

In the single v0.14.3 run, the host successfully wrote its v0.9 config response, its v0.14.3 two-folder root response including one inert `FolderData` for `offline-root`, and the guarded fictional item response. The native E7 still spun indefinitely; on normally leaving it the owner again observed a **blank update directory**. During the stalled spinner an earlier 30-second passive Wi-Fi capture reported zero TCP/UDP packets, without a same-session known-good browser control. None of this is a Nokia parser acknowledgement or proof of cache damage.

## Specific source-backed SISX identity hypothesis

The historical Nokia NCD implementation [`CNcdNodeContentInfo::InternalizeL`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/provider/server/src/ncdnodecontentinfoimpl.cpp) converts the content `id` to an application UID **only** if application-purpose downloadable content has MIME `KMimeTypeMatchSisx`, defined in [`catalogsconstants.h`](https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/760927eba63e3324cceee974b9ed582da90cb9a3/ncdengine/inc/catalogsconstants.h) as `x-epoc/x-sisx-app`. The inherited inert child had `mime=application/octet-stream` and the nonhex `id=e7-lab-not-a-package`, so the historical path leaves its app UID null.

v0.14.4 changes **only those two values** in the child `dataEntity/downloadableContent`:
- `mime`: `application/octet-stream` -> `x-epoc/x-sisx-app`
- `id`: `e7-lab-not-a-package` -> `E7A01444`, an invented eight-digit UID in the development-only `0xE0000000..0xEFFFFFFF` range ([Symbian developer reference](https://cortex.p.gen.nz/nokia/symbian/Nokia%20Symbian3%20Developer%27s%20Library%20v0.8/GUID-380A8C4F-3EB6-5E1C-BCFB-ED5B866136D9.html)). Uniqueness on a handset is not verified.

All other fields, metadata records, static names/description, folder information, `size=0`, response counts/timers, expected IP/host/path and child companion allowlist remain unchanged. The configuration and root XML responses are **byte-identical to v0.14.3**.

**This is not an actual dummy SIS/SISX package.** No `.sis`/`.sisx` binaries, installable file, purchase workflow, URI, download route, signing certificate, firmware image or executable package are present. Even if the item becomes visible, **do not select, download or install it**. The E7 private writable update cache still lacks a verified rollback; therefore a metadata-only live check is optional and owner-operated, not automatic.

## Independent verification (2026-10-11)

- Twelve new TDD tests; against the v0.14.3 fallback there were five expected failures and one absent result-field error; all twelve pass with v0.14.4.
- Localhost exercised exact config 200, root 200, new SISX child 200, repeat and attempted download 404; compared all response statuses/bodies/headers with v0.14.3 and proved only stage-three body/Content-Length differ.
- **318 tests passed across all 17 modules on a clean ZIP extraction**, each module isolated to avoid combined-process fixture interference; every command exited with code 0 and `OK`. Combined discovery previously wrote `Ran 318 tests ... OK`, but other attempts intermittently failed or hung during shutdown, so the independently isolated module passes are the reliable completion evidence.
- ZIP `e7-ncd-protocol-recon-v0.14.4.zip`: **60 members**, **59 SHA256 manifest entries** verified, archive integrity checked, **no binary SIS/SISX members**.
- **All 54 inherited files other than README and checksum manifest byte-for-byte unchanged** from the real v0.14.3 ZIP. Added only the v0.14.4 responder, one test file, release notes and live-read instructions.
- ZIP SHA256: `54e38730adbcac4d9b23d54333d432b03d17d04f2ef78f1a2e452b71cdc1881e`.
- No actual E7 v0.14.4 trial has been performed.

## Experiment boundary

The separately delivered ZIP includes `LIVE-V144.md`; verify the SHA256 manifest and run the dry-run/test suite before optional live use. SIM out, mobile data off, isolated Sanctuary hotspot, 1 check only, **explicit cache-risk acknowledgement**. If the spinner remains, stop mutating metadata and investigate the updater completion path rather than adding a package URI or executable bytes.

No claim of native Belle parser acceptance, successful updater completion, safe cache mutation or genuinely installable SIS is made here.
