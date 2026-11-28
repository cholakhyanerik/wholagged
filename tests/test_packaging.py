"""wholagged's runtime dependencies as players install them from PyPI (WL-104).

`uvx wholagged` and `uv tool install wholagged` ignore uv.lock: they get the newest versions pyproject.toml allows.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).parents[1]
MAIN = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
LOCK = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))

# name>=A.B[.C…],<A.B+1: patch releases of the tested minor (6.12.1, 6.12.1.1), nothing newer.
BOUNDED = re.compile(r"(?P<name>[a-z0-9-]+)>=(?P<floor>\d+\.\d+(?:\.\d+)*),<(?P<cap>\d+\.\d+)")


def _minor(version: str) -> tuple[int, int]:
    parts = version.split(".")
    assert len(parts) >= 2 and all(part.isdigit() for part in parts), f"{version!r} isn't A.B[.C…]"
    return int(parts[0]), int(parts[1])


def _locked(name: str) -> str:
    versions = [package["version"] for package in LOCK["package"] if package["name"] == name]
    assert len(versions) == 1, f"{name}: want one locked version, uv.lock has {versions}"
    return versions[0]


def test_runtime_dependencies_stay_on_the_tested_minor():
    """Players get the bug and security fixes of the minor CI tested, but a new minor (a new Qt) only once
    update-deps has raised the floor and the cap with `uv add` and locked it: `uv lock --upgrade` stays under it."""
    requirements = MAIN["project"]["dependencies"]
    assert requirements, "wholagged has runtime dependencies (PySide6)"
    for requirement in requirements:
        match = BOUNDED.fullmatch(requirement)
        assert match, f"{requirement!r}: write it as name>=A.B[.C…],<A.B+1 (update-deps)"
        major, minor = _minor(_locked(match["name"]))
        assert _minor(match["floor"]) == (major, minor), f"{requirement!r}: the floor is the locked minor"
        assert _minor(match["cap"]) == (major, minor + 1), f"{requirement!r}: the cap is the next minor"


def test_the_qt_cap_holds_shiboken_too():
    """PySide6 pins shiboken6 to its own version, so the one cap covers both. If a release ever loosens that pin,
    the lock would take a newer shiboken6 than the PySide6 it was built for, and this fails: cap shiboken6 too."""
    assert _locked("shiboken6") == _locked("pyside6-essentials")
