"""Delete build/test leftovers and temp files from the repo (CLAUDE.md rule 10).

Only removes known junk patterns that git does not track, and never touches
.git or .venv. Untracked files that don't match a junk pattern are listed, not
deleted: they may be new work. Stops without deleting anything if git fails.

    uv run --no-project python .claude/skills/cleanup/cleanup.py [--dry-run]
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
KEEP = {".git", ".venv"}
JUNK_DIRS = {"__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", "build", "dist", "htmlcov", "wheels"}
JUNK_DIR_SUFFIXES = (".egg-info",)
JUNK_FILES = {".coverage", "nul", "Thumbs.db", ".DS_Store"}
JUNK_SUFFIXES = (".pyc", ".pyo", ".tmp", ".temp", ".bak", ".orig", ".rej", ".log", "~")


def git_lines(*args: str) -> list[str]:
    proc = subprocess.run(  # noqa: S603 - fixed argv
        ["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=False  # noqa: S607
    )
    if proc.returncode != 0:
        # Without the list of tracked files every match would look like junk: stop instead.
        sys.exit(f"cleanup: `git {' '.join(args)}` failed, nothing deleted: {proc.stderr.strip()}")
    return proc.stdout.splitlines()


def is_junk(path: Path) -> bool:
    name = path.name
    if path.is_dir():
        return name in JUNK_DIRS or name.endswith(JUNK_DIR_SUFFIXES)
    return name in JUNK_FILES or name.endswith(JUNK_SUFFIXES) or name.startswith("~$")


def find_junk() -> list[Path]:
    tracked = {ROOT / p for p in git_lines("ls-files")}
    found: list[Path] = []

    def walk(folder: Path) -> None:
        for child in folder.iterdir():
            if child.name in KEEP:
                continue
            if is_junk(child) and not any(t == child or child in t.parents for t in tracked):
                found.append(child)
            elif child.is_dir() and not child.is_symlink():
                walk(child)

    walk(ROOT)
    return found


def remove(path: Path) -> None:
    # Windows reserves names such as `nul`; only the \\?\ form of the path can delete such a file.
    target = "\\\\?\\" + str(path) if sys.platform == "win32" else str(path)
    if path.is_dir():
        shutil.rmtree(target)
    else:
        os.remove(target)


def main() -> int:
    dry = "--dry-run" in sys.argv[1:]
    junk = find_junk()
    for path in junk:
        rel = path.relative_to(ROOT)
        if dry:
            print(f"would remove {rel}")
            continue
        try:
            remove(path)
        except OSError as exc:
            print(f"could not remove {rel}: {exc}")
        else:
            print(f"removed {rel}")
    if not junk:
        print("nothing to clean")
    leftovers = git_lines("ls-files", "--others", "--exclude-standard")
    if leftovers:
        print("untracked files kept (commit them or delete them by hand if they are scratch):")
        print("\n".join("  " + p for p in leftovers))
    return 0


if __name__ == "__main__":
    sys.exit(main())
