"""PostToolUse hook: lint every Python file Claude edits, right away.

Runs `ruff check` on the edited file. Problems go back to Claude on stderr with
exit code 2, so they are fixed in the same step instead of piling up.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    try:
        event = json.loads(sys.stdin.buffer.read().decode("utf-8") or "{}")
    except ValueError:
        return 0
    path = (event.get("tool_input") or {}).get("file_path") or ""
    if not path.endswith(".py"):
        return 0
    try:
        rel = Path(path).resolve().relative_to(ROOT)
    except ValueError:
        return 0  # outside the repo
    if not (ROOT / rel).exists():
        return 0
    try:
        proc = subprocess.run(
            ["uv", "run", "--frozen", "--quiet", "ruff", "check", "--output-format", "concise", str(rel)],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return 0
    if proc.returncode == 1:  # 1 = lint findings; anything else is a tool problem, not the code's
        print(f"ruff found problems in {rel}. Fix them now:\n{proc.stdout.strip()}", file=sys.stderr)
        return 2
    if proc.returncode != 0:
        print(f"post_edit_lint: ruff could not run ({proc.returncode}): {proc.stderr.strip()[:300]}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
