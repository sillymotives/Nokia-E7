# Historical toolkit audit

Audited: 2026-08-23

## Artifact

- Filename: `nokia-e7-toolkit.zip`
- SHA-256: `e1f4b1e2123fe94988a3cb0c25b29c5153d7a9c65d546c6d96fffe17fb49bd1e`
- Contents: 12 ZIP members, 11,343 bytes uncompressed.
- Archive-path validation: no absolute paths or parent-directory traversal.
- File types: regular files and directories only; no archived symlinks.

The ZIP itself is not committed. Its text contents are preserved under
`archive/nokia-e7-toolkit-20260805/`.

## Behavioural review

- `01-preserve-mass-memory.sh` identifies exactly one removable Nokia `S60`
  USB disk, checks USB identity and size, unmounts its mounted partitions, and
  reads it into a host-side image. It does not write to the source disk.
- `02-inspect-suite-mode.sh` performs host-side inspection only.
- `03` through `06` transmit information-query AT commands over `ttyACM`.
- `07-blink-display.sh` intentionally changes the backlight state briefly and
  attempts to restore its reported original state.
- `08-menu-press.sh` intentionally sends one emulated Menu keypress after an
  interactive confirmation.
- The Python transport opens serial ports read/write because AT queries must be
  transmitted. It does not independently select or validate Nokia ownership of
  every discovered `ttyACM` port.

## Decision

The toolkit is valuable historical evidence and reusable reference code, but
its active scripts will not be run blindly. Fresh Nokia Suite-mode enumeration
comes first; subsequent probes will bind explicitly to a host-proven Nokia
interface. Scripts `07` and `08` remain outside the current read-only gate.

