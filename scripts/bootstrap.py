"""Recreate the captured CachyOS environment without modifying disk identity."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import android_sdk
import schedule
from common import (
    HOME,
    PRIVATE,
    REPO,
    assert_no_secret,
    contained,
    digest,
    ensure_user,
    lock,
    private_permissions,
    read_json,
    reject_symlink_parents,
    relative,
    run,
    target_path,
    write_json,
)


class Bootstrap:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.settings = args.settings.expanduser().resolve()
        self.state = HOME / ".local/state/cachyos-bootstrap"
        self.report: dict = {
            "schema_version": 1,
            "started_at": datetime.now(UTC).isoformat(),
            "phases": [],
            "conditional_skips": [],
            "pending_signins": [],
        }
        self.deployment: dict = {}
        self.backup = (
            self.state / "runs" / datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        )
        self.journal: list[dict] = []

    def phase(self, name: str, operation) -> None:
        print(f"\n[{name}]", flush=True)
        row = {"name": name, "status": "running"}
        self.report["phases"].append(row)
        write_json(self.backup / "report.json", self.report)
        try:
            operation()
        except Exception:
            row["status"] = "failed"
            self.report["status"] = "failed"
            write_json(self.backup / "report.json", self.report)
            raise
        row["status"] = "completed"
        write_json(self.backup / "report.json", self.report)

    def plan(self) -> None:
        packages = read_json(REPO / "manifests/packages.json")
        services = read_json(REPO / "manifests/services.json")
        deployment = self.settings / "deployment.json"
        result = {
            "action": "plan-only; no installations, network requests, locks, or deployment",
            "target": "CachyOS x86-64, ashin, /home/ashin",
            "packages_observed": len(packages["packages"]),
            "package_install_requests": sum(
                bool(p["explicit"] or p.get("runtime_required"))
                for p in packages["packages"]
            ),
            "version_policy": "latest",
            "excluded": ["Devin", "GRUB appearance", "credentials", "AI model weights"],
            "settings_repo": "ashin-15/cachyos-settings",
            "deployment_entries": len(read_json(deployment)["entries"])
            if deployment.exists()
            else "fetch during apply",
            "system_units": services["system"],
            "user_units": services["user"],
            "phases": [
                "prerequisites",
                "private-overlay",
                "repositories",
                "packages",
                "configuration",
                "language-tools",
                "source-tools",
                "vendor-tools",
                "android",
                "extensions",
                "editor-tools",
                "system-settings",
                "capture-schedule",
                "services",
            ],
            "prompts": [
                "sudo",
                "GitHub authentication",
                "AUR recipes",
                "vendor installer review",
                "Android licenses",
            ],
            "recovery_validation": "fresh-install, boot, greeter, and desktop unverified",
        }
        print(json.dumps(result, indent=2))

    def prerequisites(self) -> None:
        run(["sudo", "-v"])
        run(
            [
                "sudo",
                "pacman",
                "-Syu",
                "--needed",
                "git",
                "git-lfs",
                "github-cli",
                "python",
                "python-yaml",
                "base-devel",
                "curl",
            ]
        )

    def overlay(self) -> None:
        if not (self.settings / "deployment.json").exists():
            if self.settings.exists() and any(self.settings.iterdir()):
                raise RuntimeError(
                    "Private settings directory is nonempty but has no deployment.json"
                )
            self.settings.parent.mkdir(parents=True, exist_ok=True)
            if run(["gh", "auth", "status"], output=True, check=False).returncode:
                run(
                    [
                        "gh",
                        "auth",
                        "login",
                        "--hostname",
                        "github.com",
                        "--git-protocol",
                        "https",
                    ]
                )
            run(
                ["gh", "repo", "clone", "ashin-15/cachyos-settings", str(self.settings)]
            )
        self.settings.chmod(0o700)
        if run(["gh", "auth", "status"], output=True, check=False).returncode:
            run(
                [
                    "gh",
                    "auth",
                    "login",
                    "--hostname",
                    "github.com",
                    "--git-protocol",
                    "https",
                ]
            )
        run(["gh", "auth", "setup-git"])
        run(["git", "lfs", "install", "--local"], cwd=self.settings)
        run(["git", "lfs", "pull"], cwd=self.settings)
        self.deployment = read_json(self.settings / "deployment.json")
        if self.deployment.get("schema_version") != 1:
            raise ValueError("Unsupported private deployment schema")
        destinations = set()
        for entry in self.deployment["entries"]:
            target_path(entry["root"], entry["path"])
            identity = (entry["root"], entry["path"])
            if identity in destinations:
                raise ValueError("Duplicate deployment destination")
            destinations.add(identity)
            if entry["kind"] == "file":
                if (
                    not isinstance(entry["mode"], int)
                    or not 0 <= entry["mode"] <= 0o777
                ):
                    raise ValueError("Unsafe deployment file mode")
                source = contained(self.settings, entry["source"])
                if not source.is_file() or digest(source) != entry["sha256"]:
                    raise RuntimeError(
                        f"Missing or changed captured file: {entry['source']}"
                    )
                assert_no_secret(source)
        unresolved = [
            n for n in self.deployment["notes"] if n["status"] == "unresolved"
        ]
        if unresolved:
            raise RuntimeError(
                "Private capture has unresolved sources; review deployment.json notes"
            )

    def repositories(self) -> None:
        extra = read_json(REPO / "manifests/repositories.json")["extra"]
        configured = run(
            ["pacman-conf", "--repo-list"], output=True
        ).stdout.splitlines()
        missing_standard = [
            name for name in ["core", "extra", "multilib"] if name not in configured
        ]
        if missing_standard:
            text = Path("/etc/pacman.conf").read_text()
            for name in missing_standard:
                text += "\n[" + name + "]\nInclude = /etc/pacman.d/mirrorlist\n"
            self.deploy_bytes(text.encode(), "system", "etc/pacman.conf", 0o644)
        current = run(["pacman-conf", "--repo-list"], output=True).stdout.splitlines()
        for repo in extra:
            if repo["name"] in current:
                continue
            if repo["name"] != "openai-chatgpt" or not repo["server"].startswith(
                "https://persistent.oaistatic.com/"
            ):
                raise ValueError("Unsupported additional package repository")
            key_file = contained(REPO, repo["key_file"])
            inspected = run(
                ["gpg", "--batch", "--show-keys", "--with-colons", str(key_file)],
                output=True,
            ).stdout
            fingerprints = [
                line.split(":")[9]
                for line in inspected.splitlines()
                if line.startswith("fpr:")
            ]
            if not fingerprints or fingerprints[0] != repo["key_fingerprint"]:
                raise RuntimeError("Repository public-key fingerprint mismatch")
            run(["sudo", "pacman-key", "--add", str(key_file)])
            run(["sudo", "pacman-key", "--lsign-key", repo["key_fingerprint"]])
            content = Path("/etc/pacman.conf").read_text()
            content += "\n[openai-chatgpt]\nServer = " + repo["server"] + "\n"
            self.deploy_bytes(content.encode(), "system", "etc/pacman.conf", 0o644)

    def packages(self) -> None:
        manifest = read_json(REPO / "manifests/packages.json")
        # Dependencies follow current package metadata; do not force obsolete ABI names.
        desired = {
            p["name"]
            for p in manifest["packages"]
            if p["explicit"] or p.get("runtime_required")
        }
        run(["sudo", "pacman", "-Syu"])
        available = {
            line.split()[1]
            for line in run(["pacman", "-Sl"], output=True).stdout.splitlines()
            if len(line.split()) >= 3
        }
        native = sorted(desired & available)
        foreign = sorted(desired - available)
        run(["sudo", "pacman", "-S", "--needed", *native])
        if foreign:
            query = urllib.parse.urlencode(
                [("v", "5"), ("type", "info"), *[("arg[]", name) for name in foreign]]
            )
            request = urllib.request.Request(
                "https://aur.archlinux.org/rpc?" + query,
                headers={"User-Agent": "cachyos-bootstrap/1"},
            )
            with urllib.request.urlopen(request, timeout=60) as response:
                metadata = json.load(response)
            found = {row["Name"] for row in metadata.get("results", [])}
            unavailable = set(foreign) - found
            if unavailable:
                raise RuntimeError(
                    "Required packages have neither a configured repository nor an AUR recipe: "
                    + ", ".join(sorted(unavailable))
                )
            self.report["aur_package_bases"] = {
                row["Name"]: row["PackageBase"] for row in metadata["results"]
            }
            if not shutil.which("paru"):
                raise RuntimeError("paru is required for packages outside repositories")
            print("Review AUR recipes when paru prompts; building runs as ashin.")
            run(["paru", "-S", "--needed", *foreign])
        explicit = sorted(p["name"] for p in manifest["packages"] if p["explicit"])
        run(["sudo", "pacman", "-D", "--asexplicit", *explicit])
        self.report["resolved_packages"] = run(
            ["pacman", "-Q"], output=True
        ).stdout.splitlines()

    def hardware_matches(self) -> bool:
        for name, value in self.deployment["hardware"].items():
            path = Path("/sys/class/dmi/id") / name
            if value and (not path.exists() or path.read_text().strip() != value):
                return False
        return True

    def deploy_bytes(self, data: bytes, root: str, path: str, mode: int) -> None:
        with tempfile.TemporaryDirectory(prefix="cachyos-file-") as temp:
            source = Path(temp) / "file"
            source.write_bytes(data)
            self.deploy(
                {"root": root, "path": path, "kind": "file", "mode": mode}, source
            )

    def deploy(self, entry: dict, source: Path | None = None) -> None:
        dest = target_path(entry["root"], entry["path"])
        reject_symlink_parents(dest)
        if (
            entry["kind"] == "file"
            and dest.is_file()
            and not dest.is_symlink()
            and digest(dest) == digest(source)
            and dest.stat().st_mode & 0o777 == entry["mode"]
            and (entry["root"] != "system" or dest.stat().st_uid == 0)
        ):
            return
        if (
            entry["kind"] == "symlink"
            and dest.is_symlink()
            and str(dest.readlink()) == entry["link"]
        ):
            return
        if dest.is_dir() and not dest.is_symlink():
            raise RuntimeError(f"File destination is a directory: {dest}")
        privileged = entry["root"] == "system"
        prefix = ["sudo"] if privileged else []
        saved = (
            self.backup
            / "before"
            / str(len(self.journal))
            / entry["root"]
            / entry["path"]
        )
        exists = dest.exists() or dest.is_symlink()
        row = {
            "root": entry["root"],
            "path": entry["path"],
            "existed": exists,
            "saved": str(saved.relative_to(self.backup)),
            "state": "prepared",
            "kind": entry["kind"],
            "expected": digest(source) if source else entry["link"],
        }
        self.journal.append(row)
        write_json(self.backup / "journal.json", self.journal)
        if exists:
            saved.parent.mkdir(parents=True, exist_ok=True)
            run([*prefix, "cp", "-a", "--", str(dest), str(saved)])
        row["state"] = "backed-up"
        write_json(self.backup / "journal.json", self.journal)
        run([*prefix, "mkdir", "-p", "--", str(dest.parent)])
        if entry["kind"] == "file":
            args = [*prefix, "install", "-m", oct(entry["mode"])[2:]]
            if privileged:
                args += ["-o", "root", "-g", "root"]
            if dest.is_symlink():
                run([*prefix, "rm", "--", str(dest)])
            run([*args, "--", str(source), str(dest)])
        else:
            link = Path(entry["link"])
            resolved = (link if link.is_absolute() else dest.parent / link).resolve()
            if not (resolved.is_relative_to(HOME) or resolved.is_relative_to("/usr")):
                raise ValueError("Unapproved symlink target")
            run([*prefix, "ln", "-sfn", "--", entry["link"], str(dest)])
        row["state"] = "applied"
        write_json(self.backup / "journal.json", self.journal)

    def configuration(self) -> None:
        matching = self.hardware_matches()
        for entry in self.deployment["entries"]:
            if entry.get("hardware") and not matching:
                self.report["conditional_skips"].append(entry["path"])
                continue
            source = (
                contained(self.settings, entry["source"])
                if entry["kind"] == "file"
                else None
            )
            self.deploy(entry, source)
        run(["gh", "auth", "setup-git"])
        for row in self.journal:
            if row["root"] == "home" and row["path"] == ".gitconfig":
                row["expected"] = digest(HOME / ".gitconfig")
        write_json(self.backup / "journal.json", self.journal)
        self.report["pending_signins"] = [
            n["source"]
            for n in self.deployment["notes"]
            if n["status"] == "reauthenticate"
        ]

    def language_tools(self) -> None:
        tools = read_json(REPO / "manifests/tools.json")
        (HOME / ".local/bin").mkdir(parents=True, exist_ok=True)
        run(
            [
                "npm",
                "install",
                "--global",
                "--prefix",
                str(HOME / ".npm-global"),
                *[p + "@latest" for p in tools["npm"]],
            ]
        )
        run(["bun", "add", "--global", *[p + "@latest" for p in tools["bun"]]])
        run(["rustup", "toolchain", "install", "stable", "--profile", "default"])
        run(["rustup", "default", "stable"])
        if tools["rust_components"]:
            run(["rustup", "component", "add", *tools["rust_components"]])
        for package in tools["cargo"]:
            run(["cargo", "install", package])
        for package in tools["uv"]:
            run(["uv", "tool", "install", "--upgrade", package])
        run(["uv", "python", "install", *tools["python_versions"]])
        run(["npx", "--yes", "lmstudio@latest", "install-cli"])

    def source_tools(self) -> None:
        for repo in read_json(REPO / "manifests/tools.json")["source_repos"]:
            path = contained(HOME, repo["path"])
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                run(["git", "clone", repo["url"], str(path)])
            else:
                if not (path / ".git").exists():
                    raise RuntimeError(
                        f"Existing dependency is not a Git checkout: {path}"
                    )
                if run(["git", "status", "--porcelain"], cwd=path, output=True).stdout:
                    raise RuntimeError(
                        f"Local dependency edits preserved; update manually: {path}"
                    )
                run(["git", "pull", "--ff-only"], cwd=path)
            if repo["kind"] == "camp-fi":
                run(["uv", "sync"], cwd=path)
                run(["uv", "tool", "install", "--upgrade", str(path)])
            elif repo["kind"] == "hermes":
                run(["uv", "venv", str(path / ".hermes"), "--allow-existing"])
                run(
                    [
                        "uv",
                        "pip",
                        "install",
                        "--python",
                        str(path / ".hermes/bin/python"),
                        "-e",
                        str(path),
                    ]
                )
                run(["npm", "install"], cwd=path)
                run(["npm", "run", "build", "--workspace", "apps/desktop"], cwd=path)
                for name in ["hermes", "hermes-agent", "hermes-acp"]:
                    self.deploy_bytes(
                        f'#!/bin/sh\nexec "{path}/.hermes/bin/hermes" "$@"\n'.encode(),
                        "home",
                        ".local/bin/" + name,
                        0o755,
                    )

    def vendors(self) -> None:
        for vendor in read_json(REPO / "manifests/tools.json")["vendor_installers"]:
            with tempfile.TemporaryDirectory(prefix="cachyos-installer-") as temp:
                script = Path(temp) / "install.sh"
                run(
                    [
                        "curl",
                        "--fail",
                        "--location",
                        "--proto",
                        "=https",
                        "--tlsv1.2",
                        "--output",
                        str(script),
                        vendor["url"],
                    ]
                )
                print(
                    f"Installer {vendor['name']}: {vendor['url']}; SHA-256 {digest(script)}"
                )
                if not self.args.accept_vendor_installers:
                    run(["less", str(script)])
                    if (
                        input("Execute this installer as ashin? [y/N] ").strip().lower()
                        != "y"
                    ):
                        raise RuntimeError(
                            f"Required installer declined: {vendor['name']}"
                        )
                run([vendor["shell"], str(script), *vendor["args"]])

    def extensions(self) -> None:
        for editor, extensions in read_json(REPO / "manifests/extensions.json")[
            "editors"
        ].items():
            if extensions and not shutil.which(editor):
                raise RuntimeError(f"Editor CLI not available: {editor}")
            for extension in extensions:
                run([editor, "--install-extension", extension, "--force"])

    def android(self) -> None:
        try:
            self.report["android_components"] = android_sdk.install(
                read_json(REPO / "manifests/android.json")
            )
        finally:
            cli = HOME / ".local/bin/android"
            if cli.is_file():
                for row in self.journal:
                    if row["root"] == "home" and row["path"] == ".local/bin/android":
                        row["expected"] = digest(cli)
            write_json(self.backup / "journal.json", self.journal)

    def editor_tools(self) -> None:
        if (HOME / ".config/nvim/lua/config/lazy.lua").exists():
            run(["nvim", "--headless", "+Lazy! sync", "+qa"])
        if (HOME / ".zshrc").exists():
            run(["zsh", "-ic", ":"])

    def system_settings(self) -> None:
        run(["sudo", "fc-cache", "-f"])
        run(["fc-cache", "-f"])
        account = self.deployment["account"]
        existing = {
            line.split(":", 1)[0]
            for line in Path("/etc/group").read_text().splitlines()
        }
        missing = set(account["groups"]) - existing
        for group in sorted(missing):
            run(["sudo", "groupadd", "--", group])
        if account["groups"]:
            run(["sudo", "usermod", "-aG", ",".join(account["groups"]), "ashin"])
        run(["sudo", "usermod", "-s", account["shell"], "ashin"])
        run(["sudo", "locale-gen"])
        dconf = self.deployment.get("dconf")
        if dconf:
            source = contained(self.settings, dconf["source"])
            if digest(source) != dconf["sha256"]:
                raise RuntimeError("dconf settings checksum mismatch")
            before = run(["dconf", "dump", "/"], output=True).stdout
            (self.backup / "dconf-before.ini").write_text(before)
            (self.backup / "dconf-before.ini").chmod(0o600)
            subprocess.run(
                ["dconf", "load", "/"], input=source.read_text(), text=True, check=True
            )
        # Merge only the Plymouth hook. Target-specific hooks and UUIDs survive.
        conf = Path("/etc/mkinitcpio.conf")
        if conf.exists() and shutil.which("mkinitcpio", path="/usr/bin"):
            text = conf.read_text()
            match = re.search(r"^HOOKS=\(([^)]*)\)", text, re.MULTILINE)
            if not match:
                raise RuntimeError(
                    "Cannot safely locate target initramfs hooks for Plymouth"
                )
            hooks = match[1].split()
            if "plymouth" not in hooks:
                where = (
                    hooks.index("filesystems") if "filesystems" in hooks else len(hooks)
                )
                hooks.insert(where, "plymouth")
                text = (
                    text[: match.start()]
                    + "HOOKS=("
                    + " ".join(hooks)
                    + ")"
                    + text[match.end() :]
                )
                self.deploy_bytes(text.encode(), "system", "etc/mkinitcpio.conf", 0o644)
            run(["sudo", "mkinitcpio", "-P"])
        else:
            raise RuntimeError(
                "Plymouth integration requires the target mkinitcpio boot stack"
            )

    def capture_schedule(self) -> None:
        for name, text in schedule.unit_files().items():
            self.deploy_bytes(
                text.encode(), "home", ".config/systemd/user/" + name, 0o644
            )
        schedule.initialize()

    def services(self) -> None:
        units = read_json(REPO / "manifests/services.json")
        display = Path("/etc/systemd/system/display-manager.service")
        if display.is_symlink() and display.resolve().name != "sddm.service":
            raise RuntimeError(
                "A competing display manager is enabled; resolve before enabling SDDM"
            )
        if (
            "mariadb.service" in units["system"]
            and run(
                ["sudo", "test", "-d", "/var/lib/mysql/mysql"], check=False
            ).returncode
        ):
            existing = run(
                ["sudo", "ls", "-A", "/var/lib/mysql"], output=True, check=False
            )
            if existing.returncode == 0 and existing.stdout.strip():
                raise RuntimeError(
                    "Existing uninitialized MariaDB data is preserved; review before initialization"
                )
            run(
                [
                    "sudo",
                    "mariadb-install-db",
                    "--user=mysql",
                    "--basedir=/usr",
                    "--datadir=/var/lib/mysql",
                ]
            )
        run(["sudo", "systemctl", "daemon-reload"])
        run(["systemctl", "--user", "daemon-reload"])
        for scope, prefix in [
            ("system", ["sudo", "systemctl"]),
            ("user", ["systemctl", "--user"]),
        ]:
            available = {
                row["unit_file"]
                for row in json.loads(
                    run(
                        [*prefix, "list-unit-files", "--output=json", "--no-pager"],
                        output=True,
                    ).stdout
                )
            }
            for unit in units[scope]:
                if (
                    unit == "intel_lpmd.service"
                    and "GenuineIntel" not in Path("/proc/cpuinfo").read_text()
                ):
                    self.report["conditional_skips"].append(unit)
                    continue
                if unit not in available:
                    raise RuntimeError(f"Required {scope} unit missing: {unit}")
                if "@." in unit:
                    continue  # Template instances belong to the target installation.
                run([*prefix, "enable", unit])
        for unit in units.get("disabled_user", []):
            run(["systemctl", "--user", "disable", unit])
        # Never restart the greeter or networking during bootstrap.
        for unit in ["camp-fi.service", "no-mistakes-daemon-786ed5c5.service"]:
            run(["systemctl", "--user", "start", unit])
            run(["systemctl", "--user", "is-active", "--quiet", unit])
        run(["systemctl", "--user", "enable", "--now", schedule.TIMER])
        self.report["enabled_units"] = units

    def apply(self) -> None:
        private_permissions(self.state)
        with lock(REPO / ".state/operation.lock"), lock(self.state / "operation.lock"):
            self.backup.mkdir(parents=True, exist_ok=False, mode=0o700)
            operations = [
                ("prerequisites", self.prerequisites),
                ("private-overlay", self.overlay),
                ("repositories", self.repositories),
                ("packages", self.packages),
                ("configuration", self.configuration),
                ("language-tools", self.language_tools),
                ("source-tools", self.source_tools),
                ("vendor-tools", self.vendors),
                ("android", self.android),
                ("extensions", self.extensions),
                ("editor-tools", self.editor_tools),
                ("system-settings", self.system_settings),
                ("capture-schedule", self.capture_schedule),
                ("services", self.services),
            ]
            for name, operation in operations:
                self.phase(name, operation)
            self.report["status"] = (
                "installed-pending-signins-and-interactive-review"
                if self.report["pending_signins"]
                else "installed-pending-interactive-review"
            )
            write_json(self.backup / "report.json", self.report)
            print(
                f"\nInstallation completed. Report and configuration backups: {self.backup}"
            )
            print(
                "Complete application sign-ins, then log out/reboot and review boot, SDDM, desktop, audio, and services."
            )


def rollback(run_directory: Path) -> None:
    state = (HOME / ".local/state/cachyos-bootstrap/runs").resolve()
    directory = run_directory.resolve()
    if not directory.is_relative_to(state):
        raise ValueError("Rollback directory must belong to bootstrap run history")
    journal = read_json(directory / "journal.json")
    for row in reversed(journal):
        dest = target_path(row["root"], row["path"])
        reject_symlink_parents(dest)
        prefix = ["sudo"] if row["root"] == "system" else []
        saved = directory / relative(row["saved"])
        if not saved.parent.resolve().is_relative_to(directory):
            raise ValueError("Backup parent escapes the run directory")
        current = (
            str(dest.readlink())
            if dest.is_symlink()
            else digest(dest)
            if dest.is_file()
            else None
        )
        if row["state"] in {"prepared", "rolled-back"}:
            continue
        if current != row["expected"]:
            raise RuntimeError(
                f"Destination changed since deployment; refusing overwrite: {dest}"
            )
        if row["existed"]:
            if not saved.exists() and not saved.is_symlink():
                raise RuntimeError(f"Original backup missing: {saved}")
            run([*prefix, "rm", "--", str(dest)])
            run([*prefix, "cp", "-a", "--", str(saved), str(dest)])
        elif dest.exists() or dest.is_symlink():
            run([*prefix, "rm", "--", str(dest)])
        row["state"] = "rolled-back"
        write_json(directory / "journal.json", journal)
    print(
        "Configuration rollback completed. Packages and service enablement were not rolled back."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--plan",
        action="store_true",
        help="Read-only plan; no downloads or system changes",
    )
    parser.add_argument("--settings", type=Path, default=PRIVATE)
    parser.add_argument(
        "--accept-vendor-installers",
        action="store_true",
        help="Execute named official installers without individual review prompts",
    )
    parser.add_argument(
        "--rollback",
        type=Path,
        help="Restore configuration from one previous run; packages unchanged",
    )
    args = parser.parse_args()
    ensure_user()
    if args.rollback:
        with lock(HOME / ".local/state/cachyos-bootstrap/operation.lock"):
            rollback(args.rollback)
    elif args.plan:
        Bootstrap(args).plan()
    else:
        Bootstrap(args).apply()


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Bootstrap stopped: {error}", file=sys.stderr)
        sys.exit(1)
