# First read-only run

## Prepare the phone

1. Boot the E7 normally and unlock it.
2. Connect it directly to the Linux computer with a known data-capable USB
   cable; avoid a hub for this first capture.
3. If the phone asks for a USB mode, select **Mass storage**.
4. Do not format, repair, initialise, or accept any host prompt that proposes a
   change.

## Run on the Linux host

Save the script in a normal host directory such as `~/Downloads`, then run:

```bash
chmod +x e7-host-baseline.sh
./e7-host-baseline.sh
```

The script refuses to run from common removable-media mount paths. It writes
only into its current host directory and never invokes `sudo`.

## Result

The run creates:

- a timestamped report directory;
- a compressed `.tar.gz` bundle;
- a `.sha256` file for the bundle.

Share the bundle and checksum for interpretation. Do not commit the raw bundle
to this public repository.

