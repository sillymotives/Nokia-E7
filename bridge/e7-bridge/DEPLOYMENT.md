# E7 Bridge v0.7: owner-triggered SIS deployment pilot

Status: **physically accepted and merged on 2026-10-10.** Belle installed the disposable data-only package and exposed the expected 69-byte marker; music, Wi-Fi, standby and pairing survived. v0.8 registry inspection remains a separate source candidate.

## Design and trust boundary

The operator opens E7 Bridge manually on the Nokia, and Sanctuary connects via
the existing mutually authenticated protocol. Entering `deploy LOCAL.sis` on
Sanctuary stages the package with the v0.6 upload mechanism, then sends a new
nonce/sequence/HMAC-bound admin request `LAUNCH name size sha256`.

On the phone, LAUNCH refuses partial uploads, traversal, symlinks, names not
ending `.sis` / `.sisx`, missing/redirected `E:/Installs`, files exceeding 8 MiB,
zero-size packages, and mismatched length or SHA-256. It then calls Qt 4.7's
`QDesktopServices::openUrl(QUrl::fromLocalFile(path))`, delegating to Belle's
native file association / package installer. **Success means only that the
platform accepted an open request**. Actual installation, signature checks,
user prompts and package version acceptance are controlled by the OS.

This pilot refuses `E7Bridge*` self-upgrades from the host command. It does not
seek capabilities beyond `NetworkServices ReadUserData WriteUserData` and does
not attempt AllFiles/TCB, firmware rewriting, silent install or a remote shell.
The TCP connection still lacks confidentiality. Prefer disposable local probes.

## Physical acceptance procedure

1. On Sanctuary preserve your known-good **v0.6.0** SIS and the existing key.
   Build v0.7 with the same signer and UID3. Install it on the Nokia C: memory.
   Ensure `ping`, `info`, and `metrics` still work and pairing is remembered.
2. Create the data-only disposable `E7DeployProbe` SIS using the pinned
   toolchain helper in `build/build-install-probe.sh`. This installs only a tiny
   public marker under `C:/Data/E7DeployProbe/`, not any executable.
3. In the authenticated v0.7 controller, run `deploy ./E7DeployProbe-v0.1.0.sis`
   using the path to the generated fixture. Check the printed upload SHA-256
   and the status **installer launch requested**, which is *not* install proof.
4. On the E7, observe whether Belle opens the installer, whether it prompts,
   whether signing is accepted, and whether it finishes. Do not dismiss
   unexpected warnings without inspecting them.
5. If the OS reports success, reconnect if needed and run
   `ls C:/Data/E7DeployProbe` and
   `stat C:/Data/E7DeployProbe/probe.txt` in the bridge. Inspect the marker
   file locally using the Nokia File Manager. The marker should say
   `E7 installer pilot: installed by the native Symbian package manager.`
6. Check music, Wi-Fi, standby and reconnect behaviour. Stop and report any
   `ERR INSTALLER_*` response or a disappearing bridge connection.
7. Do **not** deploy v0.7 onto itself via the remote command. Only test the
   disposable data-only fixture. Roll back by manually reinstalling v0.6
   on phone memory if necessary, retaining the original signing identity.

## Result semantics

- `STORED`: transport accepted an exact-size/hash file into E:/Installs.
- `LAUNCH_REQUESTED`: Qt's associated-document launcher accepted an open request.
- `ERR INSTALLER_OPEN_FAILED`: Qt refused the open request.
- `ERR PACKAGE_*`: source on device failed validation; no installer launch.
- Actual installation: confirm via Belle UI and the newly installed fixture.

No automatic installation status is claimed. Reliable registry/status queries
and controlled bridge self-upgrade are separate future milestones.

## Historical implementation references

- Qt 4.7 document opening API: https://qt.developpez.com/doc/4.7/qdesktopservices/
- Qt 4.7 local-file URL API: https://qt.developpez.com/doc/4.7-snapshot/qurl/
- Symbian SIS handoff historical discussion: https://stackoverflow.com/questions/4826664/can-i-install-sis-files-from-within-an-nokiaqt-symbian-application

## v0.8 follow-up

The v0.7 operator-confirmed installation is documented here. Version 0.8 adds read-only native Software Install registry lookup (`packages`, `pkg`, `verify`) and a safe read-only `batch` host command. It remains a source candidate until a signed Symbian build runs on the Nokia. These queries do not uninstall, silently install or self-upgrade packages.

## v0.7 observed installation

The physical phone successfully installed the disposable probe from Sanctuary using the native Belle installer, despite a harmless package compatibility warning. Subsequent independent bridge commands found `C:/Data/E7DeployProbe/probe.txt` at exactly 69 bytes. The operator also verified the native music player, Wi-Fi, standby and remembered connection settings. These observations are distinct from v0.8's proposed registry-based verification.
