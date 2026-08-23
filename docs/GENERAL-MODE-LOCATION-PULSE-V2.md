# General-mode location pulse v2

Prepared: 2026-08-24

## Why this probe exists

The first controlled state write succeeded. The E7 acknowledged
`AT+CFUN=1`, read-back proved CFUN 1, and the serial interface remained healthy.
With no SIM, registration changed from unavailable to denied and no operator
was selected. The user then opened Belle's top status/settings drawer; the
handset froze and required a hard reset. Reboot restored the normal no-SIM
Offline state.

Nokia's Symbian implementation shows that this command directly requests
General profile ID 0 and waits for the normal RF-on system state. It is not
merely an opaque modem toggle. Separate Symbian UI code normally prevents
leaving Offline when the SIM-status property is `ESimNotPresent`; the AT plugin
uses the lower profile-engine interface and bypasses that UI check.

The evidence therefore separates two claims:

- General mode can be reached without a SIM through the bounded AT path;
- Belle's top status/settings drawer is unsafe in that contradictory state.

It does not yet show whether Camera's local location setting or integrated GPS
can operate safely in the same state.

## Exact experiment

The v2 helper performs the original ownership, supported-value, CFUN 0,
no-usable-SIM, and no-registration checks. It then:

1. transmits exactly `AT+CFUN=1`;
2. proves CFUN 1 and rechecks SIM and registration state;
3. opens a fixed 90-second observation window;
4. polls CFUN every five seconds and registration every ten seconds;
5. transmits exactly `AT+CFUN=0` when the window ends or Ctrl-C is received;
6. requires read-back proving CFUN 0.

No reset parameter, persistent profile command, phone-file write, package
installation, call, message, or data-session command is permitted.

## Handset action

Before starting, place Camera on screen so its Settings menu is easy to reach.
During the 90-second pulse, perform only:

`Camera` → `Settings` → `Save location info`

Record whether the setting can be enabled and whether Camera remains
responsive. Do not open the top status/settings drawer, Maps, positioning
settings, connectivity settings, Profiles, or any telephony surface during
this pulse.

The host will attempt to restore Offline/CFUN 0 automatically. If the handset
freezes, hard-reset it once, do not repeat the pulse, and preserve the generated
report.
If the pulse is partial but the handset and USB interface remain responsive,
run the included explicit rollback wrapper:

```bash
./scripts/e7-general-mode-trial-v1.sh rollback
```

## Interpretation

- **Camera accepts location and rollback passes:** the location policy can be
  released independently of the broken top drawer. Retain this as evidence for
  a narrower no-SIM location repair.
- **Camera still reports Offline:** its policy state did not follow the General
  transition, despite the proven profile/RF state.
- **Camera freezes:** another consumer cannot tolerate General without a SIM;
  stop runtime forcing and investigate a SIM-status or location-specific patch.
- **Host loses CFUN proof:** treat the transition as unstable and use the
  attempted automatic rollback or one hard reset only.

This pulse is diagnostic. It is not a candidate permanent operating mode.

## Observed result and closure

The phone entered General mode and Camera remained capable of rendering its
viewfinder. The wider system then became unresponsive. The AT endpoint stopped
answering during the pulse, so the automatic `AT+CFUN=0` rollback could not be
delivered or verified. A hard reset was required and restored the normal
Offline state.

The split behaviour is consistent with a system/profile/telephony deadlock
rather than loss of display, camera hardware, or total power. Runtime
General/RF-on forcing without a SIM is closed and must not be repeated.

The location problem moves to firmware and policy analysis. Camera's open
source geotagging path calls `RLocationTrail` directly, while the corresponding
Location Trail source includes explicit Offline handling and continues to
consume GPS positions. The preferred repair is therefore a narrow
Offline-safe Location Trail/LBS/profile-policy change, not a permanent General
mode or deletion of foundational telephony libraries.
