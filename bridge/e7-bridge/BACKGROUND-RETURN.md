# E7 Bridge v0.8.3: return from Background (experimental)

## Physical bug report

On the real Nokia E7 with v0.8.2, selecting **Background** preserved the
authenticated socket but could make the app window impossible to reopen. A
capture from Sanctuary showed traffic on the E7 Bridge TCP port while the UI
was not accessible. This does **not** establish whether the app could be
restored using every launcher or task-switcher path.

## Narrow code change

v0.8.2 called `QWidget::showMinimized()`. For the Symbian build, v0.8.3
instead uses `CCoeEnv::Static()->RootWin().SetOrdinalPosition(-1)`.
This moves the native window group to the background **without** setting
Qt's minimized window state. It follows a documented historical Symbian Qt
pattern: https://stackoverflow.com/questions/10673624/qml-symbian-hide-app

Other platforms keep `showMinimized()`. Build explicitly links `cone` and
`ws32` for the native API; neither UID nor app capability changes.
The existing authenticated socket, pairing storage, package installer,
admin framing, native music and Wi-Fi are deliberately untouched.

**Status:** source assertions updated; the pinned Qt 4.7.4/GCCE native
compile and real E7 behaviour still require operator verification.
This is a *candidate*, not a proven fix.

## Build with existing toolchain and signer

On Sanctuary, after checking out this branch in the existing project:

```bash
python3 -m unittest discover -s bridge/e7-bridge/tests -q
bash -n bridge/e7-bridge/build/*.sh
cd bridge/e7-bridge
bash ./build/build-with-pocketjs.sh --pocketjs "$HOME/StudioProjects/pocketjs"
file dist/E7Bridge-v0.8.3.sis
sha256sum dist/E7Bridge-v0.8.3.sis
```

Do **not** remotely self-upgrade the bridge while it runs. Preserve your
known-good v0.8.2 and v0.8.0 signed SIS and existing pairing settings.
If the current window is inaccessible, try the phone's **hold Menu** native
task switcher to open/close the application. Only if necessary, manually
restart the handset after saving other work to clear the orphaned session.
Transfer v0.8.3 SIS by USB/manual file transfer and let the native Belle
installer handle it. No protected filesystem writes, FOTA changes or reboot
at installation are requested by this patch.

## Real E7 acceptance

1. Open E7 Bridge v0.8.3; connect to the existing Sanctuary host and run
   `info` and `ping`.
2. Press **Background** once; using Sanctuary run `ping` again.
3. Long-press the E7's physical **Menu/Home** button and select **E7 Bridge**
   in the native task switcher. Its UI should be foregrounded with the
   current authenticated session **without needing another Connect**.
4. Repeat background/return twice and try launching its icon while it is
   backgrounded. Check whether the original session survives.
5. Press **Disconnect** and **Exit Bridge**. Relaunch manually; confirm
   remembered pairing works. Finally verify native Music, Wi-Fi, standby.
6. Report the build output and actual on-device pass/fail. If it fails,
   revert to your saved signed v0.8.2 SIS without uninstalling/resetting
   app data or changing ROMPatcher/system settings.

The E7 does not have a physical red End button. The optional AVKON End
key event filter is unchanged and is outside this fix's physical test.
