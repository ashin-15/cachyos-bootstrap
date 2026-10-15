# Implementation evidence and remaining acceptance

Updated: 2026-10-16. Implementation approved; Devin and GRUB appearance excluded.

## Implemented

- Public bootstrap, capture, privacy/integrity audit, and rollback entry points.
- User-authorized four-day local capture schedule, with persistent hourly eligibility
  checks, login catch-up, success timestamps, failure retry, and bootstrap integration.
- Private checksummed deployment manifest: 805 entries, 790 payload files, 508,630,190 bytes, plus dconf. Four large executables use Git LFS.
- 1,533 diagnostic package records; 304 explicit/runtime installation intents, with current dependencies resolved from package metadata. Nineteen requested AUR sources were identified through the official API; none unresolved.
- Forty enabled system/user units recorded, including custom dependencies and retained disabled Hermes gateway intent.
- Packages/tools, Android CLI/SDK resolution, source-tool environments, Hermes desktop build, editor extensions/plugins, SDDM theme, Plymouth integration, manual fonts and personal preferences.
- Twenty-five pre-existing broken sources were excluded with reasons; two credential configurations were redacted. A password-only OpenCode file is excluded entirely.

## Observed evidence

- Capture executed successfully. Every captured payload hash matched the manifest during the audit.
- Recognized credential-signature scan found zero matches in reviewed public files and private payloads. This is not proof of absence of every possible secret.
- Ruff lint/format and Bash syntax checks passed. The non-mutating plan was displayed successfully.
- The capture timer is installed and observed as enabled and active in the current
  user session. Initial eligibility is 2026-10-20 01:38 IST, with the full capture due
  at the following hourly check, around 02:00 IST. A four-day elapsed run has not yet
  been observed; no capture was forced to exercise the scheduler.
- AUR source and Google stable SDK catalog lookups succeeded. These prove metadata/source resolution, not successful installation.
- No package installation, upgrade, reboot, SDK installation, vendor installer, VM, or
  test suite was run against the working system. The user capture timer is the only
  service activation authorized by the scheduling follow-up.

## Acceptance matrix

| Criterion | Result | Evidence / remaining gate |
| --- | --- | --- |
| AC-001 | Blocked | Fresh CachyOS execution has not been performed. |
| AC-002 | Pass | Package/tool manifests, identified AUR recipes, checksummed local artifacts, installer/source recipes. Runtime compatibility remains part of AC-001/003. |
| AC-003 | Blocked | Configuration captured; interactive desktop review not performed. |
| AC-004 | Blocked | Plan observed; deployment/rerun/rollback scenarios require an isolated target. |
| AC-005 | Pass | Explicit public/private boundary and recognized-signature audit before publication. |
| AC-006 | Blocked | Error handling implemented; installation failure paths not exercised. |
| AC-007 | Pass | Capture repeatedly produced current manifests without committing or pushing; stale generated payload is archived locally. |
| AC-008 | Blocked | Stable SDK identifiers resolved; actual component installation not performed. |
| AC-009 | Blocked | Service recipes and enablement implemented; fresh-target service results unverified. |
| AC-010 | Blocked | Preflight source inspected; invalid-target cases not exercised. |
| AC-011 | Blocked | Locks/journal/retry implemented; concurrency/interruption cases not exercised. |
| AC-012 | Blocked | Credential filtering observed; private-overlay authentication failure scenario not exercised. |
| AC-013 | Blocked | SDDM assets captured; greeter rendering, video, session selection, and login unverified. |
| AC-014 | Blocked | Known observations classified; exhaustive environment coverage still requires fresh-target review. |
| AC-015 | Blocked | Assets/configuration captured; target boot/desktop behavior unverified. |

Overall: implementation delivered; complete recovery is not accepted yet.

The next acceptance action is an isolated fresh CachyOS run followed by boot, login, desktop, audio, networking, and custom-service review. Tests and VM provisioning have not been requested.

## Publication

- Public bootstrap: https://github.com/ashin-15/cachyos-bootstrap
- Private settings: https://github.com/ashin-15/cachyos-settings
- Both repositories are on main; visibility was checked after upload.
- Four Git LFS objects totaling 451 MB were uploaded successfully.
- Publication is complete. Fresh-target recovery remains unverified.
