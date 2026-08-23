# Integrated GPS and offline Maps probe v1

Prepared: 2026-08-23

## Purpose

Prove the E7's integrated satellite receiver independently of A-GPS, network
positioning, map downloads, and retired Nokia services. Then determine whether
the installed Maps client can render any existing local map content.

These are separate questions. A position fix can succeed over a blank map, and
street tiles can be cached without proving a fresh satellite fix.

The earlier read-only mass-memory census found a `cities` tree with Nokia Maps
catalogue/icon scaffolding, but the entire filesystem usage was far too small
to contain a substantial offline map region. Missing street detail is therefore
expected and is not evidence of failed GPS hardware.

## Phase A: record positioning methods

Open:

`Settings` → `Application settings` → `Positioning` → `Positioning methods`

Record every method shown and its current enabled state before changing
anything. Expected families may include integrated GPS, assisted GPS,
network/Wi-Fi positioning, and Bluetooth GPS; use the handset's actual labels
as evidence.

For the isolated receiver test:

- enable only the integrated/internal GPS method;
- disable assisted GPS and network-based or Wi-Fi positioning;
- leave Bluetooth GPS disabled unless an external receiver is intentionally
  being tested;
- disconnect Wi-Fi before opening Maps.

These changes are reversible. Do not alter positioning-server addresses,
download map data, sign into an account, or accept a paid/mobile connection.

## Phase B: cold satellite fix

1. Take the phone outdoors with a broad view of the sky. Avoid testing through
   coated glass or while the handset is surrounded by metal.
2. Open `Maps`, choose the current-position/My position view, and decline or
   cancel any online connection prompt.
3. Keep the phone reasonably still and do not cover its upper or lower edges.
4. Allow up to 20 minutes for this first isolated fix. A device unused for
   years may have no useful satellite assistance or current orbital data.
5. Record separately:
   - whether the position indicator changes from searching to fixed;
   - the displayed accuracy, if any;
   - approximate time to first fix;
   - whether the position follows a short walk;
   - whether map orientation responds when the phone is turned;
   - whether streets/labels render, a blank grid appears, or Maps asks to go
     online.

Do not record or publish the exact home location. A broad result such as
`outdoors in Cardiff area, correct within one street` is sufficient.

## Phase C: local state

If a fix succeeds, create one temporary favourite named `KAI GPS TEST`, close
Maps, reopen it, and confirm the favourite persists. Delete only that exact
test favourite afterward.

Do not test traffic, weather, search, sharing, check-in, account sync, or Map
Loader yet. Those mix local Maps behaviour with remote dependencies.

## Interpretation

- **Fix and map detail:** retain integrated GPS and the local Maps renderer;
  later prove route calculation and establish a reproducible offline map set.
- **Fix but no map detail:** retain GPS; repair offline map content separately.
- **No isolated fix:** repeat once outdoors after verifying integrated GPS is
  enabled. Only then investigate antenna, receiver state, or an assisted-data
  bootstrap.
- **Map detail but no fix:** local tiles exist, but receiver evidence remains
  absent.
- **Favourite persists:** local Maps data storage is functional regardless of
  online service status.

## Observed result

The handset exposed Assisted GPS, Integrated GPS, Bluetooth GPS,
Wi-Fi/Network, and Network based methods. For the isolated attempt, Integrated
GPS was left enabled and the other methods were disabled.

Maps did not expose a position view. It stopped at a `Street maps` screen
reporting that new street maps were required; dismissing that screen exited the
application. A search of the installed application surfaces did not find a
separate GPS Data, Location, or Landmarks front end. Camera's location setting
then supplied the decisive policy clue: location is not supported while the
phone is in Offline mode.

The absent street-map payload remains a separate repair problem, but Offline
mode now blocks a clean integrated-GPS test before map rendering can be judged.
The next bounded experiment is the runtime functionality trial in
[`GENERAL-MODE-TRIAL-V1.md`](GENERAL-MODE-TRIAL-V1.md).

## Evidence basis

The Nokia E7-00 Nokia Belle user guide documents Maps, positioning, favourites,
and offline use as native device functions. Handset observation determines
which parts remain functional on this firmware and installation.
