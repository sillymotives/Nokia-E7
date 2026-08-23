# Recovered Nokia E7 serial toolkit subset

This directory preserves the non-private serial and USB probing portion of a
Linux toolkit recovered on 2026-08-23 from an archive dated 2026-08-05.

The original ZIP had SHA-256:

`e1f4b1e2123fe94988a3cb0c25b29c5153d7a9c65d546c6d96fffe17fb49bd1e`

## Included reference scripts

- `02-inspect-suite-mode.sh`: host-side Nokia Suite interface inventory.
- `03-identify-serial.sh`: AT identity queries.
- `04-live-status.sh`: AT battery, radio, registration, and clock queries.
- `05-data-capabilities.sh`: AT command, phonebook, and SMS capability queries.
- `06-visible-controls.sh`: AT keypad and backlight capability queries.
- `07-blink-display.sh`: intentionally changes and restores backlight state.
- `08-menu-press.sh`: intentionally sends one emulated Menu keypress.
- `lib/e7_at.py`: dependency-free serial AT transport used by the scripts.

These are preserved as historical reference, not an active run order. The old
transport probes generic `ttyACM` devices without independently proving that
each belongs to the Nokia. The current project first performs fresh USB and
udev enumeration, then binds any AT probe to a host-proven Nokia interface.

Scripts `07` and `08` change visible phone state and are outside the current
read-only gate.

The original toolkit README and mass-memory imaging script are not published
here because they contain a private host filesystem path. Their safety analysis
and preservation receipt are recorded in `docs/TOOLKIT-AUDIT.md` and
`docs/PROJECT-STATE.md` without disclosing that path.

