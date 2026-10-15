#!/usr/bin/env python3
"""Read, bump and validate the version in herdr-plugin.toml.

    version.py get                          print the current version
    version.py bump patch|minor|major|X.Y.Z  write the new version, print it
    version.py check                        validate the manifest
"""

import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "herdr-plugin.toml"
SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
VERSION_LINE = re.compile(r'^version = "[^"]*"$', re.M)


def current():
    return tomllib.loads(MANIFEST.read_text())["version"]


def bumped(version, part):
    if SEMVER.match(part):
        return part
    major, minor, patch = map(int, SEMVER.match(version).groups())
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    if part == "patch":
        return f"{major}.{minor}.{patch + 1}"
    sys.exit(f"unknown bump '{part}': use patch, minor, major or X.Y.Z")


def check():
    data = tomllib.loads(MANIFEST.read_text())
    errors = [f"missing '{k}'" for k in ("id", "name", "version", "min_herdr_version") if k not in data]
    if not SEMVER.match(data.get("version", "")):
        errors.append(f"version '{data.get('version')}' is not X.Y.Z")
    for kind in ("actions", "panes"):
        for entry in data.get(kind, []):
            # Commands are ["python3", "bin/herdr-cass", ...]; the script must exist.
            script = next((a for a in entry["command"][1:] if "/" in a), None)
            if script and not (ROOT / script).exists():
                errors.append(f"{kind} '{entry['id']}': {script} not found")
    if errors:
        sys.exit("herdr-plugin.toml: " + "; ".join(errors))
    print(f"{data['id']} {data['version']}: manifest ok")


def main(argv):
    if argv[:1] == ["get"]:
        print(current())
    elif argv[:1] == ["check"]:
        check()
    elif argv[:1] == ["bump"] and len(argv) == 2:
        new = bumped(current(), argv[1])
        MANIFEST.write_text(VERSION_LINE.sub(f'version = "{new}"', MANIFEST.read_text(), count=1))
        print(new)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
