"""CLAUDE.md stays short, and its details live in path-scoped .claude/rules/ files (CLAUDE.md rule 17)."""

from __future__ import annotations

import functools
import re
import shutil
import subprocess
from pathlib import Path, PurePosixPath

import pytest

ROOT = Path(__file__).parents[1]
CLAUDE_MD = ROOT / "CLAUDE.md"
RULES = sorted((ROOT / ".claude" / "rules").glob("*.md"))
MAX_LINES = 400


@functools.cache
def repo_files() -> tuple[PurePosixPath, ...]:
    """Tracked and new, not ignored, files: what CI's checkout holds once the task is committed."""
    git = shutil.which("git")
    assert git, "git is needed to list the repo's files"
    out = subprocess.run(  # noqa: S603 - fixed argv, no user input
        [git, "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT, capture_output=True, check=True,
    ).stdout.decode("utf-8")
    return tuple(PurePosixPath(name) for name in out.split("\0") if name)


def front_matter_paths(text: str) -> list[str]:
    """The `paths:` globs of a rules file's frontmatter, written as a YAML list."""
    match = re.match(r"---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        return []
    paths: list[str] = []
    in_paths = False
    for line in match.group(1).splitlines():
        item = line.strip()
        if line.startswith("paths:"):
            in_paths = True
        elif in_paths and item.startswith("- "):
            paths.append(item[2:].strip().strip("\"'"))
        elif item:
            in_paths = False
    return paths


def test_claude_md_is_short():
    lines = len(CLAUDE_MD.read_text(encoding="utf-8").splitlines())
    assert lines <= MAX_LINES, f"CLAUDE.md has {lines} lines (limit {MAX_LINES}): move details to .claude/rules/"


def test_claude_md_has_no_imports():
    # Claude Code expands `@path` everywhere except inside code blocks and code spans.
    text = re.sub(r"```.*?```", "", CLAUDE_MD.read_text(encoding="utf-8"), flags=re.DOTALL)
    text = re.sub(r"`[^`\n]*`", "", text)
    assert not re.findall(r"(?<!\S)@[\w~./\\-]+", text), "an @import loads at startup: use .claude/rules/"


def test_rules_files_exist():
    assert RULES


@pytest.mark.parametrize("rule", RULES, ids=lambda p: p.name)
def test_rules_file_is_path_scoped(rule):
    text = rule.read_text(encoding="utf-8")
    assert not text.startswith("\ufeff"), f"{rule.name} starts with a BOM: save it as UTF-8 without one"
    patterns = front_matter_paths(text)
    assert patterns, f"{rule.name} needs a `paths:` list in its frontmatter, or it loads in every session"
    for pattern in patterns:
        assert "{" not in pattern, f"{rule.name}: write `{pattern}` out as separate globs"
        assert any(f.full_match(pattern) for f in repo_files()), f"{rule.name}: `{pattern}` matches no file"


@pytest.mark.parametrize("rule", RULES, ids=lambda p: p.name)
def test_rules_file_is_listed_in_claude_md(rule):
    row = f"| `{rule.name}` |"
    assert row in CLAUDE_MD.read_text(encoding="utf-8"), f"add {rule.name} to CLAUDE.md's 'Where the details are' table"


def test_front_matter_parser():
    text = '---\npaths:\n  - "src/**/*.py"\n  - tests/**\nother: x\n---\n# Title\n'
    assert front_matter_paths(text) == ["src/**/*.py", "tests/**"]
    assert front_matter_paths("# No frontmatter\n- item\n") == []
    assert front_matter_paths("---\nname: x\n---\n") == []
