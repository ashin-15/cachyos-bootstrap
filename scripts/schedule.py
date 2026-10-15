"""Install or run the persistent four-day local capture schedule."""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import UTC, datetime, timedelta

from capture import Capture
from common import (
    CAPTURE_STATE,
    HOME,
    PRIVATE,
    REPO,
    ensure_user,
    lock,
    read_json,
    reject_symlink_parents,
    run,
    write_json,
)

INTERVAL = timedelta(days=4)
TIMER = "cachyos-capture.timer"


def initialize() -> None:
    """Anchor a newly installed schedule without delaying an existing schedule."""
    if not CAPTURE_STATE.exists():
        write_json(CAPTURE_STATE, {"anchor_at": datetime.now(UTC).isoformat()})


def unit_files() -> dict[str, str]:
    script = str(REPO / "scripts/schedule.py")
    script = script.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%")
    return {
        "cachyos-capture.service": f'''[Unit]
Description=Capture CachyOS environment when four days have elapsed

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 "{script}"
Environment="PATH=/home/ashin/.local/bin:/home/ashin/.npm-global/bin:/home/ashin/.bun/bin:/home/ashin/.cargo/bin:/usr/local/bin:/usr/bin"
Environment=HOME=/home/ashin
Nice=10
IOSchedulingClass=idle
TimeoutStartSec=2h
''',
        TIMER: """[Unit]
Description=Check whether the four-day CachyOS capture is due

[Timer]
OnCalendar=hourly
OnStartupSec=5min
Persistent=true
AccuracySec=1min
Unit=cachyos-capture.service

[Install]
WantedBy=timers.target
""",
    }


def install() -> None:
    directory = HOME / ".config/systemd/user"
    reject_symlink_parents(directory / TIMER)
    directory.mkdir(parents=True, exist_ok=True)
    for name, text in unit_files().items():
        destination = directory / name
        if destination.is_symlink():
            raise RuntimeError(f"Resolve existing unit symlink manually: {destination}")
        destination.write_text(text)
        destination.chmod(0o644)
    with lock(REPO / ".state/operation.lock"):
        initialize()
    run(["systemctl", "--user", "daemon-reload"])
    run(["systemctl", "--user", "enable", "--now", TIMER])
    print("Four-day capture schedule installed. Captures remain local until you push.")


def capture_if_due() -> None:
    # Use the same lock as manual capture and bootstrap, including the due check.
    with lock(REPO / ".state/operation.lock"):
        initialize()
        state = read_json(CAPTURE_STATE)
        timestamp = state.get("last_success_at", state.get("anchor_at"))
        if not isinstance(timestamp, str):
            raise TypeError("Capture schedule timestamp is missing or invalid")
        previous = datetime.fromisoformat(timestamp)
        if previous.tzinfo is None:
            raise ValueError("Capture schedule timestamp must include its time zone")
        due = previous + INTERVAL
        if datetime.now(UTC) < due:
            print(
                f"Capture is not due. Next eligible time: {due.astimezone().isoformat()}"
            )
            return
        if not (PRIVATE / ".git").exists():
            raise RuntimeError(f"Private settings checkout is missing: {PRIVATE}")
        Capture(PRIVATE).execute()
        write_json(CAPTURE_STATE, {"last_success_at": datetime.now(UTC).isoformat()})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--install", action="store_true", help="Install and enable user timer"
    )
    args = parser.parse_args()
    ensure_user()
    if args.install:
        install()
    else:
        capture_if_due()


if __name__ == "__main__":
    try:
        main()
    except (
        OSError,
        RuntimeError,
        TypeError,
        ValueError,
        subprocess.CalledProcessError,
    ) as error:
        print(f"Scheduled capture stopped: {error}", file=sys.stderr)
        sys.exit(1)
