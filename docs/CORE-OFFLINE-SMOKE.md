# Core offline native smoke test

Prepared: 2026-08-23

## Purpose

Prove the E7's high-value built-in offline applications before changing its
menu or installing software. This pass uses the native UI only and requires no
host payload, account, cellular service, or internet connection.

## Result vocabulary

- **Pass**: the tested native workflow completes and persists as expected.
- **Partial**: the application opens, but a documented function, resource, or
  persistence step is unavailable.
- **Fail**: the application will not open, crashes, or cannot complete the
  tested workflow.
- **Blocked**: the test requires a missing file, language pack, licence, or
  other dependency that has not yet been supplied.

## Test sequence

Keep the handset in Offline profile with Wi-Fi disconnected for this pass.

### 1. Clock and alarm

1. Open Clock and confirm the date, time, and Cardiff time zone are correct.
2. Create an alarm two minutes in the future.
3. Leave Clock and allow the alarm to fire.
4. Dismiss it, reopen Clock, and delete the test alarm.

Pass requires a visible/audible alert at the expected time and exact cleanup.

### 2. Calendar

1. Open Calendar and confirm that today is selected correctly.
2. Create an appointment named `KAI NATIVE TEST` five minutes in the future.
3. Save it, leave Calendar, and reopen the entry.
4. Delete only `KAI NATIVE TEST` and confirm it is gone.

### 3. Notes

1. Create a note containing `KAI NATIVE TEST 2026-08-23`.
2. Save it, leave Notes, reopen it, and append ` REOPENED`.
3. Save again, reopen once more, then delete the test note.

### 4. Calculator

Calculate `111040 + 1511`. The expected result is `112551`.

### 5. Dictionary

Look up `resurrection`. Record whether a definition appears or whether a
dictionary/language download is requested.

### 6. File manager

Open Files and record the drive names, reported capacities/free space, and
which roots are browseable. Do not rename, move, or delete anything.

### 7. ZIP

Open ZIP and record its initial screen, available commands, and any prompt. No
archive creation or extraction is required in this pass.

### 8. Adobe Reader

Open Adobe Reader and record whether it reaches its document browser, presents
a licence/activation prompt, or reports an error. A PDF rendering test follows
later with a controlled fixture.

### 9. Microsoft Apps

Open Microsoft Apps and record the visible component list, version/licence
prompt, and any error. Do not add an account or accept a network-dependent
setup during this pass.

### 10. User guide

Open User guide, search for `USB`, and open one matching help topic. This proves
the on-device documentation and search index are useful offline.

## Evidence and cleanup

A single readable video is sufficient. Do not open existing personal entries.
The alarm, calendar entry, and note must be removed before the test is marked
complete. No application installation, uninstall, reset, account creation,
network connection, or system-file mutation is authorised by this pass.
