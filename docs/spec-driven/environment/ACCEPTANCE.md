# Acceptance contract

Status: Frozen
Approval: Approved by user on 2026-10-16; GRUB appearance excluded.

| ID | Related requirements | Observable condition | Required evidence |
| --- | --- | --- | --- |
| AC-001 | FR-001, FR-008 | One bootstrap entry point completes the approved phases on a fresh CachyOS installation with an existing user. | Fresh-install execution log and final report. |
| AC-002 | FR-002, FR-004 | Every captured package/tool has an identified restoration source; unresolved required entries prevent full acceptance. | Coverage report compared with the captured inventory. |
| AC-003 | FR-003 | Approved shell, terminal, editor, and desktop configuration plus required assets are deployed to supported target paths. | Manifest/deployment comparison and interactive desktop review. |
| AC-004 | FR-005 | Preview makes no installation or configuration changes; existing files are preserved before deployment; rerun does not duplicate configuration. | Isolated destination and rerun evidence. |
| AC-005 | FR-006 | Public staged contents follow the allowlist and exclude identified credentials and private state. | File review and secret-scanning report before publication. |
| AC-006 | FR-008 | A failed required phase yields a nonzero result and identifies the failed step; optional skips are visible. | Failure-path evidence. |
| AC-007 | FR-007 | Capture records subsequent package/configuration changes without silently staging unrelated home files. | Before/after capture comparison. |
| AC-008 | FR-009 | Bootstrap fetches SDK tooling/components, includes API targets 35 and 36, resolves current stable build tools/NDK/CMake, and reports installed IDs; no model weights are downloaded. | SDK inventory and bootstrap execution log. |
| AC-009 | FR-010 | camp-fi and no-mistakes are restored with dependencies and enabled; required missing configuration is reported. | Dependency inventory, enabled-state evidence, and service results on the target. |
| AC-010 | FR-001, FR-005 | Wrong username, home, distribution, architecture, or root execution is rejected before installation/configuration mutation. | Preflight failure-path evidence. |
| AC-011 | FR-005, FR-008 | Concurrent writers are rejected; interrupted installation can be retried and deployment journal identifies preserved destination versions. | Isolated failure/retry/concurrency evidence. |
| AC-012 | FR-006, FR-011 | Private-overlay authentication failure is explicit; credentials and private state do not enter either repository, public history, or logs. | Allowlist review, secret scan, and isolated authentication-failure evidence. |

| AC-013 | FR-012 | Exact SDDM theme assets and selecting/input configuration are captured with checksums, restored to the correct system paths with required runtime packages, and SDDM is enabled on the target. | Capture manifest and file integrity; fresh-target greeter rendering, video playback, session selection, and login evidence. |

| AC-014 | FR-013 | Every discovered persistent customization has a coverage record with restore operation, dependencies, destination, and conditional or exclusion rationale. Required unresolved records block full acceptance. | Cross-reference modified package metadata, unowned asset inventory, settings dependencies, enabled-unit inventory, and coverage ledger. |
| AC-015 | FR-003, FR-012, FR-013 | Selected login, desktop, toolkit, font, icon/cursor, splash customizations are restored with referenced assets; device-specific settings are conditional and target disk/account identity is preserved. | Exact-asset comparison, merged-configuration review, and fresh-target session/greeter/boot observations. |

All criteria are release blockers for claiming complete system reproduction. Implementation delivery may be reported with explicit unverified fresh-install gates; it must not be described as accepted recovery.

## Preconditions and boundaries

Fresh CachyOS x86-64, user `ashin`, home `/home/ashin`, network access, sudo availability, and private-repository authentication. Installation may ask for sudo, authentication, AUR recipe review, and Android licenses. A logout/reboot may be needed to use restored session settings.

Package availability and third-party installers can change. A missing required source is an installation failure, not an acceptable silent skip. Personal projects/data, credentials, browser sessions, model weights, OS installation, and disk layout restoration are out of scope. Selected local-project checkouts needed by tools/services are dependencies, not a general project backup.

No restore validation has been performed. Source inspection, syntax checks, and configuration-only preview cannot establish fresh-install or desktop acceptance. Tests and isolated VM provisioning will not run without user authorization. Required evidence remains unverified until obtained.

GRUB appearance is excluded by the user's implementation approval on 2026-10-16. AC-014/015 do not require it.

## User amendment - exclude Devin

The user requested "No need of devin" during implementation. Exclude Devin desktop, CLI, configuration, and launchers from capture and restoration. This is an approved scope reduction.
