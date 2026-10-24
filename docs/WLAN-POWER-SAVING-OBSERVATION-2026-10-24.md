# Nokia E7 WLAN power saving: provisional fix and next acceptance

**Recorded:** 2026-10-24
**Handset:** E7-00 / RM-626 / Belle Refresh 111.040.1511 (known project identity).
**Status:** user reports improvement; not yet a verified lasting fix.

## What the operator observed

The E7 had intermittently ceased providing useful Wi-Fi, and the operator suspected WLAN-specific power saving. After adjusting WLAN power saving in Belle settings, the operator reported: 'I think the power saving fixed it.' The exact before/after effective CommsDat values, interval of normal use, AP deauthentication logs, and the on-screen Wi-Fi toggle at the moment of the former failure were not captured. Do not silently upgrade this to a measured root cause.

## What the stock firmware and Symbian source establish

- Our preserved stock E7 Z: variant CommsDat includes WlanLastSessionClosedTimeout=1, WlanLastSocketActivityTimeout=-1, WlanLastSocketClosedTimeout=-1 and WlanPowerMode=1. These are factory source values, not verified current C: database values.
- Symbian's Customisation Interface documents the WLAN connection-lifetime timeout values as **seconds** and -1 as unlimited. One second after the last application session closes could contribute to a normal idle disconnect; it does not prove the Wi-Fi toggle turned Off.
- The Symbian WLAN server stores iPowerSaveEnabled from settings.powerMode, confirming this is a separate power-saving control; the user-facing setting is not equivalent to application ownership of an access point.
- Separate E1GW Reborn ROM comparison indicates the language pack retained stock WLAN-related defaults. Nothing from Reborn was installed during this observation.

Relevant original source:
- https://github.com/cdaffara/symbiandump-os1/blob/a48c2548bd6f6086dc5dd4a8b19705da2176039c/sf/os/deviceplatformrelease/foundation_system/sf_config/CI_external/customisation/CustomisationInterface/confml/CI_commsdatcreator.confml
- https://github.com/SymbianSource/oss.FCL.sf.mw.ipconnmgmt/blob/7c6f294faf11b41753e2402de392b6359acc8a2e/dbcreator/commsdatcreator/src/cdcwlantables.cpp
- https://github.com/SymbianSource/oss.FCL.sf.os.wlan/blob/7d13c530bec186a64107a3f1e69cd60d235d5abf/wlan_bearer/wlanengine/wlan_symbian/wlanengine_symbian_3.1/src/wlmserver.cpp

## Low-risk validation gate

1. Record the current WLAN-specific power-saving setting and note whether the phone is on battery or charging.
2. Manually connect to the trusted E7-Sanctuary-Lab network. Confirm the Wi-Fi toggle shows On and the E7 browser loads a local host page.
3. Close E7 Bridge and all diagnostic keep-alives; lock the phone for five minutes, then unlock and reload a local page.
4. Record separately: Wi-Fi toggle state, whether an access point is associated, whether a connection is created on demand, and whether the page reload works. These are not interchangeable outcomes.
5. Repeat during normal use over a longer period. If disabling power saving causes unacceptable battery drain or another regression, restore the previous setting.
6. Do not interpret a host's missing AP association alone as evidence of the phone's Wi-Fi toggle moving to Off.

A separate **host-only** news-gateway candidate has passed eleven offline unit tests. Its live E7/browser behaviour is not yet proven. It is intended to exercise meaningful HTTPS-to-trusted-LAN service access while observing this WLAN setting; it does not run an always-on ping or modify the handset.

## Safety and provenance

No flashing, ROM transplant, kernel module modification, C: private database write, package install, or user-file mutation is authorised by this observation. The existing stock recovery preflight stays in force. Symbian WLAN source is credited above. Reborn CFW comparison was performed against the official symbuzzer firmware and E1GW pack, with upstream contributors acknowledged; no Reborn payload is included in this public note.

