"""Capture selected state into a private overlay and safe public inventories."""

from __future__ import annotations

import argparse
import configparser
import grp
import json
import os
import re
import shutil
import sys
import tomllib
from datetime import UTC, datetime
from pathlib import Path

from common import (
    CAPTURE_STATE,
    HOME,
    PRIVATE,
    REPO,
    assert_no_secret,
    digest,
    ensure_user,
    lock,
    private_permissions,
    read_json,
    redact_text,
    run,
    target_path,
    write_json,
)

TEXT_SUFFIXES = {
    ".toml",
    ".yaml",
    ".yml",
    ".json",
    ".jsonc",
    ".conf",
    ".ini",
    ".lua",
    ".qml",
    ".js",
    ".ts",
    ".py",
    ".sh",
    ".zsh",
    ".css",
    ".md",
    ".desktop",
    ".service",
    ".socket",
    ".timer",
    ".path",
    ".target",
    ".kvconfig",
    ".txt",
    ".svg",
    ".xml",
}
EXCLUDED_BIN = {
    "devin",
    "agy",
    "codex",
    "claude",
    "copilot",
    "kiro-cli",
    "kiro-cli-chat",
    "kiro-cli-term",
    "omp",
    "no-mistakes",
    "hermes",
    "hermes-agent",
    "hermes-acp",
    "python3.8",
    "python3.11",
    "camp-fi",
    "graphify",
    "graphify-mcp",
    "hf",
    "typer",
}


def shell_template(text: str) -> str:
    """Correct captured startup defects without editing the running shell."""
    text = re.sub(
        r'if \[ -d "/home/ashin/Waterfox" \]; then\s*rm -rf ~/Waterfox\s*fi\n?',
        "",
        text,
    )
    text = re.sub(
        r"^alias update=.*$",
        "alias update='~/Repos/cachyos-bootstrap/capture.sh'",
        text,
        flags=re.MULTILINE,
    )
    text = text.replace(
        '"$ANDROID_HOME/platform-tools:$ANDROID_HOME/cmdline-tools/latest/bin:$PATH"',
        '"$ANDROID_HOME/platform-tools" "$ANDROID_HOME/cmdline-tools/latest/bin"',
    )
    text = text.replace(
        '[ -d "$dir" ] && PATH="${dir}:$PATH"',
        'if [[ -d "$dir" && ":$PATH:" != *":$dir:"* ]]; then PATH="$dir:$PATH"; fi',
    )
    return text.replace("exa --icons", "eza --icons")


class Capture:
    def __init__(self, settings: Path) -> None:
        self.settings = settings
        self.policy = read_json(REPO / "manifests/capture.json")
        self.entries: dict[tuple[str, str], dict] = {}
        self.notes: list[dict] = []
        self.excludes = set(self.policy["global_excludes"])
        self.visited: set[tuple[str, str]] = set()

    def add(self, source: Path, root: str, path: str, hardware: bool = False) -> None:
        if "devin" in path.lower():
            return
        target_path(root, path)
        if not source.exists() and not source.is_symlink():
            return
        if source.is_dir() and not source.is_symlink():
            marker = (root, path)
            if marker in self.visited:
                return
            self.visited.add(marker)
            for child in sorted(source.iterdir()):
                if (
                    child.name.startswith(".tmp-")
                    or child.name in self.excludes
                    or child.name.endswith((".bak", ".old", ".log", ".lock", ".zwc"))
                ):
                    continue
                if child.name.startswith((".env", "auth.", "credentials")):
                    continue
                self.add(child, root, f"{path}/{child.name}", hardware)
            return
        key = (root, path)
        entry = {"root": root, "path": path, "hardware": hardware}
        if source.is_symlink():
            link = str(source.readlink())
            resolved = source.resolve()
            if not source.exists():
                self.notes.append(
                    {
                        "source": str(source),
                        "status": "excluded-broken-source",
                        "reason": "pre-existing broken symlink; no working target to restore",
                    }
                )
                return
            if not (resolved.is_relative_to(HOME) or resolved.is_relative_to("/usr")):
                self.notes.append(
                    {
                        "source": str(source),
                        "status": "unresolved",
                        "reason": "symlink outside approved roots",
                    }
                )
                return
            if resolved.is_relative_to(HOME):
                destination = str(resolved.relative_to(HOME))
                if destination.startswith(
                    (".ssh", ".gnupg", ".codex/auth", ".local/share/keyrings")
                ):
                    raise RuntimeError(
                        f"Credential symlink is outside capture scope: {source}"
                    )
                self.add(resolved, "home", destination, hardware)
            entry.update(kind="symlink", link=link)
        elif source.is_file():
            destination = self.settings / "files" / root / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            with source.open("rb") as stream:
                header = stream.read(8192)
            content = b""
            is_text = source.suffix in TEXT_SUFFIXES or (
                b"\x00" not in header and source.stat().st_size < 2_000_000
            )
            redactions = 0
            if is_text:
                try:
                    text = source.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    is_text = False
                else:
                    is_code = (
                        source.suffix
                        in {
                            ".py",
                            ".js",
                            ".ts",
                            ".qml",
                            ".lua",
                            ".sh",
                            ".zsh",
                            ".md",
                            ".css",
                        }
                        or header.startswith(b"#!")
                        or "/skills/" in str(source)
                        or "/snippets/" in str(source)
                    )
                    if not is_code:
                        text, redactions = redact_text(text)
                    if path == ".zshrc":
                        text = shell_template(text)
                    content = text.encode()
            if is_text:
                destination.write_bytes(content)
            else:
                shutil.copyfile(source, destination)
            destination.chmod(0o600)
            assert_no_secret(destination)
            entry.update(
                kind="file",
                source=f"files/{root}/{path}",
                sha256=digest(destination),
                mode=source.stat().st_mode & 0o777,
                bytes=destination.stat().st_size,
            )
            if redactions:
                self.notes.append(
                    {
                        "source": str(source),
                        "status": "reauthenticate",
                        "redactions": redactions,
                    }
                )
        else:
            self.notes.append(
                {
                    "source": str(source),
                    "status": "excluded",
                    "reason": "not a regular file/link",
                }
            )
            return
        self.entries[key] = entry

    def active_login_theme(self) -> None:
        config = configparser.ConfigParser(interpolation=None, strict=False)
        sources = []
        for directory in [Path("/usr/lib/sddm/sddm.conf.d"), Path("/etc/sddm.conf.d")]:
            if directory.is_dir():
                sources.extend(sorted(directory.glob("*.conf")))
        sources.append(Path("/etc/sddm.conf"))
        config.read(sources)
        theme = config.get("Theme", "Current", fallback="").strip()
        if not theme:
            return
        directory = Path(
            config.get("Theme", "ThemeDir", fallback="/usr/share/sddm/themes")
        )
        if (
            directory != Path("/usr/share/sddm/themes")
            or not re.fullmatch(r"[A-Za-z0-9_.-]+", theme)
            or theme in {".", ".."}
        ):
            self.notes.append(
                {
                    "source": "SDDM theme selection",
                    "status": "unresolved",
                    "reason": "Nonstandard theme path requires an explicit reviewed capture policy",
                }
            )
            return
        theme_path = directory / theme
        if not theme_path.is_dir():
            self.notes.append(
                {
                    "source": str(theme_path),
                    "status": "unresolved",
                    "reason": "Selected SDDM theme directory is missing",
                }
            )
            return
        entries = [
            entry
            for entry in self.policy["entries"]
            if not (
                entry["root"] == "system"
                and entry["path"].startswith("usr/share/sddm/themes/")
            )
        ]
        entries.append(
            {"root": "system", "path": str(theme_path.relative_to("/")), "type": "tree"}
        )
        if entries != self.policy["entries"]:
            self.policy["entries"] = entries
            write_json(REPO / "manifests/capture.json", self.policy)

    def inventory(self) -> dict:
        all_packages = run(["pacman", "-Q"], output=True).stdout.splitlines()
        explicit = set(run(["pacman", "-Qqe"], output=True).stdout.split())
        foreign = set(run(["pacman", "-Qqm"], output=True).stdout.split())
        excluded = set(self.policy["excluded_packages"])
        packages = [
            {
                "name": line.split()[0],
                "observed_version": line.split()[1],
                "explicit": line.split()[0] in explicit,
                "observed_foreign": line.split()[0] in foreign,
            }
            for line in all_packages
            if line.split()[0] not in excluded
        ]
        additions = [
            "git",
            "git-lfs",
            "github-cli",
            "python",
            "python-yaml",
            "npm",
            "bun",
            "uv",
            "rustup",
            "sddm",
            "qt6-5compat",
            "qt6-multimedia",
            "qt6-declarative",
            "fontconfig",
            "fzf",
            "bat",
            "eza",
            "curl",
            "unzip",
            "base-devel",
            "satty",
            "cliphist",
            "wl-clipboard",
            "xorg-xhost",
            "uwsm",
            "swash",
        ]
        names = {p["name"] for p in packages}
        for name in additions:
            if name not in names:
                packages.append(
                    {
                        "name": name,
                        "explicit": True,
                        "observed_foreign": False,
                        "observed_version": None,
                    }
                )
        for package in packages:
            package["runtime_required"] = (
                package["name"] in additions or package["name"] == "dconf"
            )
        write_json(
            REPO / "manifests/packages.json",
            {
                "schema_version": 1,
                "version_policy": "latest",
                "excluded": sorted(excluded),
                "packages": packages,
            },
        )
        npm = json.loads(
            run(["npm", "list", "--global", "--depth=0", "--json"], output=True).stdout
        )
        npm_names = sorted(
            set(npm.get("dependencies", {})) | set(self.policy["npm_extra"])
        )
        bun_file = HOME / ".bun/install/global/package.json"
        bun = read_json(bun_file).get("dependencies", {}) if bun_file.exists() else {}
        uv_tools = []
        for tool in sorted((HOME / ".local/share/uv/tools").iterdir()):
            receipt = tool / "uv-receipt.toml"
            if receipt.is_file():
                for requirement in (
                    tomllib.loads(receipt.read_text())
                    .get("tool", {})
                    .get("requirements", [])
                ):
                    if requirement["name"] == "camp-fi":
                        continue
                    if (
                        "directory" in requirement
                        or "git" in requirement
                        or "url" in requirement
                    ):
                        self.notes.append(
                            {
                                "source": str(receipt),
                                "status": "unresolved",
                                "reason": "non-registry uv tool requires source recipe",
                            }
                        )
                    else:
                        uv_tools.append(requirement["name"])
            elif tool.is_dir():
                self.notes.append(
                    {
                        "source": str(tool),
                        "status": "excluded-broken-installation",
                        "reason": "missing uv receipt; no runnable installation recorded",
                    }
                )
        cargo_output = run(["cargo", "install", "--list"], output=True).stdout
        cargo = [
            line.split()[0]
            for line in cargo_output.splitlines()
            if line and not line.startswith(" ")
        ]
        components = [
            line.rsplit("-x86_64", 1)[0]
            for line in run(
                ["rustup", "component", "list", "--installed"], output=True
            ).stdout.splitlines()
        ]
        tools = {
            "schema_version": 1,
            "npm": npm_names,
            "bun": sorted(bun),
            "uv": sorted(set(uv_tools)),
            "cargo": cargo,
            "rust_components": components,
            "python_versions": ["3.11", "3.12"],
            "vendor_installers": self.policy["vendor_installers"],
            "source_repos": self.policy["source_repos"],
        }
        write_json(REPO / "manifests/tools.json", tools)
        unit_state = {}
        for scope, extra in [("system", []), ("user", ["--user"])]:
            result = run(
                [
                    "systemctl",
                    *extra,
                    "list-unit-files",
                    "--state=enabled",
                    "--output=json",
                    "--no-pager",
                ],
                output=True,
                check=False,
            )
            if result.returncode:
                raise RuntimeError(
                    f"Cannot capture {scope} enabled services; rerun with system bus access"
                )
            unit_state[scope] = [row["unit_file"] for row in json.loads(result.stdout)]
        unit_state.update(schema_version=1, disabled_user=["hermes-gateway.service"])
        write_json(REPO / "manifests/services.json", unit_state)
        repos = run(["pacman-conf", "--repo-list"], output=True).stdout.splitlines()
        if "openai-chatgpt" in repos:
            server = run(
                ["pacman-conf", "--repo", "openai-chatgpt", "Server"], output=True
            ).stdout.strip()
            if not server.startswith("https://persistent.oaistatic.com/"):
                raise RuntimeError("Unexpected source for openai-chatgpt repository")
            write_json(
                REPO / "manifests/repositories.json",
                {
                    "schema_version": 1,
                    "extra": [
                        {
                            "name": "openai-chatgpt",
                            "server": server,
                            "key_file": "manifests/openai-repository.asc",
                            "key_fingerprint": "3BFA0E4AE8B8CC16A2D9BA684A3B4A566C4660E4",
                        }
                    ],
                },
            )
        return tools

    def extensions(self) -> None:
        result = {}
        for label, command in [("code", "code"), ("cursor", "cursor")]:
            if shutil.which(command):
                proc = run([command, "--list-extensions"], output=True, check=False)
                result[label] = sorted(
                    line
                    for line in proc.stdout.splitlines()
                    if re.fullmatch(r"[\w-]+\.[\w.-]+", line)
                )
        write_json(
            REPO / "manifests/extensions.json", {"schema_version": 1, "editors": result}
        )

    def execute(self) -> None:
        private_permissions(self.settings)
        self.active_login_theme()
        self.inventory()
        self.notes.extend(
            {
                "source": str(HOME / item["path"]),
                "status": "excluded-credentials-only",
                "reason": item["reason"],
            }
            for item in self.policy.get("excluded_files", [])
        )
        for spec in self.policy["entries"]:
            source = target_path(spec["root"], spec["path"])
            try:
                self.add(
                    source, spec["root"], spec["path"], spec.get("hardware", False)
                )
            except PermissionError:
                self.notes.append(
                    {
                        "source": str(source),
                        "status": "unresolved",
                        "reason": "requires privileged read",
                    }
                )
        # Directly installed fonts are persistent assets, not package inventories.
        for source in sorted(Path("/usr/share/fonts").iterdir()):
            if (
                source.is_file()
                and run(
                    ["pacman", "-Qqo", str(source)], output=True, check=False
                ).returncode
            ):
                self.add(source, "system", str(source.relative_to("/")))
        for source in sorted((HOME / ".local/bin").iterdir()):
            if source.name in EXCLUDED_BIN or ".old" in source.name:
                continue
            self.add(source, "home", str(source.relative_to(HOME)))
        # no-mistakes has a maintained installer; don't retain its daemon/database.
        # Required symlink target for locally built tools is captured by add().
        groups = sorted(g.gr_name for g in grp.getgrall() if "ashin" in g.gr_mem)
        hardware = {}
        for name in ["sys_vendor", "product_name", "product_version"]:
            path = Path("/sys/class/dmi/id") / name
            hardware[name] = path.read_text().strip() if path.exists() else ""
        dconf = None
        if shutil.which("dconf"):
            text = run(["dconf", "dump", "/"], output=True).stdout
            text, redactions = redact_text(text)
            destination = self.settings / "settings/dconf.ini"
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(text)
            destination.chmod(0o600)
            assert_no_secret(destination)
            dconf = {"source": "settings/dconf.ini", "sha256": digest(destination)}
            if redactions:
                self.notes.append(
                    {
                        "source": "dconf settings",
                        "status": "reauthenticate",
                        "redactions": redactions,
                    }
                )
        metadata = {
            "schema_version": 1,
            "captured_at": datetime.now(UTC).isoformat(),
            "entries": list(self.entries.values()),
            "notes": self.notes,
            "hardware": hardware,
            "account": {"shell": "/usr/bin/zsh", "groups": groups},
            "dconf": dconf,
        }
        write_json(self.settings / "deployment.json", metadata)
        referenced = {e["source"] for e in self.entries.values() if e["kind"] == "file"}
        archived = (
            self.settings
            / "captures"
            / ("superseded-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ"))
        )
        for directory, _, names in os.walk(self.settings / "files", followlinks=False):
            for name in names:
                item = Path(directory) / name
                rel = str(item.relative_to(self.settings))
                if rel not in referenced:
                    destination = archived / rel
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    item.replace(destination)
        lfs = [
            json.dumps(e["source"]) + " filter=lfs diff=lfs merge=lfs -text"
            for e in self.entries.values()
            if e.get("bytes", 0) >= 25 * 1024 * 1024
        ]
        (self.settings / ".gitattributes").write_text("\n".join(sorted(lfs)) + "\n")
        self.extensions()
        write_json(
            REPO / "manifests/android.json",
            {
                "schema_version": 1,
                "api_targets": [35, 36],
                "latest_stable": True,
                "families": ["platform-tools", "build-tools", "ndk", "cmake"],
            },
        )
        unresolved = [n for n in self.notes if n["status"] == "unresolved"]
        print(
            f"Captured {len(self.entries)} private deployment entries; {len(unresolved)} unresolved sources."
        )
        print(
            "Review deployment.json notes and both Git diffs before committing. Nothing was published."
        )
        if unresolved:
            raise RuntimeError(
                "Capture has unresolved sources; see private deployment.json."
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--settings", type=Path, default=PRIVATE)
    args = parser.parse_args()
    ensure_user()
    with lock(REPO / ".state/operation.lock"):
        settings = args.settings.expanduser().resolve()
        Capture(settings).execute()
        if settings == PRIVATE.resolve():
            write_json(
                CAPTURE_STATE, {"last_success_at": datetime.now(UTC).isoformat()}
            )


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError) as error:
        print(f"Capture stopped: {error}", file=sys.stderr)
        sys.exit(1)
