# Bootstrap technical design

Status: Frozen
Approval: Approved by user on 2026-10-16; GRUB appearance excluded.

## Observed system

- CachyOS, x86-64, ext4 root and EFI boot partition.
- Initial inventory: 1,535 pacman packages, 290 explicit packages, 22 foreign packages. Refresh at capture time.
- Hyprland uses `~/.config/hypr/hyprland.lua` and required modules under `config/`.
- Current desktop starts `/usr/bin/noctalia`, owned by package `noctalia` version 5.2.1-1.1. Legacy `noctalia-shell` is also installed; its version is not the running desktop's version.
- Noctalia uses `~/.config/noctalia/config.toml`; effective GUI overrides are confirmed in `~/.local/state/noctalia/settings.toml`. Capture that settings file and required palette/plugin assets; exclude clipboard, recent usage, and notification history.
- Additional installers include npm globals, Bun globals, uv tools, rustup/Cargo, and custom executables under `~/.local/bin`.
- Existing clean repository: `/home/ashin/Repos/hypr-dots`, remote `git@github.com:ashin-15/hypr-dots.git`. Its tracked configuration includes older Noctalia JSON settings, so it is not a complete current snapshot.
- Custom user services include camp-fi, Hermes gateway, and no-mistakes. Service definitions contain hardcoded home paths.
- Enabled system services include databases, networking, Docker, VPN, display manager, and power management. Do not replay every enabled service on another installation without reviewing applicability.
- GitHub CLI authentication works outside the network sandbox.

## Proposed architecture

Use a small Bash entry point with explicitly ordered phases and structured inventories. Python may handle manifest validation and safe file deployment where shell parsing would be fragile. Installation manifests and selected configuration should be reviewable text files.

Proposed phases: preflight, repositories and prerequisites, pacman full upgrade and native packages, foreign-package installation as the user, language and vendor tools, configuration deployment, selected service enablement, and final report.

Do not run the entire bootstrap as root. Request sudo only for system operations. Never perform an Arch partial upgrade. Preserve existing CachyOS repository and hardware configuration unless an approved change is needed.

Record all installed pacman packages with versions and installation reasons. Use explicit packages plus discovered runtime dependencies as installation intent; retain the full list for comparison. Foreign packages require individual source resolution because absence from current repositories does not prove AUR provenance.

## Configuration deployment

Use explicit allowlists. Do not copy all of `.config`, `.local`, or `.agents` into Git. Review files and their dependencies before staging; automatic secret scanning supplements that review and cannot prove absence of sensitive content.

Preserve symlink semantics and capture required targets. Preflight must require username `ashin` and home `/home/ashin`; reject other users before making changes. Existing absolute references may be retained under that explicit target contract. Resolve `.local/bin` symlinks to installer recipes or consciously retained artifacts.

Capture desktop appearance dependencies such as fonts, palettes, wallpapers, icons, terminal themes, Neovim lockfiles, launchers, MIME defaults, and selected state overrides. Personal values need a separate classification from reusable configuration.

Keep a deployment journal with backups of preexisting files, phase results, and errors. Reruns must inspect actual state; a previous completion marker alone must not skip missing outputs. Stop or clearly report required installation failures.

## Inspection findings requiring treatment

- The current `.zshrc` contains a shell-startup deletion of `~/Waterfox`. Do not carry this destructive behavior into the bootstrap template.
- Its Android PATH loop groups multiple paths into one directory-existence check. Normalize the captured template so valid paths are added individually.
- The `update` alias recursively copies all `.agents` into the old repository. Replace it with the proposed allowlisted capture workflow after approval.
- `uv tool list` reports a malformed pyrefly installation. Inventory it as unresolved; do not silently reproduce a broken environment or uninstall it during inspection.
- Some local tool links point to versioned release directories or development artifacts and need explicit restoration sources.

## Confirmed repository and version policy

The public `cachyos-bootstrap` repository will contain scripts, package/tool manifests, reviewed reusable configuration, and documentation. The private `cachyos-settings` overlay will contain reviewed personal settings under an explicit allowlist. Initial private-repository authentication may require an interactive login during bootstrap. Never embed a GitHub token in the public script. Current package releases are desired; historical versions in the inventory are diagnostic only.

## Module and manifest contracts

- `bootstrap.sh`: orchestrates phases; Bash strict error handling; requires non-root `ashin`, `/home/ashin`, CachyOS, and x86-64 before mutation.
- `manifests/`: schema-versioned package/tool/component/service inventory and explicit configuration allowlists. Save full installed package versions and install reasons as diagnostic evidence; install current releases.
- `scripts/`: capture, deployment, installer adapters, and reporting. No hidden per-machine executable commands in JSON manifests.
- `config/`: reviewed reusable configuration. Private overlay has a corresponding allowlisted tree and declarative deployment map, never arbitrary remotely supplied shell hooks.
- `docs/`: setup, credential/sign-in steps, recovery, coverage, and known limitations.

Configuration paths are relative to a fixed approved root and must reject absolute paths, traversal, duplicate conflicting destinations, and unexpected symlink escape. Private settings checkout uses restrictive local permissions; public and private captures must never recursively include each other.

## Private overlay and authentication

Use HTTPS GitHub CLI authentication or an independently configured SSH identity. Authenticate during the same invocation when the private overlay is unavailable. Do not store tokens or private keys in either repository. If the overlay cannot be obtained, required settings remain incomplete and the invocation must report failure instead of silently treating public-only installation as a complete restore.

Private contents include reviewed application/editor/AI settings, personal paths/preferences, user identity settings, and machine-specific display settings. Exclude auth files, keyrings, private keys, environment credential values, browser profiles, conversations, databases, and model files. For mixed configuration files, preserve non-secret settings and use explicit environment-variable placeholders or application-supported credential files; provide a manual sign-in checklist. Never print secret values in reports or logs.

## Android SDK and local-project tools

Fetch official Android tooling rather than archive the SDK into Git. Resolve stable platform/build-tool/NDK/CMake components against the current catalog. Include existing API targets 35 and 36 for compatibility; record resolved IDs in the installation report. Provide an explicit component manifest for future project-specific additions. Handle license acceptance interactively; report denial or installation failure. Configure `ANDROID_HOME` and individual executable PATH entries. The installed legacy sdkmanager reported an SDK XML version mismatch; a fresh bootstrap should obtain current tooling rather than copy that installation.

Observed SDK inventory: platform-tools; platforms android-35 and android-36; build-tools 35.0.0, 36.0.0, 36.1.0; ndk 29.0.14206865; cmake 3.31.6. These historical versions are evidence rather than a version lock.

camp-fi source is `git@github.com:ashin-15/camp-fi.git`, currently checked out at `/home/ashin/Projects/wifi-auther`. Restore that dependency at the service's expected location and recreate its Python environment. Other source-backed tools need equivalent explicit recipes. No local project contents are silently copied into the settings repository. Unpublished required executables need an identified source or an explicitly documented retained artifact; an unexplained symlink is not a restoration method.

## Services and system configuration

Restore camp-fi and no-mistakes with their dependencies and captured enabled intent. Restore other custom user unit enabled/disabled intent, including leaving the observed disabled Hermes gateway disabled. Enable selected system services after validating package availability and conflicts. Do not blindly replay mutually competing network, power, or display-manager services. Capture relevant reviewed `/etc` overrides separately from generated machine files; never replace fstab, crypttab, machine-id, host keys, disk identifiers, boot entries, or hardware-specific network profiles from this machine.

## Execution, rollback, and resource costs

Permit only one active bootstrap/capture writer per checkout or deployment state using a lock. Do not install all package families concurrently; serialize package databases and bound vendor downloads. Keep capture limited to explicit paths rather than scanning hundreds of GB of projects or caches.

Each phase records start/end, resolved versions, changes, and failures. Stop required dependent phases after a failure and return nonzero. Rerun rechecks installed state. Back up existing configuration with modes and symlink metadata before replacing it and retain a journal for restoration. Configuration rollback is scoped to those files; package installs/full upgrades are not promised to be transactionally reversible.

Downloads use HTTPS and verify published checksums/signatures when available. AUR recipes execute as the unprivileged user after visible recipe review. Vendor installers must have recorded provenance and explicit behavior rather than unreviewed curl-to-shell pipelines.

## Validation boundaries

No installation, upgrade, or service activation will be performed against the current working system as a bootstrap test. Implementation inspection can establish manifest coverage, source provenance, and configuration review. Actual recovery acceptance requires isolated or fresh-install execution and desktop review. Tests or VM provisioning require user authorization under the current agent instructions; record unperformed criteria as unverified, never passed.

## Alternatives considered

A whole-disk image and restic were excluded by user preference. Exact-version archives were excluded by the selected current-package policy. A single repository was replaced by the selected public/private split.

## Implementation discovery tasks


Complete tool-by-tool installer provenance and the file-level configuration allowlists during implementation. Findings that would change scope, publish sensitive material, require retaining unapproved credentials, or remove required behavior must return for user decision. Discovery tasks do not permit weakening acceptance criteria.

## SDDM login theme

The active selected theme is `star-rail`, configured in `/etc/sddm.conf` and `/etc/sddm.conf.d/theme.conf`. `/etc/sddm.conf.d/virtualkbd.conf` is also part of the current selecting/input configuration. The theme lives at `/usr/share/sddm/themes/star-rail` and is not owned by a pacman package. Installing SDDM alone cannot restore it.

Capture the exact `Main.qml`, `metadata.desktop`, `theme.conf`, and `bg.mp4` files in the private settings repository. The video is about 12.5 MB. Theme imports require SDDM components, QtQuick/declarative, Qt5Compat graphical effects, and QtMultimedia; add explicit runtime dependencies independent of their current package installation reason. The QML references an optional `font` directory that is absent on this machine; record this rather than inventing a font asset.

Deploy the theme and reviewed selecting/input configuration with root-owned paths and appropriate readable permissions after preserving destination files. Preserve the effective semantics of the existing configuration despite its multiple configuration files. Enable SDDM on the target, reporting a competing enabled display manager rather than silently switching it. Never restart the active display manager on this working installation. Fresh-target validation must cover theme rendering, background playback, session selection, and login; file backup integrity alone does not establish those outcomes.

## Comprehensive customization discovery and coverage

FR-013 expands discovery beyond dotfiles. Use package backup metadata to identify modified tracked configuration, compare relevant asset/configuration locations with package ownership, inventory custom executables/symlink targets, and record enabled units and unit overrides. Package backup metadata covers designated backup files only; it does not establish absence of edits elsewhere. Referenced assets must be followed to their real source paths and classified.

Coverage records contain source path/unit/tool, category, package ownership or installer provenance, public/private destination, dependencies, restore operation, machine conditions, evidence, and unresolved rationale. An existing unowned file is neither automatically safe to publish nor automatically irrelevant. Capture approved private assets exactly with hashes and permissions; use current packages for upstream defaults and preserve local deltas. Never bulk-copy `/etc`, `/usr/share`, `/opt`, or application profile trees.

Current additional findings:
- Ten manually installed root-level fonts in `/usr/share/fonts` are unowned by pacman. Capture these as private assets and rebuild the font cache after deployment.
- GTK selects Tokyonight-Dark, breeze-dark icons, Oxygen_Zion cursors, and JetBrains Mono Nerd Font. Qt6 uses kvantum-dark and Kvantum selects MateriaDark. Capture referenced custom palettes/styles and install corresponding providers.
- GRUB appearance is excluded by the 2026-10-16 approval amendment. Do not capture or deploy it. Plymouth selects cachyos-bootanimation, supplied by cachyos-plymouth-bootanimation. Restore Plymouth package assets and its selection only. Do not modify GRUB appearance or import generated GRUB configuration.
- `/etc/mkinitcpio.conf` includes plymouth and resume hooks. Integrate needed appearance hooks with the target's boot stack and regenerate target artifacts through its tools; never overwrite target disk identity, reinstall bootloader firmware entries, or copy a prebuilt initramfs. A different boot stack needs a visible conditional result, not assumed compatibility.
- `/etc/environment.d/30-opencl.conf` sets RUSTICL_ENABLE=iris; `/etc/modprobe.d/sof-disable.conf` selects an Intel audio driver; `/etc/tmpfiles.d/micmute-led.conf` sets an LED trigger. Preserve them in a hardware profile with explicit device prerequisites.
- Ollama has an override setting OLLAMA_CONTEXT_LENGTH=65536. Capture the setting independently of AI model weights. Preserve the service's captured enablement intent.
- Package backup metadata currently reports 26 modified configuration files, including generated/account/disk files that require exclusion or semantic reconstruction. This count is not a complete customization inventory.

Enabled-unit inventory must include system services (Docker, MariaDB, NetworkManager, Bluetooth, SDDM, UFW, Proton VPN, Avahi, CPU/power services, and systemd networking/resolver/time components), their sockets, and timers (mirror refresh, trim, firmware refresh), plus user audio/keyring services and custom units. Resolve conflicts from actual configuration; preserve required behavior and report an unresolved conflict rather than silently dropping a unit or enabling competing defaults. Database contents, VPN credentials, and keyring contents remain excluded.

## Execution ownership

Implementation is performed serially by the main agent. No live-system installation/upgrade, boot regeneration, service activation, or fresh-install test is authorized as part of implementing repository contents. Capture and read-only review commands are permitted.

## User amendment - exclude Devin

The user requested "No need of devin" during implementation. Exclude Devin desktop, CLI, configuration, and launchers from capture and restoration. This is an approved scope reduction.
