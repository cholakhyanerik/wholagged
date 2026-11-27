"""The `dota-netcheck` package in alias/dota-netcheck/: the old name, held on PyPI so nobody else can take it (WL-102).

It installs wholagged and the old command, nothing more. release.yml builds and uploads it with every release,
so its version must be wholagged's, and the rest of its metadata must say what wholagged's says.
"""

from __future__ import annotations

import ast
import re
import tomllib
from pathlib import Path, PurePosixPath

from test_claude_md import repo_files

import wholagged

ROOT = Path(__file__).parents[1]
PREFIX = PurePosixPath("alias/dota-netcheck")
ALIAS = ROOT / PREFIX


def _toml(path: Path) -> dict:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _release(version: str) -> tuple[int, int, int]:
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version)
    assert match, f"{version!r} isn't X.Y.Z"
    return int(match[1]), int(match[2]), int(match[3])


MAIN = _toml(ROOT / "pyproject.toml")
OLD = _toml(ALIAS / "pyproject.toml")


def test_alias_has_the_old_name_and_the_same_version():
    """A release uploads both packages at the tag's version; a version PyPI already has would fail the upload."""
    assert OLD["project"]["name"] == "dota-netcheck"
    assert OLD["project"]["version"] == wholagged.__version__, (
        "set the same version in alias/dota-netcheck/pyproject.toml (finish-task step 4)"
    )


def test_alias_declares_nothing_else():
    """No extras or other scripts, and no [tool.*] table but wholagged's source-exclude: a [tool.uv.build-backend]
    with more in it could rename the module or ship other files."""
    assert set(OLD) == {"project", "build-system", "tool"}
    assert OLD["tool"] == {"uv": {"build-backend": MAIN["tool"]["uv"]["build-backend"]}}
    assert set(OLD["project"]) == {
        "name", "version", "description", "readme", "license", "license-files", "authors", "requires-python",
        "dependencies", "urls", "scripts",
    }


def test_alias_installs_wholagged_and_the_old_command():
    """The old command runs the same entry point as wholagged's own alias, so both packages write the same file."""
    [requirement] = OLD["project"]["dependencies"]
    match = re.fullmatch(r"wholagged>=(\S+)", requirement)
    assert match, f"{requirement!r}: only a lower bound, so users of the old name get the newest wholagged"
    assert _release(match[1]) <= _release(wholagged.__version__)
    assert OLD["project"]["scripts"] == {"dota-netcheck": MAIN["project"]["scripts"]["dota-netcheck"]}


def test_alias_metadata_matches_wholagged():
    for key in ("license", "license-files", "authors", "requires-python", "urls"):
        assert OLD["project"][key] == MAIN["project"][key], key
    assert OLD["build-system"] == MAIN["build-system"], "move both [build-system] ranges together (update-deps)"


def test_alias_ships_the_same_license():
    """license-files can't point outside the package folder, so it has a copy."""
    assert (ALIAS / "LICENSE").read_text(encoding="utf-8") == (ROOT / "LICENSE").read_text(encoding="utf-8")


def test_alias_ships_no_code():
    """The build backend needs a module; a docstring is all it may hold, so there is nothing to review in it."""
    # The files the release's checkout holds: build output (ignored by git) doesn't count.
    files = sorted(str(name.relative_to(PREFIX)) for name in repo_files() if name.is_relative_to(PREFIX))
    assert files == ["LICENSE", "README.md", "pyproject.toml", "src/dota_netcheck/__init__.py"]
    [statement] = ast.parse((ALIAS / "src" / "dota_netcheck" / "__init__.py").read_text(encoding="utf-8")).body
    assert isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant)
    assert isinstance(statement.value.value, str)
