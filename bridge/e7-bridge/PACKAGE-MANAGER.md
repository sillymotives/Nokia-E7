# E7 Bridge v0.8: native SIS package inventory and verification

**Status:** source candidate. Python model tests and shell syntax can run in the authoring container. The Nokia Qt/GCCE build and on-device registry checks require Sanctuary.

## Basis for the implementation

The original Symbian Foundation source headers for `swi/sisregistrysession.h`
and `swi/sisregistryentry.h` explicitly expose `RSisRegistrySession::InstalledUidsL`
(requires `ReadUserData`), `RSisRegistryEntry::Open`, `VersionL` and `PackageNameL`.
The `sisregistryclient.lib` dependency is supported by the historical SWI build, but whether it is available in Sanctuary's pinned SDK still requires native compilation.
See:
- https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/master/installationservices/swi/inc/swi/sisregistrysession.h
- https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/master/installationservices/swi/inc/swi/sisregistryentry.h
- https://github.com/SymbianSource/oss.FCL.sf.mw.appinstall/blob/master/installationservices/swi/group/sisregistryclient.mmp

## Commands

- `packages` (12 rows) / `packages OFFSET` / `packages all`
- `pkg UID`: one base SIS package, installed status, name and version
- `verify UID VERSION`: exact version comparison, not launch-request acceptance
- `batch LOCAL.txt`: a bounded local UTF-8 script, **read-only** commands only

Use package UIDs from SIS headers, **not executable Secure IDs**. The previous
probe package was `0xE94B7002`, expected version `0.1.0`; E7 Bridge itself uses
`0xE94B7001`, v0.8.0. InstalledUidsL omits augmentations; it is not identical
to an inventory of all app menu icons.

## Acceptance on physical E7

1. Keep signed `E7Bridge-v0.7.0.sis` for rollback and record the working pairing IP and key.
2. Build and sign v0.8.0 with exactly the existing build identity, UID3, and `sr1-qt474-v1` toolchain. If SDK compilation fails (missing SWI client headers or import library), stop; don't alter ROMPatcher to force it.
3. Install v0.8.0 **manually**, keeping remembered settings; reconnect from Sanctuary using matching v0.8 host.
4. `ping`; `info`; `packages`; `pkg 0xE94B7002`; `verify 0xE94B7002 0.1.0`.
5. Try `verify 0xE94B7002 99.0.0` and confirm **NOT VERIFIED**; query an uninstalled UID and confirm `not installed`, not an error or a fabricated version.
6. Test `batch` with a local file containing a few read-only commands, including a `pkg`/`verify` check. Deliberately include `push` in a temporary batch file and confirm the entire batch is refused before executing any commands.
7. Confirm music player, Wi-Fi, standby and remembered settings still work. Keep PR draft until all pass.

## Not yet supported

Automatic installer-completion monitoring, a rollback-capable bridge self-upgrade,
package removal, elevated AllFiles/TCB, and firmware/ROM writes. Legacy TCP traffic
is not encrypted. Keep private phone metadata on the trusted LAN only.
