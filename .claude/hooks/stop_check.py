"""Stop hook: don't end a turn with broken code or unshipped work (CLAUDE.md rules 4, 7, 8, 17).

1. If Python code, pyproject.toml, uv.lock, CLAUDE.md or .claude/rules/ changed, or a file was deleted
   or renamed (a rules-file glob may now match nothing): run the tests and ruff.
   tests/test_claude_md.py checks CLAUDE.md and .claude/rules/.
   On failure Claude is sent back (exit code 2) with the output.
2. If the tree is dirty or commits are unpushed: remind Claude once to finish
   the task with the finish-task skill, or to say why it stops mid-task.
`stop_hook_active` is honoured, so the hook never loops.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CODE_FILES = (".py", "pyproject.toml", "uv.lock")
TESTED_DOCS = ("CLAUDE.md", ".claude/rules/")  # rule 17: size and path scoping are tested


def run(*args: str, timeout: float = 300) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            args, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return -1, type(exc).__name__
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def tail(text: str, lines: int = 40) -> str:
    return "\n".join(text.splitlines()[-lines:])


def main() -> int:
    try:
        event = json.loads(sys.stdin.buffer.read().decode("utf-8") or "{}")
    except ValueError:
        event = {}
    if event.get("stop_hook_active"):
        return 0

    _, status = run("git", "status", "--porcelain", "--untracked-files=all", timeout=15)
    changed = [line[3:].strip().strip('"') for line in status.splitlines()]
    code, ahead = run("git", "rev-list", "--count", "@{u}..HEAD", timeout=15)
    unpushed = int(ahead) if code == 0 and ahead.isdigit() else 0
    if not changed and not unpushed:
        return 0

    moved = any(code in line[:2] for line in status.splitlines() for code in "DR")
    if moved or any(name.endswith(CODE_FILES) or name.startswith(TESTED_DOCS) for name in changed):
        code, out = run("uv", "run", "--frozen", "--quiet", "pytest", "-q", "-x")
        if code != 0:
            print("Tests fail. New code must not break old code (CLAUDE.md). Fix this first:\n" + tail(out),
                  file=sys.stderr)
            return 2
        code, out = run("uv", "run", "--frozen", "--quiet", "ruff", "check", "--output-format", "concise")
        if code != 0:
            print("ruff reports problems. Fix them first:\n" + tail(out), file=sys.stderr)
            return 2

    parts = []
    if changed:
        parts.append(f"{len(changed)} uncommitted file(s)")
    if unpushed:
        parts.append(f"{unpushed} unpushed commit(s)")
    print(
        "Unshipped work: " + ", ".join(parts) + ". If the task is done, run the finish-task skill now "
        "(TASKS.md, CHANGELOG, version, README, CLAUDE.md, commit, push, cleanup). "
        "If you are deliberately stopping mid-task, say why in your reply.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
