# E7 Bridge 0.4.1: remembered connection gate

Prepared: 2026-10-10. **Status: source candidate; Symbian build/on-device acceptance pending.**

## Requirement

Reduce post-reboot friction: the last **successfully authenticated** Debian IPv4 host and 16-hex pairing key are prefilled on next launch. Do not auto-connect or auto-start. The TCP protocol, HMAC, host controller and remote read-only command set remain unchanged.

## Symbian storage model

The application uses `QSettings(QApplication::applicationDirPath() + "/e7bridge-connection.ini", QSettings::IniFormat)` on the Nokia. Qt 4's Symbian `applicationDirPath()` maps to that executable's UID3-caged private folder. The default `QSettings::UserScope` is **not safe for secrets on Symbian**, as `C:/data/.config` is readable/writable by other apps.

The 64-bit development pairing secret is stored **in plaintext** inside that private folder. App sandboxing does not equal encryption at rest, especially against privileged tools, malicious firmware or exported phone backups. Do not use the same value as any other password. For now use only a trusted LAN and treat the token as a local-development credential.

When the operator unchecks Remember, the saved file's keys are cleared. `Forget saved pairing` also disconnects and erases the in-memory input fields. Both operations are **local settings writes only**, not user-file or firmware changes. The app never connects on launch. Failed authentication never stores entered values.

## Physical acceptance tests (before merge)

1. On Sanctuary run the existing Python host controller and confirm `python3 -m unittest discover -s tests -v` passes. Build the v0.4.1 SIS using the pinned PocketJS Qt 4.7.4 image and the same signer as v0.4.0.
2. Close the v0.4 bridge and install the v0.4.1 SIS on C: (phone memory). Confirm app splash and `info` both say v0.4.1.
3. Enter the trusted LAN host and existing key once. Keep Remember checked. Connect; verify `ping` and `metrics` work.
4. Disconnect; close and relaunch the app. Confirm the address and masked key fields are filled without typing. Verify it **did not connect automatically**. Connect manually; confirm `ping`.
5. Test failure containment: enter a deliberately incorrect key (without deleting the saved file), attempt auth and close; relaunch. The previously successful configuration should still be restored. Do not log or publish either secret.
6. Uncheck Remember, close/reopen: host and key should now be empty. Press Forget (including after previously saving) and verify both saved and visible details clear.
7. Confirm native music playback, Wi-Fi and standby work after exit; confirm no automatic network activity after launch.

No firmware updates, startup manipulation, automatic pairing or new capabilities are authorised. If SIS build fails or the app won't connect, reinstall the already physically accepted v0.4.0 signed SIS (same UID and signer). Uninstall/reinstall may affect private settings; preserve any other desired app data separately.
