---
name: update-deps
description: Bring wholagged's Python version and dependencies up to date (CLAUDE.md rules 1 and 2) - match the system Python, upgrade packages, the uv build backend and pinned GitHub Actions, and adapt the code. Use when the session-start check reports an ACTION for Python or dependencies, and at the start of each milestone.
---

# Update the Python version and dependencies

uv only. Never pip, venv or bare `python` (the guard hook blocks them).

## 1. Python must match the system (rule 1)
1. `uv python list --only-installed`. The "system" Python is the newest stable CPython installed outside
   the project's `.venv`. Compare its `major.minor` with `.python-version`.
2. If the system one is newer, first check that every dependency supports it: try
   `uv lock --upgrade --python X.Y` on a scratch copy of the tree, or check that PyPI has wheels
   (PySide6 / shiboken6 are the usual blockers).
3. If supported: `uv python pin X.Y`, set `requires-python = ">=X.Y"` in `pyproject.toml` and `alias/dota-netcheck/pyproject.toml`, `uv lock`,
   `uv sync`, then update the Python badge and text in `README.md`, `README.hy.md` (and `README.ru.md`),
   and the Python version in `.github/workflows/*` if it is set there. ruff takes its target version from
   `requires-python`, so nothing else to change there.
4. If not supported yet: keep the current pin, log it in `DECISIONS.md`, and add a `TASKS.md` card
   "Move to Python X.Y when <package> supports it".

## 2. Packages (rule 2)
1. `uv tree --outdated --depth 1` lists what is behind.
2. `uv lock --upgrade` (or `uv lock --upgrade-package <name>`), then `uv sync`.
3. For each **major** bump, read the package's changelog for breaking changes and adapt the code
   (PySide6: deprecated enums and APIs; pytest: removed options).
4. Raise the lower bounds to the versions you tested: `uv add "pyside6-essentials>=A.B.C"`,
   `uv add --dev "pytest>=…" "ruff>=…"`. Never hand-edit the dependency lists.
5. `uv audit` must report no known vulnerabilities.
6. New ruff version? Run `uv run ruff check` and fix new findings rather than silencing them.

## 3. Build backend and tools
- `uv --version`. `[build-system] requires` must be `uv_build>=<uv version>,<next minor>`
  (for example uv 0.13.9 → `uv_build>=0.13.9,<0.14.0`). This is the one table that is edited by hand, in
  `pyproject.toml` and in `alias/dota-netcheck/pyproject.toml` alike (`tests/test_alias.py`).
- GitHub Actions (when workflows exist): bump each pinned action to its latest release SHA,
  for example `gh api repos/actions/checkout/releases/latest --jq .tag_name` and then
  `gh api repos/actions/checkout/commits/<tag> --jq .sha`. Keep the `# vX.Y.Z` comment next to the SHA.

## 4. Verify and ship
`uv run ruff check`, `uv run pytest -q`, and the headless GUI smoke test from `finish-task`. Record
everything under `Dependencies` in CHANGELOG, then run `finish-task`.
