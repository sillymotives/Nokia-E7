# Nokia E7: phase 1 native application pruning

Prepared: 2026-10-24
Status: planning and read-only package triage; **no phone cleanup has been performed by this PR**.

## Objective and hard boundaries

Turn the Nokia E7-00 / RM-626 / Belle Refresh 111.040.1511 into a clean, useful **Wi-Fi-only pocket computer**. Remove distracting dead-service launchers from the normal workflow and, **only after a verified reinstall/rollback path**, consider actually uninstalling demonstrably disposable SIS packages.

Avoid the tempting but unsafe shortcut of deleting ROM `Z:` binaries, `C:/sys`, `C:/private`, disabling startup services based on their names, or flashing an unknown product/keyboard variant. A preserved ROM/Z: archive is not a writable C: backup, nor proof of stock dead-USB flash recovery. Do not reinstall or flash Reborn merely to clean up a menu.

Separate *hiding an application launcher* from *uninstalling an installed package*, from *removing a boot service*. The first improves usability; it does not necessarily free RAM or prevent startup processes.

## Evidence from our own E7

- The visual 2026-08-23 [NATIVE-CENSUS.md](NATIVE-CENSUS.md) records the handset's main application menu and 13 named entries in Belle's **Already installed** list.
- E7 Bridge v0.8.0 / Sanctuary host v0.8.1 can query Belle's **SIS package registry** through `packages all` and `pkg UID` without changing the handset. On 2026-10-10 this returned **407 registry entries**. These are **not** 407 uninstallable apps; many are framework/base packages, and the registry is not equivalent to AppArc launcher inventory.
- Media playback, camera/gallery/editors, notes, clock, calendar, basic documents and E7 Bridge have documented physical acceptance. WLAN power-saving adjustment was reported beneficial on 2026-10-24 but awaits a longer lock/unlock trial.
- The app and package census is historical. **Confirm names and current install state on the actual E7** before any destructive action.

## Stage A: make the UI useful without uninstalling anything

Create a `Legacy Nokia` folder in Belle's application menu. The Belle menu supports **New folder**, then long-press icon -> **Move to folder**. If the visible options differ, follow the handset's own menu rather than attempting filesystem manipulation.

**High-confidence *menu-clutter* candidates** (move, do not uninstall yet): `Store`, `Weather`, `Nokia Music`, `Social`, `Nat Geo`, `My Nokia`.

**Service-dependent or uncertain; park in a folder such as `Later / Legacy`**: `Microsoft Apps`, `Communicator`, `Guides`, `Public Transport`, `Map Loader`. This classification reflects a Wi-Fi-only use case, not proof that every feature is nonfunctional.

**Protect for later integration or recovery**: `Maps`, `Drive`, `Mail`, `Nokia Sync`, `SW update`, and `User guide`. These may be parked in a `Tools / Later` folder but their components must not be uninstalled in this phase. Navigation, synchronisation and installed software management still have possible future uses.

**Keep readily accessible**: `Contacts`, `Calendar`, `Web`, `Settings`, `Files`, `Music player`, `FM radio`, `Videos`, `Camera`, `Gallery`, `Video editor`, `Photo editor`, `Recorder`, `Clock`, `Notes`, `Calculator`, `Dictionary`, `Zip`, `Adobe Reader`, and `E7 Bridge` where installed. Keep `Search` as long as device-wide search is useful. Keep native system control surfaces, even if their launcher is placed in a folder.

**Cellular-specific shortcuts** (`Messaging`, `Log`, possibly `Msg. reader`) can go in a `Phone / Legacy` folder if not in use. Do not remove telephony, emergency-call or RF-profile components; offline/no-SIM operation previously had serious device-state failures.

Remove only obsolete **home-screen widgets or shortcuts** after noting what they are, not deleting home-screen panels or personal data. Some widgets poll external services; removing a widget is not proof that its underlying package or service stopped.

**Acceptance after Stage A:** a shorter first-level menu; useful local apps remain reachable; Web and E7 Bridge connect on the trusted WLAN; Music player, Camera, Files, Clock, and standby still work; no unsolicited new network prompts. Restore an icon by moving it back out of the folder.

## Stage B: read-only current-state uninstall triage

From the existing E7 Bridge v0.8.0 app and Sanctuary host v0.8.1 on a **trusted LAN**, manually connect and run:

```text
e7> info
e7> packages all
```

Keep output privately on Sanctuary. Do **not** publish raw registry dumps, screenshots, pairing keys, device identifiers, network addresses or personal application data. Use `pkg 0xXXXXXXXX` for only the relevant package UIDs found in the output.

### Candidates from the 2026-08-23 “Already installed” UI census

| Package as displayed | Treatment | Why |
| --- | --- | --- |
| Nat Geo (1 MB) | **Conditional uninstall candidate** | Service/catalogue-oriented application; check actual current SIS package name/UID and obtain exact reinstall file first |
| Social (3 MB) | **Conditional uninstall candidate** | Service-oriented UI; ensure no needed contacts/media integration and preserve reinstallation path |
| Microsoft Communicator (3 MB) | Review *later*, not first | May depend on Microsoft Shared and service registration |
| Microsoft Shared (7 MB) | **Hold** | Shared component; deleting it may break other installed Microsoft functions |
| JoikuSpot Light Engine (60 kB) | **Hold** | Hotspot/network integration could interact with the newly stabilised WLAN |
| Adobe Reader LE (4 MB) | **Retain** | Offline PDF rendering passed |
| Security Engine (324 kB) | **Protect** | Security/system role is insufficiently mapped for removal |
| Nokia Notifications Support (1 kB) | **Protect pending dependency audit** | Very small shared/support component |
| PhotoEditor and VideoEditor AIW/memory/OOM plugins | **Retain** | Dependents include native editors we have proven usable |
| Ambiguous 16-kB “lkm/Ikm” entry | **Do not touch** | Label identity not yet confirmed |

A package's name, small size or status as a SIS base entry is never sufficient reason to uninstall it.

## Stage C: actual uninstallation, one package at a time, only when gated

The handset's Belle user guide describes **Settings -> Installations -> Already installed -> long-press package -> Remove** (regional wording may vary). This is an operator-visible uninstall with side effects, not a `packages all` bridge command.

**Hard preconditions for each candidate:**

1. Confirm exact current package name, UID and version and whether it is user-installed, firmware-provisioned or a shared component.
2. Possess and verify the **exact original SIS/SISX installer and signing requirements** (or a tested complete app restore), plus backup of any data to preserve. ROM/Z: extraction alone is insufficient.
3. Document a non-destructive rollback/reinstall test or refrain from uninstalling. There is no supported E7 Bridge remote uninstall/rollback command.
4. Change **only one** package, using Belle's Application manager UI. If it warns about dependencies, refuse. Do not uninstall `Microsoft Shared`, security components, editor plugins, or the live E7 Bridge to clean the menu.
5. Reboot only normally if required; confirm boot, Wi-Fi on locked/unlocked phone, browsing, music, camera/gallery, USB, E7 Bridge, standby, and previously working applications. Record failures and stop before any other removal.

Do **not** claim RAM, battery, storage or boot performance gains without before/after measurements. Menu pruning primarily improves ergonomics.

## Stage D: optional service/startup pruning

A separate, much higher-risk project that requires dependency mapping, baseline boot snapshots, verified C: preservation, matching stock firmware, a dead-USB restore route, and a reversible patch. **Not authorised by this document**.

## Provenance and references

- [NATIVE-CENSUS.md](NATIVE-CENSUS.md), [NATIVE-RESTORATION.md](NATIVE-RESTORATION.md), [CORE-OFFLINE-SMOKE.md](CORE-OFFLINE-SMOKE.md).
- [Bridge package registry implementation and limitations](../bridge/e7-bridge/PACKAGE-MANAGER.md).
- Nokia E7 Belle guide: <https://nokia-e7-00.helpdoc.net/en/nokia-e7-00-user-guide/phone-management/manage-applications/remove-an-application-from-your-phone/> (uninstall instructions and dependency warning).
- All About Symbian, Belle menu folders: <https://allaboutsymbian.com/features/item/13551_How_to_Speed_your_way_around_h.php>.
- Official Nokia E7 user guide archived at <https://nds1.webapps.microsoft.com/phones/files/guides/Nokia_E7-00_Nokia_Belle_UG_en.pdf>.

No Reborn files or third-party software are copied into this plan. Upstream Symbian and Reborn authors remain credited in their respective technical investigations.
