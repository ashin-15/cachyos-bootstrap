# CachyOS bootstrap

Personal environment reconstruction for **CachyOS x86-64**, user **ashin**, home **/home/ashin**.

The public repository contains the installer and package/tool manifests. The private
[`ashin-15/cachyos-settings`](https://github.com/ashin-15/cachyos-settings) repository
contains the reviewed personal configuration, theme assets, and custom executable
artifacts. Credentials are excluded. This is not a backup of project contents or disk data.

## Restore

Start from a fresh CachyOS installation with user `ashin`, internet access, and sudo.
Download the entry script and execute it:

```bash
curl --fail --location https://raw.githubusercontent.com/ashin-15/cachyos-bootstrap/main/bootstrap.sh -o "$HOME/bootstrap-cachyos.sh"
bash "$HOME/bootstrap-cachyos.sh"
```

The standalone script obtains the public checkout automatically. Alternatively, clone
the repository and run `./bootstrap.sh`. Run it as your user, without `sudo` in front.
It requests sudo for system operations and prompts for GitHub login, AUR recipe review,
vendor installers, and Android licenses. `--accept-vendor-installers` skips only the
individual vendor script review prompts; other authentication/license prompts remain.

To inspect the local plan without downloads, installation, or configuration changes:

```bash
./bootstrap.sh --plan
```

## Included

- Current versions of your explicit pacman/AUR packages and the dependencies required
  by current package metadata. The complete historical inventory is diagnostic.
- npm, Bun, uv, Cargo, Rust/Python toolchains, CLI installers, and source-backed tools.
- Android tooling, API targets 35/36, the current stable platform, and current stable
  build tools, NDK, and CMake. AI model weights are never downloaded.
- Hyprland Lua configuration; Noctalia TOML configuration, effective GUI overrides,
  plugins and palettes; wallpaper assets; terminal/editor/toolkit preferences.
- SDDM `star-rail`, including QML and its video background; required Qt packages.
- Plymouth splash selection and integration with the target's mkinitcpio setup.
- Manually installed fonts, icons, launchers, MIME settings, dconf, and user groups/shell.
- Captured enabled system/user services, sockets, paths and timers. camp-fi and
  no-mistakes are started after dependencies are installed; other enabled system units
  take effect on reboot. The Hermes gateway remains disabled.
- Device-specific workarounds are conditional on the captured hardware profile.

**Excluded:** Devin, GRUB appearance, OS installation/partitioning, machine/disk identity,
SSH/GPG keys, account tokens, browser profiles, application histories, model weights,
project contents, database contents, and container persistent data.

## Capture future changes

```bash
./capture.sh
```

This refreshes public inventories and the local private overlay. It never commits or
pushes. Review both repositories and `deployment.json` notes before publishing changes.
Only explicit allowlisted paths are collected. Existing broken sources are reported
separately from missing required working sources.

Large local executable artifacts use Git LFS. Keep LFS enabled in the private checkout.
The installer verifies every private file against its deployment checksum before applying it.

## Recovery and limits

See [RECOVERY.md](docs/RECOVERY.md) for configuration backups, rollback, credentials,
package changes, and troubleshooting, and [STATUS.md](docs/STATUS.md) for actual evidence.

No fresh-install recovery, greeter login, boot, or interactive desktop acceptance has
been established yet. A successful plan or source/lint check does not establish those outcomes.
