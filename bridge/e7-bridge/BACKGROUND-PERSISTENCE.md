# E7 Bridge phone-side v0.8.2: connected-session background persistence

**Status (2026-10-11): the owner reports a signed v0.8.2 SIS was built, installed and the Background workflow plus other visible functionality work on the physical Nokia E7. The precise native build log and per-step ping/INFO results have not been reviewed in this PR. The E7 does not have a physical red End key, so the AVKON End-key filter was not exercised.**

## What problem this attempts to fix

On Symbian Belle, the **red End key** can cause an ordinary Qt GUI application to exit.
Previously, E7 Bridge only stayed connected while its window remained alive.
Qt for Symbian supports `QApplication::symbianEventFilter()`; this version
intercepts AVKON's `KAknUidValueEndKeyCloseEvent` **only after a successful,
owner-initiated HMAC handshake**. The native phone UI still comes forward,
but the bridge Qt event loop and connected TCP client are left alone.

A **Background** button also calls `showMinimized()` on the top-level window;
it does *not* hide/delete the Qt application or close the link. Use the Symbian
task switcher to return. A separate **Exit Bridge** button stops the link and
terminates the process. **Disconnect** ends the session and restores the red
End key's normal close behaviour. Pairing is still only restored as text, not
an automatic network connection. No boot/autostart package or privileged daemon
is involved. `C:/private` settings location, UID3, capability flags, native
SIS registry and HMAC/admin protocol are unchanged.

**Limits:** This does not guarantee process survival under memory pressure,
background power management, or Wi-Fi loss; it does not automatically reconnect.
A switch of foreground window is not identical to an OS process exit, and this
fix targets the documented Qt/Symbian End-key close event. A separate Wi-Fi
lifecycle recovery feature may be needed if the Nokia still drops its socket
when apps change.

## Build on Sanctuary

Use the **same pinned** `sr1-qt474-v1` PocketJS toolchain and signing identity
as the installed v0.8.0 SIS:

```bash
cd ~/Downloads/e7-bridge-phone-v0.8.2
python3 -m unittest discover -s tests -q
bash ./build/build-with-pocketjs.sh --pocketjs "$HOME/StudioProjects/pocketjs"
ls -lh dist/E7Bridge-v0.8.2.sis
```

**Never use the bridge to replace its own running SIS.** Keep the verified
`E7Bridge-v0.8.0.sis` and a local backup of the pairing information. End the
running bridge session, exit E7 Bridge on the handset, transfer the newly signed
v0.8.2 SIS via USB or normal file transfer, and open it with Belle's native
installer. It must use the same package UID and signing identity. If the
installer refuses an upgrade or the saved pairing goes missing, stop; do not
remove the working application or reset its private data to force it.

## Physical acceptance gates

1. Start the existing **v0.9 Sanctuary host** (v0.8.1 also compatible). Launch
   E7 Bridge v0.8.2 manually and press Connect; `info` should identify v0.8.2.
2. Keep the phone on the bridge, `ping`. Press **Background** and switch to
   Mail or Music via Symbian's task switcher. `ping` again. Run a full
   `baseline capture mail-open` if connected.
3. Use the E7's physical **Menu/Home key** and task switcher to navigate back and forth while the authenticated bridge remains responsive. The Nokia E7 does **not** have a physical red End key; do not require an End-key hardware test. The optional native AVKON filter is untested on this model.
4. Press **Disconnect**, check the host connection ends, and then verify
   **Exit Bridge** terminates it if launched again. Confirm manual Connect and
   remembered pairing work on relaunch.
5. Turn Wi-Fi off *only after finishing this test*, if wanted. A dropped
   network connection will still require manually starting the Sanctuary host
   and reconnecting. Do not conflate that with ordinary backgrounding.

The owner reports native build/install and working background behaviour on the real E7. Treat finer-grained acceptance evidence (e.g. INFO, ping while backgrounded, pairing, Exit) as operator-reported until its logs are supplied. Host-side Python/source assertions alone cannot prove hardware lifecycle behaviour.

## Historical API sources

- https://wiki.qt.io/How_to_Handle_the_Red_End_Key_in_a_Qt_Application
- https://qt.developpez.com/doc/4.7/qapplication/
- https://qt.developpez.com/doc/4.6-snapshot/qsymbianevent/

## Native compile correction (2026-10-11)

Sanctuary's pinned Qt/GCCE toolchain reached compilation but failed because including `avkon.hrh` also included `AknFontCategory.hrh`, which is unavailable through the existing compiler include paths. The only value the bridge needs is the public AVKON End-key close event number, `KAknUidValueEndKeyCloseEvent = 0x101F87F0` (verified in the historical Symbian public `avkon.hrh`). The phone source now uses `KE7EndKeyCloseEvent = 0x101F87F0u` instead of importing all of `avkon.hrh`; the source regression test was updated accordingly. This avoids modifying system headers or compiler volumes. After this fix, the owner reports a successful native SIS build/install and working Background functionality. The End-key test is **not applicable** to the E7 hardware. Keep the previous signed v0.8.0 SIS for rollback.

## Physical Nokia E7 correction (2026-10-11)

The E7-00 has a **Menu/Home hardware key** and an **on-screen call-ending control**, not a physical red End key (see the Nokia E7-00 user guide's Keys and Parts and Telephone sections). The AVKON End-key interception was inherited from general Symbian Qt guidance and is not the actual feature that the owner was able to test. **Background** minimises the app and retains its authenticated session; this is the reported working mechanism. No handset-side End-key behaviour has been verified. The developer may eventually simplify the unused compatibility code, but do not change a newly working binary based on an untested assumption.
