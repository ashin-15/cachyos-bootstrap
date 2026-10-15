"""Review captured payload integrity and recognized credential signatures."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from common import PRIVATE, REPO, assert_no_secret, contained, digest, read_json


def audit(settings: Path) -> dict:
    deployment = read_json(settings / "deployment.json")
    files = [entry for entry in deployment["entries"] if entry["kind"] == "file"]
    for entry in files:
        source = contained(settings, entry["source"])
        if digest(source) != entry["sha256"]:
            raise RuntimeError(f"Captured payload hash differs: {entry['source']}")
        assert_no_secret(source)
    if deployment.get("dconf"):
        source = contained(settings, deployment["dconf"]["source"])
        if digest(source) != deployment["dconf"]["sha256"]:
            raise RuntimeError("Captured dconf hash differs")
        assert_no_secret(source)
    skipped = {".git", ".state", ".ruff_cache", "__pycache__", ".lavish"}
    public_count = 0
    for directory, folders, names in os.walk(REPO):
        folders[:] = [name for name in folders if name not in skipped]
        for name in names:
            path = Path(directory) / name
            if path.is_file():
                assert_no_secret(path)
                public_count += 1
    required_unresolved = [
        note for note in deployment["notes"] if note["status"] == "unresolved"
    ]
    if required_unresolved:
        raise RuntimeError(
            "Required capture sources remain unresolved; review private manifest"
        )
    packages = read_json(REPO / "manifests/packages.json")["packages"]
    services = read_json(REPO / "manifests/services.json")
    aur = read_json(REPO / "manifests/aur-sources.json")
    return {
        "schema_version": 1,
        "captured_at": deployment["captured_at"],
        "public_files_reviewed": public_count,
        "deployment_entries": len(deployment["entries"]),
        "payload_files_hash_matched": len(files),
        "payload_bytes": sum(entry["bytes"] for entry in files),
        "recognized_credential_signatures": 0,
        "required_unresolved_sources": len(required_unresolved),
        "preexisting_broken_sources_excluded": sum(
            note["status"].startswith("excluded-broken") for note in deployment["notes"]
        ),
        "credential_configurations_redacted": sum(
            note["status"] == "reauthenticate" for note in deployment["notes"]
        ),
        "package_inventory_entries": len(packages),
        "package_install_intents": sum(
            bool(p["explicit"] or p.get("runtime_required")) for p in packages
        ),
        "aur_recipe_sources_identified": len(aur["sources"]),
        "aur_sources_unresolved": aur["unresolved"],
        "system_enabled_units": len(services["system"]),
        "user_enabled_units": len(services["user"]),
        "large_payloads_using_lfs": sum(
            entry["bytes"] >= 25 * 1024 * 1024 for entry in files
        ),
        "limits": [
            "Pattern checks do not prove absence of every possible secret.",
            "No installation, VM, test suite, reboot, greeter login, or desktop acceptance run.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--settings", type=Path, default=PRIVATE)
    args = parser.parse_args()
    print(json.dumps(audit(args.settings.expanduser().resolve()), indent=2))


if __name__ == "__main__":
    main()
