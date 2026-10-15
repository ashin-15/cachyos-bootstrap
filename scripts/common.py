"""Shared manifest, filesystem, privacy, and command helpers."""

from __future__ import annotations

import contextlib
import fcntl
import hashlib
import json
import os
import re
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
HOME = Path("/home/ashin")
PRIVATE = HOME / "Projects/cachyos-settings"
SECRET_KEY = re.compile(
    r"(?i)(?:^|[._-])(?:api[_-]?key|access[_-]?key(?:[_-]?id)?|secret[_-]?key|"
    r"client[_-]?secret|password|passwd|token|auth[_-]?token|"
    r"access[_-]?token|refresh[_-]?token|authorization|private[_-]?key)$"
)
SECRET_VALUE = re.compile(
    r"(?<![A-Za-z0-9_-])(?:sk-(?:proj-|ant-)?[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|"
    r"github_pat_[A-Za-z0-9_]{20,}|xox[baprs]-[A-Za-z0-9-]{15,}|"
    r"AKIA[A-Z0-9]{16}|-----BEGIN (?:OPENSSH |RSA |EC )?PRIVATE KEY-----[\r\n]+[A-Za-z0-9+/=]{40,})"
)
BLOCKED_SYSTEM = {
    "etc/fstab",
    "etc/crypttab",
    "etc/passwd",
    "etc/group",
    "etc/shadow",
    "etc/gshadow",
    "etc/machine-id",
    "etc/default/grub",
}
SYSTEM_PREFIXES = (
    "etc/",
    "usr/share/sddm/themes/",
    "usr/share/fonts/",
    "usr/share/icons/",
    "usr/share/themes/",
    "usr/local/bin/",
)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".new")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    temporary.chmod(0o600)
    temporary.replace(path)


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def relative(value: str) -> Path:
    path = Path(value)
    if (
        not value
        or path.is_absolute()
        or any(p in {".", ".."} for p in value.split("/"))
    ):
        raise ValueError(f"Unsafe relative path: {value}")
    return path


def contained(base: Path, value: str) -> Path:
    path = base / relative(value)
    if not path.resolve().is_relative_to(base.resolve()):
        raise ValueError(f"Path escapes approved root: {value}")
    return path


def target_path(root: str, value: str) -> Path:
    relative(value)
    if root == "home":
        if value.startswith((".ssh/", ".gnupg/")) or value in {".ssh", ".gnupg"}:
            raise ValueError("Credentials are outside the deployment contract")
        destination = HOME / relative(value)
        if not destination.parent.resolve().is_relative_to(HOME.resolve()):
            raise ValueError(f"Destination parent escapes home: {value}")
        return destination
    if (
        root != "system"
        or value in BLOCKED_SYSTEM
        or not value.startswith(SYSTEM_PREFIXES)
    ):
        raise ValueError(f"Unapproved system destination: {value}")
    if value.startswith(
        ("etc/ssh/", "etc/NetworkManager/system-connections/", "etc/grub")
    ):
        raise ValueError(f"Machine identity or GRUB destination: {value}")
    policy = read_json(REPO / "manifests/capture.json")
    selected = any(
        spec["root"] == "system"
        and (
            value == spec["path"]
            or spec["type"] == "tree"
            and value.startswith(spec["path"] + "/")
        )
        for spec in policy["entries"]
    )
    generated = value in {"etc/pacman.conf", "etc/mkinitcpio.conf"}
    font = value.startswith("usr/share/fonts/") and len(Path(value).parts) == 4
    if not (selected or generated or font):
        raise ValueError(f"System destination absent from public allowlist: {value}")
    return Path("/") / value


def reject_symlink_parents(path: Path) -> None:
    for parent in path.parents:
        if parent.is_symlink():
            raise ValueError(f"Symlink parent requires manual resolution: {parent}")


def run(
    args: list[str],
    *,
    cwd: Path | None = None,
    output: bool = False,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, check=check, capture_output=output)


@contextlib.contextmanager
def lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError(f"Another operation holds {path}") from error
        yield


def sensitive_key(key: str) -> bool:
    normalized = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", key)
    return SECRET_KEY.search(normalized) is not None


def redact_text(text: str) -> tuple[str, int]:
    """Remove literal secrets, preserving format for reviewed configuration."""
    count = 0
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        obj = None
    if obj is not None:

        def scrub(value: Any) -> Any:
            nonlocal count
            if isinstance(value, dict):
                result = {}
                for key, item in value.items():
                    if (
                        sensitive_key(key)
                        and item
                        and not isinstance(item, (dict, list))
                    ):
                        result[key] = ""
                        count += 1
                    else:
                        result[key] = scrub(item)
                return result
            if isinstance(value, list):
                return [scrub(item) for item in value]
            if isinstance(value, str):
                result, n = SECRET_VALUE.subn("", value)
                count += n
                return result
            return value

        text = json.dumps(scrub(obj), indent=2, ensure_ascii=False) + "\n"
    else:
        lines = []
        for line in text.splitlines(keepends=True):
            assignment = re.match(
                r'^(\s*(?:export\s+)?[\w.\-"\x27]+\s*[:=]\s*)(.*?)(\r?\n)?$', line
            )
            if assignment:
                key = (
                    re.split(r"[:=]", assignment[1], maxsplit=1)[0]
                    .strip()
                    .removeprefix("export ")
                    .strip('"\x27 ')
                )
                value = assignment[2].strip()
                if sensitive_key(key) and value and not value.startswith(("$", "${")):
                    line = (
                        assignment[1]
                        + '""'
                        + ("," if value.endswith(",") else "")
                        + (assignment[3] or "")
                    )
                    count += 1
            lines.append(line)
        text = "".join(lines)
        text, n = SECRET_VALUE.subn("", text)
        count += n
    text, n = re.subn(
        r"(?i)(Bearer\s+)[A-Za-z0-9._~+/=-]{12,}", r"\1REAUTHENTICATE", text
    )
    count += n
    text, n = re.subn(r"(https?://)[^/@\s]+:[^/@\s]+@", r"\1", text)
    count += n
    text, n = re.subn(
        r"(?i)([?&](?:api[_-]?key|token|access_token)=)[^&\s\"\x27]+", r"\1", text
    )
    count += n
    return text, count


def assert_no_secret(path: Path) -> None:
    """Fail on recognized credential signatures, including inside binary files."""
    with path.open("rb") as stream:
        tail = b""
        while data := stream.read(1024 * 1024):
            chunk = tail + data
            if SECRET_VALUE.search(chunk.decode("latin1")):
                raise ValueError(f"Recognized credential signature in {path}")
            tail = chunk[-512:]


def private_permissions(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    path.chmod(0o700)


def ensure_user() -> None:
    import platform
    import pwd

    if (
        os.geteuid() == 0
        or pwd.getpwuid(os.getuid()).pw_name != "ashin"
        or Path.home() != HOME
    ):
        raise RuntimeError(
            "Requires user ashin and HOME=/home/ashin; do not run with sudo"
        )
    os_release = platform.freedesktop_os_release()
    if os_release.get("ID") != "cachyos" or platform.machine() != "x86_64":
        raise RuntimeError("Requires CachyOS x86-64")
