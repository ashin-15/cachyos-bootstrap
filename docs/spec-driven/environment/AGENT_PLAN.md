# Implementation ownership

Status: Frozen
Approval: User approved on 2026-10-16, excluding GRUB appearance.
Owner: Main agent, sequential execution.

## Shared contracts

JSON schema version 1 for manifests. Paths are relative to home or system roots. Public manifests contain no private values. Private files are listed by explicit deployment map; no private shell hooks.

## Tasks

1. Engine and manifest contracts: `bootstrap.sh`, `scripts/`, `manifests/`. FR-001 through FR-011, FR-013; AC-001 through AC-012, AC-014.
2. Capture current approved environment: public safe inventory/configuration and private reviewed settings/assets/tool artifacts. Public checkout and private checkout only. FR-002/003/006/007/011/012/013; AC-002/003/005/007/012/013/014/015.
3. Installation and target deployment: package/tool/SDK recipes, safe file deployment, service enablement, SDDM and Plymouth. Same owned repository paths. All approved FRs/ACs.
4. Documentation, source inspection, package coverage and publication: repository README, docs, manifests and Git metadata. Record unverified fresh-install acceptance; do not run installation on the working host.

Forbidden writes: live `/etc`, `/usr`, `/boot`, active user configuration, existing `hypr-dots`, and private authentication files. No tests or VM provisioning without user request. Stop for scope changes, unidentified required secret handling, or unsafe publication.
