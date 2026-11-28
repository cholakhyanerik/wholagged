"""SessionStart hook: what needs attention before work starts (CLAUDE.md rules 1, 2, 5, 8, 11, 17).

Prints a short plain-text status that Claude Code adds to the session context:
system Python vs the project pin, outdated dependencies, the uv build backend
range, leftovers from the last session, the last CI run, the size of CLAUDE.md
and the next tasks.
It never fails the session: every probe has a timeout and degrades to a note.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLAUDE_MD_TARGET_LINES = 200  # rule 17's soft target; tests/test_claude_md.py enforces the hard limit


def run(*args: str, timeout: float = 20) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            args, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return -1, f"{type(exc).__name__}"
    return proc.returncode, proc.stdout.strip()


def ver(text: str) -> tuple[int, ...]:
    return tuple(int(p) for p in re.findall(r"\d+", text)[:3])


def python_status() -> str:
    pin = (ROOT / ".python-version").read_text(encoding="utf-8").strip()
    code, out = run("uv", "python", "list", "--only-installed", "--output-format", "json")
    if code != 0:
        return f"Python: project pin {pin}; could not list installed interpreters ({out[:80]})"
    system = []
    for item in json.loads(out or "[]"):
        path = item.get("path") or ""
        parts = item.get("version_parts") or {}
        if item.get("implementation") != "cpython" or item.get("variant") != "default":
            continue
        if not re.fullmatch(r"[\d.]+", item.get("version", "")) or str(ROOT).lower() in path.lower():
            continue  # pre-releases and the project's own .venv
        system.append((parts.get("major", 0), parts.get("minor", 0), parts.get("patch", 0)))
    if not system:
        return f"Python: project pin {pin}; no system CPython found"
    newest = max(system)
    newest_s = ".".join(map(str, newest))
    if newest[:2] > ver(pin)[:2]:
        return f"ACTION (rule 1): system Python {newest_s} is newer than the project pin {pin}. Run /update-deps."
    return f"Python: system {newest_s}, project {pin} - OK"


def deps_status() -> str:
    code, out = run("uv", "tree", "--outdated", "--depth", "1", "--frozen", timeout=30)
    if code != 0:
        return "Dependencies: could not check (offline?)"
    outdated = [re.sub(r"^[\s│├└─]+", "", line) for line in out.splitlines() if "(latest:" in line]
    if outdated:
        return "ACTION (rule 2): outdated dependencies: " + "; ".join(outdated) + ". Run /update-deps."
    return "Dependencies: up to date"


def build_backend_status() -> str:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    req = next((r for r in pyproject.get("build-system", {}).get("requires", []) if r.startswith("uv_build")), "")
    upper = re.search(r"<\s*([\d.]+)", req)
    code, out = run("uv", "--version")
    if code != 0 or not upper:
        return ""
    uv_v = ver(out)
    if uv_v >= ver(upper.group(1)):
        return f"ACTION (rule 2): uv {'.'.join(map(str, uv_v))} is past the build backend range `{req}`. Run /update-deps."
    return ""


def git_status() -> str:
    _, dirty = run("git", "status", "--porcelain", "--untracked-files=all")
    code, ahead = run("git", "rev-list", "--count", "@{u}..HEAD")
    notes = []
    if dirty:
        notes.append(f"{len(dirty.splitlines())} uncommitted file(s) left from an earlier session")
    if code == 0 and ahead not in ("", "0"):
        notes.append(f"{ahead} unpushed commit(s)")
    return ("ACTION (rule 8): " + ", ".join(notes) + ". Finish or commit them first.") if notes else "Git: clean"


def ci_status() -> str:
    code, out = run(
        "gh", "run", "list", "--limit", "1", "--json", "status,conclusion,workflowName,headBranch", timeout=15
    )
    if code != 0 or not out or out == "[]":
        return ""
    last = json.loads(out)[0]
    if last.get("conclusion") in ("failure", "timed_out", "startup_failure"):
        return f"ACTION: the last CI run ({last.get('workflowName')}, {last.get('headBranch')}) failed. Fix it first."
    return f"CI: last run {last.get('conclusion') or last.get('status')}"


def private_guard_status() -> str:
    path = Path(os.environ.get("WHOLAGGED_PRIVATE_PATTERNS") or Path.home() / ".claude" / "private-patterns.txt")
    try:
        entries = [s for line in path.read_text(encoding="utf-8").splitlines()
                   if (s := line.strip()) and not s.startswith("#")]
    except OSError:
        entries = []
    if not entries:
        return (f"ACTION (security): {path} is missing or empty, so the guard can't block the owner's private "
                "details. Recreate it from the private memory notes (one literal per line), outside the repo.")
    return ""


def claude_md_status() -> str:
    lines = len((ROOT / "CLAUDE.md").read_text(encoding="utf-8").splitlines())
    if lines > CLAUDE_MD_TARGET_LINES:
        return (f"ACTION (rule 17): CLAUDE.md has {lines} lines (aim for ~{CLAUDE_MD_TARGET_LINES}; "
                "tests/test_claude_md.py enforces the hard limit). Move details to path-scoped .claude/rules/ files.")
    return ""


def tasks_status() -> str:
    path = ROOT / "TASKS.md"
    if not path.exists():
        return "ACTION (rule 5): TASKS.md is missing. Create it."
    lanes: dict[str, list[str]] = {}
    lane = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            lane = line[3:].strip()
        elif line.startswith("### ") and lane:
            lanes.setdefault(lane, []).append(line[4:].strip())
    doing = next((v for k, v in lanes.items() if k.lower().startswith("in progress")), [])
    todo = next((v for k, v in lanes.items() if k.lower().startswith("to do")), [])
    backlog = next((v for k, v in lanes.items() if k.lower().startswith("backlog")), [])
    parts = []
    if doing:
        parts.append("in progress: " + " | ".join(doing))
    if todo:
        parts.append("next: " + " | ".join(todo[:3]))
    elif backlog:  # start-task pulls from the Backlog then, so the board isn't empty
        parts.append("To Do is empty, top of the Backlog (check depends on): " + " | ".join(backlog[:3]))
    return "Tasks: " + ("; ".join(parts) if parts else "board is empty, plan the next milestone")


def main() -> int:
    lines = ["[wholagged session check - .claude/hooks/session_start.py]"]
    probes = (python_status, deps_status, build_backend_status, git_status, ci_status, private_guard_status, claude_md_status,
              tasks_status)
    for probe in probes:
        try:
            line = probe()
        except Exception as exc:  # noqa: BLE001 - a broken probe must not break the session
            line = f"{probe.__name__}: failed ({type(exc).__name__})"
        if line:
            lines.append("- " + line)
    sys.stdout.write("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
