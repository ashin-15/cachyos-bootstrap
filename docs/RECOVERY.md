# Restore behavior and recovery

## Target and prerequisites

The wrapper rejects root execution, another username/home, another distribution, and
another architecture before installation. The target needs CachyOS x86-64 and a user
`ashin` at `/home/ashin`. The script can fetch its own public repository when downloaded
alone. The private overlay requires access to `ashin-15/cachyos-settings`.

## Packages and versions

`manifests/packages.json` retains all observed package names, versions, and installation
reasons. Bootstrap installs the explicit choices and declared runtime requirements,
letting current package metadata select current dependencies. It does not force old ABI
packages such as an obsolete Electron version merely because they appear in the historical
inventory. Missing required packages or failed AUR builds stop the script.

The configured official OpenAI repository uses the captured public signing certificate,
whose fingerprint is recorded in `manifests/repositories.json`. Signature checking is not
disabled. A future key rotation requires reviewing and updating that certificate/manifest.
Current CachyOS repository/mirror configuration belongs to the target installation.

## Authentication and private settings

Both repositories exclude credentials. Sign into GitHub to obtain the overlay and
authenticate applications again after restoration. Redacted configuration fields are empty;
the report lists their source settings for review. Empty credentials can leave applications
or services waiting for input, even when their installation completed.

Configuration files can contain secrets in unexpected forms. Automatic redaction and
recognized credential-signature checks supplement an explicit allowlist and human review.
Never add entire browser, keyring, `.env`, or application-history directories to the policy.

## Existing files, retry, and rollback

Each run stores `report.json`, `journal.json`, and preserved preexisting configuration under:

```text
~/.local/state/cachyos-bootstrap/runs/<UTC timestamp>/
```

Each phase rechecks installed/deployed state on rerun. Existing local edits in a source-tool
checkout stop automatic updating. Interrupted or failed required operations return a nonzero
result; inspect the failed phase and fix its cause, then rerun the same entry point.

To undo deployed files from one run:

```bash
./bootstrap.sh --rollback /home/ashin/.local/state/cachyos-bootstrap/runs/<timestamp>
```

Rollback restores preserved file versions and removes newly deployed files only when their
current contents still match that run's output. It refuses to overwrite subsequent edits.
Package upgrades/installations, user groups/shell, imported dconf, generated initramfs images,
and service enablement are not transactionally reversed by file rollback. The prior dconf
export is retained as `dconf-before.ini` for deliberate restoration with `dconf load /`.

## Display manager and boot

The installer deploys the current SDDM theme/configuration with system ownership and enables
SDDM. It refuses to replace a competing enabled display manager. It never restarts the greeter
or networking during the run. Log out/reboot after reviewing the final report.

Plymouth integration merges only its hook with the target mkinitcpio hook list and rebuilds
the target initramfs. A different boot stack is reported as an incompatibility. GRUB appearance
and generated GRUB configuration are excluded. No bootloader firmware entries are installed.

## Services and data

The enabled-unit inventory is explicit in `manifests/services.json`. It includes Docker,
MariaDB, networking/resolver/time components, Bluetooth, Avahi, SDDM, UFW, Proton VPN,
power-management components, scheduled maintenance, audio/keyring sockets, and custom services.
Intel-specific service enablement is conditional on the CPU vendor. Unit-template instances
belong to the target's existing setup.

The bootstrap also deploys and enables `cachyos-capture.timer`, an hourly persistent
eligibility check for local captures separated by at least 96 hours. Its state is kept
under `~/.local/state/cachyos-bootstrap/capture.json`, outside both Git repositories.
Reboots preserve this timestamp; overdue work runs after the next login. It does not
automatically commit or push. Check `journalctl --user -u cachyos-capture.service` for
failures. Resolve the reported problem; the next hourly check retries without moving
the successful-capture timestamp. Lock contention with manual capture or bootstrap
also retries later. Restore/rerun preserves an existing schedule timestamp.

MariaDB is initialized only when its system tables are absent and its data directory is empty.
Existing database data is preserved. Rebuilding the environment does not recover its prior
database contents, container volumes, VPN credentials, or project files.

camp-fi is cloned into `~/Projects/wifi-auther` and its environment recreated. Hermes is
installed from source and its desktop built for the captured launchers. Other local custom
executables lacking a maintained installer are retained as checksummed private artifacts.
Some may need rebuilding if future libraries change; a fresh-install run is needed to prove
their runtime compatibility. LM Studio's CLI setup fetches its CLI without model weights.
