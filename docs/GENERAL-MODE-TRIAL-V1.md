# Guarded General-mode runtime trial v1

Prepared: 2026-08-23

## Purpose

The no-SIM handset boots into Belle's Offline profile. Maps cannot pass its
missing-map screen, the separate GPS Data application is not exposed, and
Camera refuses location recording while Offline. The first controlled system
state write therefore tests the modem-functionality layer beneath that UI.

This is a runtime experiment, not a claim that the AT modem state and Belle's
visible profile are identical. A successful `AT+CFUN=1` may unlock General or
location services, or it may prove that the UI policy lives above the modem and
needs a different repair.

## Exact mutation

The helper allowlists only these set commands:

- apply: `AT+CFUN=1`;
- rollback: `AT+CFUN=0`.

The 3GPP/ETSI command model defines value 0 as minimum functionality and value
1 as full functionality. The script sends no reset parameter, `AT&W`,
persistent-profile command, call, message, packet-data command, SIM command, or
manufacturer/test command.

Before apply it must prove:

- the exact Nokia E7 Suite-mode interface and responsive interface number;
- AT attention;
- both values 0 and 1 in `AT+CFUN=?`;
- current `AT+CFUN?` value 0;
- no usable SIM through `AT+CPIN?`;
- no registered cellular state through `AT+CREG?`;
- accompanying operator and signal evidence for the run report.

After the write it requires `AT+CFUN?` value 1 and repeats SIM, registration,
operator, and signal queries. An unexpected usable-SIM or registered state
triggers an automatic attempt to restore value 0.

## Use

Put the E7 in Nokia Suite USB mode and close any program using its serial/MTP
interfaces. From the extracted toolkit run the read-only preflight first:

```bash
./scripts/e7-general-mode-trial-v1.sh inspect
```

Review its report. If it passes with current CFUN 0, perform the authorised
runtime write:

```bash
./scripts/e7-general-mode-trial-v1.sh apply
```

After a successful apply, inspect the visible phone profile and retry:

`Camera` → `Settings` → `Save location info`

Do not add a SIM, enable Wi-Fi/network positioning, accept a cellular
connection, or reboot during this first observation.

Rollback is explicit and idempotent:

```bash
./scripts/e7-general-mode-trial-v1.sh rollback
```

If apply changes neither the visible profile nor Camera's location boundary,
run rollback. The result then locates the restriction above the AT modem layer;
it does not justify guessing at persistent Symbian repositories.

## Persistence boundary

No persistent setting is requested. A power cycle may return the no-SIM phone
to Offline/CFUN 0 even if the runtime trial succeeds. Persistence, if later
desired, requires a separate evidence-backed design and its own rollback.

## Observed result

The guarded apply completed successfully on 2026-08-23. Read-back proved the
transition from CFUN 0 to CFUN 1. The no-SIM query still returned an error,
registration became denied rather than active, the operator remained empty,
and the AT interface stayed responsive through the completed report.

The handset remained usable until the user opened Belle's top status/settings
drawer. It then froze and required a hard reset. Reboot restored the original
no-SIM Offline state. The script itself did not request a reset and had already
finished successfully before the interaction-triggered freeze.

Primary Symbian source resolves the earlier uncertainty: Nokia's CFUN handler
maps value 1 directly to General profile ID 0 and waits for the normal RF-on
system state. Separate Profile Engine and SysAp UI paths normally refuse the
Offline-to-General transition when the SIM property is not usable. The AT
plugin reached the lower profile interface and bypassed that UI guard.

The first write therefore succeeded but is not a safe permanent mode. The
timed follow-up also deadlocked, stopped answering AT commands, and required a
hard reset after its automatic rollback became unreachable. Runtime no-SIM
General/RF-on forcing is closed. See
[`GENERAL-MODE-LOCATION-PULSE-V2.md`](GENERAL-MODE-LOCATION-PULSE-V2.md).
