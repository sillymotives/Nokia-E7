# USB interface map

Captured: 2026-08-23

| Phone mode | USB ID | Host exposure | Status |
| --- | --- | --- | --- |
| Mass storage | `0421:0333` | `/dev/sdb`, one 15 GiB VFAT partition | Proven, unmounted |
| Nokia Suite | `0421:0335` | Composite device with 18 interfaces | Proven |

## Nokia Suite functions

| Function | Interface(s) | Linux binding | Evidence |
| --- | --- | --- | --- |
| Imaging/PTP/MTP | `00` | No kernel driver; udev marks MTP/PTP | Proven |
| Serial ACM A | `01` control, `02` data | `cdc_acm`, `/dev/ttyACM0` | Proven Nokia-owned |
| Serial ACM B | `03` control, `04` data | `cdc_acm`, `/dev/ttyACM1` | Proven Nokia-owned |
| CDC WMC | `05` | Unbound | Observed |
| Additional CDC pairs | `06`–`13` | Unbound | Observed |
| Phonet | `14` control, `15` data | `cdc_phonet`, `usbpn0` | Proven |
| Additional CDC pair | `16`–`17` | Unbound | Observed |

`ttyACM0` and `ttyACM1` are candidates for information-only AT interrogation.
Their semantic roles have not yet been proved. `usbpn0` is a Phonet transport,
not ordinary IP networking merely because NetworkManager displays it.

