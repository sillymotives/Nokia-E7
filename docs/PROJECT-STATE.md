# Project state

Updated: 2026-08-23

## Scope

- Device family: Nokia E7-00, US model, running Nokia Belle Refresh.
- Intended role: Wi-Fi-only modernised pocket computer.
- Excluded: restoration of cellular service.
- Strategy: retain useful native functions, repair or bridge valuable broken
  dependencies, and prune dead surfaces reversibly.

## Evidence boundary

This public page records conclusions, not raw captures. Private evidence may
contain host paths, device identifiers, storage identifiers, network details,
personal filenames, or exact locations. Those values and the private
preservation-image receipt are deliberately excluded from the repository.

The test scripts independently prove their target device and storage before a
write. Generated run bundles remain private until reviewed and sanitised.

## Proven host and transport paths

- The phone exposes distinct Nokia Suite and Mass storage USB personalities.
- A bounded AT-information probe identified the model and firmware without
  exercising cellular or manufacturer-test commands.
- Mass memory can be mounted read-only for census work.
- Nokia Suite mode exposes a working, writable MTP Mass memory store and a
  separate read-only Phone memory store.
- A bounded MTP create, retrieve, byte-compare, and exact-object cleanup
  transaction passed.
- Persistent guarded deployments can create only a uniquely named folder,
  retrieve every returned object by ID, and verify its bytes.
- The E7 reaches a same-subnet host over Wi-Fi, and its native browser loads
  local HTTP, CSS, JavaScript, XHR, canvas, storage, audio, and video surfaces.

These conclusions are documented in the focused USB, AT, Mass-memory, MTP, and
Wi-Fi notes. Raw captures remain private.

## Handset baseline

- Date, time, and Cardiff time zone were corrected and survived a normal power
  cycle.
- The native menu, settings families, installed overlay, widget catalogue,
  home screens, and software-information surfaces were inventoried.
- The mass-memory census found normal Symbian scaffolding and very little user
  payload. The user confirms that its existing ordinary contents need not be
  preserved.
- A complete private mass-memory preservation image is recorded elsewhere,
  but must be freshly verified before any destructive storage or firmware work.

## Native functions retained

- Clock and alarms
- Calendar
- Notes
- Calculator
- Dictionary
- Offline User guide
- Files
- ZIP manager
- Adobe Reader
- Camera and Gallery
- Photo editor
- Video capture, playback, and editor
- Voice recorder
- FM radio
- Music player and native playlists
- Wi-Fi and the native browser as supporting infrastructure

Evidence includes local transactions, handset-originated capture, and
conservative imported TXT, PDF, ZIP, JPEG, MP3, and H.264/AAC fixtures.

Music player plays imported MP3s and its exercised controls work. Generic file
transfer preserved audio bytes but did not create a native playlist. The
track-aware MTP follow-up exposed Alpha and registered a real native playlist.
Beta did not appear through that particular probe, but the user considers the
working player fit for purpose; Music player is therefore **Retain** and the
missing second track is only a non-blocking ingestion observation.

The stock video player does not autorotate its playback surface, while system
rotation works elsewhere. This is a player-specific UI limitation, not evidence
of a failed orientation sensor.

## Deferred or unresolved

- HDMI/TV output is test-hardware blocked because the required cable is not
  available. This is not evidence of failure or success.
- A genuine local Office document handler has not yet been identified; the
  observed Microsoft Apps surface is account-dependent.
- Contacts import/export, Bluetooth roles, USB host, native backup/restore,
  Mail, Internet calling, VPN, and remote drives remain later gates.
- Store, Nokia/Ovi account surfaces, Nokia Music, Social, Weather, Public
  Transport, Web TV, and obsolete support links remain prune/bridge candidates
  after their useful local dependencies are separated from retired services.

## GPS and Maps result

The positioning settings expose Assisted GPS, Integrated GPS, Bluetooth GPS,
Wi-Fi/Network, and Network based methods. Integrated GPS was isolated, but Maps
stopped at a missing-street-maps screen and exited when that screen was
dismissed. No separate GPS Data, Location, or Landmarks front end was found.
Camera explicitly reports that location is unavailable in Offline mode.

The mass-memory census found Maps catalogue/icon scaffolding but no substantial
offline map region. Missing map data and the Offline-profile location boundary
are therefore tracked separately.

## First controlled system-state write

The guarded General-mode trial proved a transition from CFUN 0 to CFUN 1,
absent SIM context, denied rather than active registration, an empty operator,
and a responsive AT interface. Nokia's Symbian source confirms that this
command directly activates General profile ID 0 and the normal RF-on state.

The handset stayed usable until the top status/settings drawer was opened. It
then froze and required a hard reset. Reboot restored Offline mode. The script
had already completed successfully and sent no reset or persistent command.

## General-mode location pulse result

The timed follow-up also failed safely enough to preserve the handset, but not
cleanly enough to remain an available strategy. General mode appeared and the
Camera viewfinder continued rendering, then the wider system and AT endpoint
became unresponsive. The script's automatic `CFUN=0` rollback could not be
delivered or verified. A hard reset restored Offline mode.

Runtime no-SIM General/RF-on forcing is closed and must not be repeated. See
[`GENERAL-MODE-LOCATION-PULSE-V2.md`](GENERAL-MODE-LOCATION-PULSE-V2.md).

## Active gate: firmware recovery preflight

The project is now permitted to investigate custom firmware, but no image is
yet flash-authorised. The current gate inventories exact stock firmware,
product/variant identity, preservation images, Nokia service tools, and a
dead-USB recovery path. See
[`FIRMWARE-PREFLIGHT-V1.md`](FIRMWARE-PREFLIGHT-V1.md).

## Mutation policy

The active firmware preflight may create reports on the host and transmit only
the already-proven AT identity queries. Earlier storage transactions remain
documented but are not part of this gate. The preflight does not authorise:

- formatting or repartitioning;
- firmware flashing before the recovery preflight and exact image review pass;
- manual writes into Symbian-managed private/system trees;
- package installation or removal without a separate reviewed gate;
- account creation or acceptance of paid/mobile connectivity;
- deletion or overwrite of pre-existing phone objects.
