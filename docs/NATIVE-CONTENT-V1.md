# Native content probe v1

Prepared: 2026-08-23

## Purpose

Test the E7's genuine local file-handling paths without an account, SIM card,
cellular service, or historical server. The deployment creates one new folder,
`Mass memory:/KAI-NATIVE-V1`, containing three hash-allowlisted fixtures.

| File | Native surface under test | Pass condition |
| --- | --- | --- |
| `KAI-README.TXT` | Files and plain-text association | The complete text opens and is legible. |
| `KAI-ADOBE-PROBE.PDF` | Adobe Reader | The single page renders with its title, table, glyph rows, and footer intact. |
| `KAI-ZIP-PROBE.ZIP` | ZIP manager | The archive opens and lists `KAI-ZIP-CONTENTS.TXT`; optional extraction produces readable text. |

The PDF is deliberately conservative: PDF 1.3, one A4 page, built-in Helvetica,
no encryption, forms, JavaScript, transparency, embedded fonts, or images. The
ZIP contains one ASCII-named text member compressed with legacy Deflate.

## Host deployment

Put the E7 in Nokia Suite USB mode, close any graphical file manager using the
phone, and run:

```bash
./scripts/e7-deploy-native-content-v1.sh
```

The script:

1. verifies the exact three local fixtures by byte count and SHA-256;
2. proves that exactly one Nokia E7-00 is the host's sole MTP candidate;
3. selects the read/write `Mass memory` MTP store;
4. refuses to proceed if `KAI-NATIVE-V1` already exists;
5. creates only that folder and uploads only the three allowlisted files;
6. retrieves every created object by its returned MTP object ID;
7. compares every retrieved file byte-for-byte with its host original; and
8. leaves the verified folder on the phone for native UI testing.

It never overwrites or deletes an existing phone object. If a partial transfer
creates residue, it records the returned object IDs and deliberately leaves the
folder in place for inspection rather than guessing at cleanup.

## On-device sequence

Keep Wi-Fi disconnected so any unexpected service dependency is obvious.

1. In Files, browse `Mass memory:/KAI-NATIVE-V1` and open `KAI-README.TXT`.
2. Open `KAI-ADOBE-PROBE.PDF`. Record launch result, page rendering, zooming,
   and whether any licence, activation, or network prompt appears.
3. Open `KAI-ZIP-PROBE.ZIP`. Record the member list. If extraction is offered,
   extract its one text member into the same folder and open the extracted copy.
4. Do not choose `Updates & upgrades`, add an account, or accept a network
   setup prompt during this test.

A readable video is sufficient evidence. The persistent test folder remains a
small, reversible diagnostic fixture and may be removed in a later, separately
bounded cleanup pass.

## Device result

Completed: 2026-08-23

The user reports that all three fixtures work correctly on the handset. This
promotes the following native paths from launch-only evidence to useful local
content handling:

- Files can browse the deployed folder and open its plain-text fixture;
- Adobe Reader can open and render the conservative local PDF; and
- ZIP manager can open the local Deflate archive and expose its text content.

The returned toolkit ZIP is byte-identical to the issued package, with SHA-256
`f7a143c32e99b8b7bd2620f24238387c51be86e7cea35addda2ae38a1c1a29c3`,
and its embedded ZIP integrity test passes. The generated MTP deployment report
bundle was not supplied, so the device-side result is recorded as a direct user
observation rather than a captured host log.
