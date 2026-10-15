# CachyOS environment reproduction

Status: Frozen
Approval: Approved by user on 2026-10-16; GRUB appearance excluded.
Updated: 2026-10-15

## Goal

Recreate the user's installed tools and environment from GitHub through one bootstrap entry point on a fresh CachyOS installation with an existing user. Personal files and project contents are backed up separately. This is an environment reconstruction workflow, not a disk image.

## Confirmed decisions

- GitHub stores the reproducible environment and scripts.
- Fresh CachyOS and an existing user are prerequisites.
- Use a public bootstrap repository plus a private settings repository.
- Install current available package versions; exact historical versions are not required.
- Require username `ashin` and home directory `/home/ashin`.
- Restic is not part of this workflow.
- Ask consequential questions as inspection proceeds.
- The private repository contains personal application, editor, and AI settings. Credentials and private keys are excluded; authentication is performed again on the new installation.
- Restore and enable camp-fi and no-mistakes when their dependencies are available. Other custom user services retain their captured enabled/disabled intent.
- Fetch Android SDK components during bootstrap. Do not download AI model weights.
- Include the current SDDM login theme and its assets, independently of user-session desktop themes.

## Requirements

| ID | Requirement |
| --- | --- |
| FR-001 | Provide one bootstrap entry point covering packages, user configuration, development tools, desktop setup, and selected services. |
| FR-002 | Capture native and foreign packages, installation reasons, and tools installed outside pacman. |
| FR-003 | Capture actual current configuration and its dependencies rather than relying on previous dotfile copies. |
| FR-004 | Assign each installed tool and selected setting a restoration method or an explicit unresolved status. |
| FR-005 | Support a preview, preserve existing destination files, and permit safe retries after failure. |
| FR-006 | Keep credentials, private keys, browser sessions, application histories, and personal data outside public Git history. Credentials, private keys, browser sessions, and histories are excluded from both repositories. |
| FR-007 | Provide a capture/update workflow so future environment changes can be recorded. |
| FR-008 | Report restored, skipped, failed, and manual steps without declaring incomplete restoration successful. |

## Repository layout and user flow

- Public repository: `ashin-15/cachyos-bootstrap`; local checkout: `/home/ashin/Projects/cachyos-bootstrap`.
- Private repository: `ashin-15/cachyos-settings`; separate local checkout: `/home/ashin/Projects/cachyos-settings`.
- Existing `hypr-dots` remains an independent repository. Capture from the live environment, not its stale snapshot.
- On fresh CachyOS, user `ashin` obtains the public repository and invokes `./bootstrap.sh`. If git is missing, the README provides the prerequisite command or archive-download alternative.
- The script checks prerequisites, authenticates for the private overlay when needed, installs packages/tools, fetches Android SDK components, deploys selected settings, enables approved services, and prints a result report.
- After future environment changes, an explicit capture command prepares reviewable changes in the two local repositories. It does not automatically commit or publish files.

## Additional requirements

| ID | Requirement |
| --- | --- |
| FR-009 | Fetch Android command-line tooling, platform tools, current stable build tools, NDK, and CMake; include currently used API targets 35 and 36 as well as the current stable platform. Record actual resolved component IDs and support project-specific component additions. |
| FR-010 | Recreate and enable camp-fi and no-mistakes only after their executables, source checkouts, configuration, and service files are restored. Report missing sign-ins or other required inputs. |
| FR-011 | Public and private repositories remain independently reviewable, with no private settings embedded in public configuration or logs. |
| FR-012 | Back up and restore the active SDDM star-rail theme, its exact QML/configuration/video assets, selecting configuration, and runtime dependencies. Enable SDDM as the target display manager without restarting the current working session. |

## System customization coverage

FR-013: Bootstrap the current environment's persistent customizations, including manually installed files outside the home directory, alongside installed packages. The user explicitly requested that SDDM-like customizations be covered without requiring them to name each one.

Coverage includes:

- Login manager theme, QML/video assets, configuration, and dependencies (FR-012).
- Plymouth splash selection and required integration with the target's existing boot setup. GRUB appearance is explicitly excluded.
- Hyprland and Noctalia settings, GUI overrides, plugins, palettes, widgets, keybindings, and wallpaper assets.
- GTK, Qt, Kvantum, terminal and editor themes, icon and cursor selections, manually installed fonts, and font configuration.
- Custom application launchers, MIME defaults, shell/PATH configuration, and local executable installer sources.
- Enabled system/user services, sockets, paths, and timers; overrides and non-secret runtime settings.
- Relevant system environment, locale, audio, suspend/power, device-rule, and hardware-workaround configuration.
- User shell and supplementary group intent, recreated through supported commands instead of replacing account databases.

A coverage ledger must assign every discovered customization to package installation, exact asset deployment, a configuration merge/command, a conditional hardware profile, or an explicit exclusion/unresolved item with rationale. No discovered required item may silently disappear from bootstrap scope. Required unresolved items block a claim of complete recovery.

Generic system services previously left as unspecified selections are now in scope for explicit coverage. For enabled units, restore intended enablement after dependencies and compatibility checks. Credentials-dependent services must report pending sign-in; this does not authorize storing credentials. Do not override disabled intent for other custom units.

The existing scope exclusions for credentials, personal project/data contents, database/container state, model weights, OS installation, and disk identity remain in force. Hardware settings must use checked conditions and must not silently migrate device identities or disk-specific boot arguments.

## Decisions and assumptions

The user approved implementation on 2026-10-16 and explicitly excluded GRUB appearance. Repository names are proposed reversible defaults within the user's authorization to create public and private repositories.

Target is CachyOS x86-64. Keep the captured display arrangement as a named machine profile, and preserve fresh-install hardware, partitions, bootloader, and network identity settings. The script must report an incompatible display profile rather than overwrite unrelated machine identity data.

## Success and completion

The intended outcome is one execution restoring the approved environment. A complete package/tool coverage report must distinguish automatically restored tools from unresolved required items. Unknown installers or unavailable required packages block a claim of complete reproduction. A fresh-install run and interactive desktop review are required to establish actual recovery, beyond implementation checks.

## Scope limits

OS installation, partitioning, personal project contents, browser sessions, databases, containers' persistent data, and model weights are not implicitly covered by package installation. Any additional scope requires an explicit decision. Network access, sudo, and authentication may be required during one script execution; one command does not mean zero prompts or zero reboots.

## Approval amendment - 2026-10-16

User: "Grub appearance need not be included. Now I give you approval to start the implementation". Exclude GRUB theme assets, selection, configuration regeneration, and bootloader appearance operations. Plymouth remains in scope.

## User amendment - exclude Devin

The user requested "No need of devin" during implementation. Exclude Devin desktop, CLI, configuration, and launchers from capture and restoration. This is an approved scope reduction.
