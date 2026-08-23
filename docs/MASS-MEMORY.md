# Mass-memory map

Captured: 2026-08-23

## Proven filesystem

- USB personality: `0421:0333` Nokia E7-00 Mass storage.
- Host disk during capture: `/dev/sdb`; device names are not durable.
- One approximately 15 GiB VFAT partition.
- Read-only capture mount options:
  `ro,nosuid,nodev,noexec` plus normal udisks VFAT options.
- Usage: approximately 18 MiB used and 15 GiB available.
- Objects: 321 directories, 120 files, no symbolic links.
- The capture unmounted the partition successfully.

## Contents

- Symbian-managed roots: `Private`, `sys`, and `cities`.
- Ordinary payload roots include `Installs`, `Games`, `Images`, `Music`,
  `Sounds`, `Videos`, `Playlists`, `Others`, and `DCIM`.
- No SIS or SISX installation packages were present.
- No top-level `resource` directory was present, consistent with no current
  application payload installed to mass memory.
- Nine JPEG files were present alongside gallery thumbnails and index
  databases.
- Nokia Maps catalogue/icon metadata exists, but the filesystem is far too
  small to contain a substantial offline map payload.

Most ordinary directories and several Symbian scaffolding directories have
2022 timestamps. This suggests a format, reset, or reinitialisation around that
period, but timestamps alone do not prove which operation occurred.

## Future write policy

The user explicitly confirms that none of the current mass-memory contents
matter or require preservation. The mass memory may therefore become a media
and application payload target without first retrieving the Acer image.

That statement is scoped to data value, not arbitrary mechanism. Direct manual
writes into `Private` or `sys`, filesystem formatting, and repartitioning remain
unauthorised. Application-owned content should normally be created through the
Symbian installer or the application itself.
