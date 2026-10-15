"""Resolve current SDK components and install through Google's Android CLI."""

from __future__ import annotations

import re
import urllib.request
import xml.etree.ElementTree as ET

from common import HOME, run

CATALOG = "https://dl.google.com/android/repository/repository2-1.xml"


def elements(element: ET.Element, name: str) -> list[ET.Element]:
    return [e for e in element.iter() if e.tag.rsplit("}", 1)[-1] == name]


def first(element: ET.Element, name: str) -> str:
    matches = elements(element, name)
    return (matches[0].text or "") if matches else ""


def revision(element: ET.Element) -> tuple[int, ...]:
    parts = elements(element, "revision")
    if not parts:
        return (0,)
    return tuple(int(first(parts[0], n) or 0) for n in ["major", "minor", "micro"])


def install(policy: dict) -> list[str]:
    cli = HOME / ".local/bin/android"
    if not cli.is_file():
        raise RuntimeError(
            "The checksummed Android CLI seed is missing from private settings"
        )
    # The retained seed is bootstrapping material, not a version lock.
    run([str(cli), "--no-metrics", "update"])
    with urllib.request.urlopen(CATALOG, timeout=120) as response:
        catalog = ET.fromstring(response.read())
    packages = []
    for entry in elements(catalog, "remotePackage"):
        channels = elements(entry, "channelRef")
        if entry.get("obsolete") == "true" or (
            channels and channels[0].get("ref") != "channel-0"
        ):
            continue
        if any(int(node.text or 0) > 0 for node in elements(entry, "preview")):
            continue
        packages.append(entry)
    ids = {p.get("path"): p for p in packages}
    components = {"platform-tools", "cmdline-tools;latest"}
    for api in policy["api_targets"]:
        name = f"platforms;android-{api}"
        if name not in ids:
            raise RuntimeError(f"Required SDK target unavailable: {name}")
        components.add(name)
    platforms = [p for p in ids if re.fullmatch(r"platforms;android-\d+", p or "")]
    if policy["latest_stable"] and platforms:
        components.add(max(platforms, key=lambda p: int(p.rsplit("-", 1)[1])))
    for family in ["build-tools", "ndk", "cmake"]:
        candidates = [p for p in packages if p.get("path", "").startswith(family + ";")]
        if not candidates:
            raise RuntimeError(f"No stable Android {family} available")
        components.add(max(candidates, key=revision).get("path", ""))
    sdk = HOME / "Android/Sdk"
    print("Android SDK licenses may require your response.")
    for component in sorted(components):
        run(
            [
                str(cli),
                "--no-metrics",
                "--sdk=" + str(sdk),
                "sdk",
                "install",
                component.replace(";", "/"),
            ]
        )
    return sorted(components)
