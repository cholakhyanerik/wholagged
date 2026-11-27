---
paths:
  - "pyproject.toml"
  - "uv.lock"
  - ".python-version"
  - "src/wholagged/__init__.py"
  - "alias/**"
---

# Packaging, version and names

## Version and dependencies
- The version lives in `pyproject.toml`, `__init__.__version__` and `alias/dota-netcheck/pyproject.toml`;
  tests fail if they differ.
- Bump with `uv version --bump patch|minor`, then set the same `__version__` and the alias's `version`.
- Dependencies: `uv add <pkg>` / `uv add --dev <pkg>`. Never hand-edit the lists.
- The `[build-system]` range (`uv_build>=<uv>,<next minor>`) is the one table edited by hand (`update-deps`),
  in both pyproject files (`tests/test_alias.py` checks they match).
  Move it together with the `setup-uv` pin: `release.yml` builds `--offline`, so it fails once CI's uv is
  outside the range, rather than downloading a `uv_build` into the release.
- `uv_build` ignores `.gitignore`: `source-exclude` keeps secrets and junk out of the package.

## Names
- The UI and the User-Agent use `APP_NAME` from `__init__.py`; never hard-code the name.
- `wholagged` is the command. `dota-netcheck` is a deprecated alias for the same `main`: keep it working
  (`test_both_commands_are_installed`).

## PyPI
- Published by `.github/workflows/release.yml` (`.claude/rules/ci.md`). `[project.urls]` gives the PyPI
  page its links: the README's relative links don't work there.
- `wholagged` and `dota-netcheck` are on PyPI, so both names are ours; their publisher is `release.yml` +
  environment `pypi`, with no API token. To publish: `gh release create vX.Y.Z --verify-tag` on a task's
  tag. A tag alone uploads nothing. Release notes show only commands that are in `ALLOWED` in
  `tests/test_docs.py`; nothing checks them.
- The READMEs install with `uvx wholagged` / `uv tool install wholagged`; the old name as
  `uvx dota-netcheck`. `tests/test_docs.py` keeps README commands to its reviewed lists
  (`.claude/rules/docs.md`).
- The PyPI page shows the README of the newest upload: README-only changes reach it with the next release.
- `uvx` and `uv tool install` ignore `uv.lock`: players get the newest dependencies that `pyproject.toml`
  allows (WL-104). uv 0.13 picks or downloads a Python that fits `requires-python` by itself.
- uvx reuses the version it cached first; `uvx wholagged@latest` checks for a newer one.
- `uv tool install` puts the commands in uv's tool bin folder; when it isn't on PATH, uv warns and
  `uv tool update-shell` adds it. To try installs without touching the system, set `UV_TOOL_DIR` and
  `UV_TOOL_BIN_DIR` to a scratch folder.

## The `dota-netcheck` package (`alias/dota-netcheck/`)
- It holds the old name on PyPI, so `uvx dota-netcheck` can't fetch someone else's code. Its only owner is
  the same account as wholagged's: check `ownership` in `https://pypi.org/pypi/dota-netcheck/json`.
- Never delete `wholagged` or `dota-netcheck` on PyPI: anyone may register a deleted name again, and the
  READMEs and players' cached uvx installs point at both. To retire the old name, leave it or archive it.
- No code: `wholagged>=<floor>` and the script `dota-netcheck = "wholagged:main"`, the same as wholagged's,
  so both packages write an identical file (in one environment uv installs both without a warning). Its
  module is a docstring only, because uv_build needs one. `tests/test_alias.py` keeps it so.
- Same version as wholagged: `release.yml` uploads both with every release. The floor stays where it is
  unless old wholagged versions must never be installed through the old name.
- A standalone project, not a uv workspace member: no lock, no venv, not in the dev environment.
  `uv version` / `uv sync` with `--project alias/dota-netcheck` would create a lock and a venv there (with
  `--frozen`, `uv version` refuses), so edit its `version` line by hand.
- `LICENSE` is a copy (`license-files` can't leave the project folder); its README is the PyPI page, in
  en/hy/ru in one file, and `tests/test_docs.py` checks its commands.
- Build it like the release does: `uv build --no-sources --offline alias/dota-netcheck --out-dir dist`.
- Two uv tools can't own the same command: with the `dota-netcheck` tool installed, `uv tool install
  wholagged` stops with "Executable already exists" (and the other way round). Uninstall the old tool first;
  its README says so. Never offer both tool installs side by side.

## Pitfalls
- After renaming the distribution or a script, `uv run` (inexact sync) installs the new one next to the old
  one, and the next `uv sync` (exact) removes the old one with every script both list.
  - Run `uv sync` before any `uv run` after such a rename.
  - Repair with `uv sync --reinstall-package wholagged`.
- This shell has `.venv\Scripts` on PATH, so `uv run <cmd>` in another checkout silently falls back to
  this venv's script. Take it off PATH when reproducing install problems elsewhere.
- `uv build` writes a `.gitignore` (`*`) into the output folder; upload-artifact leaves it out (hidden file).
- uv 0.13 writes a normalised `pyproject.toml` into the sdist and keeps the original next to it as
  `pyproject.toml.orig` (like Cargo): expected, and only our own comments are in it.
