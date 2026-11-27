---
name: ci-workflow
description: Rules and a template for writing or changing GitHub Actions workflows in wholagged so they stay cheap (the owner runs many repos with Actions) and secure. Use for any change under .github/.
---

# GitHub Actions: cheap and safe

The owner has many repositories that use Actions, so every workflow must spend as few runner minutes
as possible. Public repos get free standard runners, but private repos share a monthly quota in which
Windows minutes count 2× and macOS minutes 10×; write every workflow as if it were metered.

## Budget rules
1. **Test locally first** (`uv run ruff check`, `uv run pytest -q`) so CI is not used to find bugs.
2. **Trigger narrowly:** `push` to `main` and `pull_request`, with `paths:` limited to code and config
   (`src/**`, `tests/**`, `.claude/hooks/**` (the guard hook has tests), `pyproject.toml`, `uv.lock`,
   `.python-version`, `.github/workflows/**`, and `README*.md`, whose commands `tests/test_docs.py` checks).
   Other docs-only changes don't run CI. Write the list once as a YAML
   anchor (`paths: &code-paths`) and reuse it (`paths: *code-paths`). Tag pushes don't trigger CI, because
   the `push` filter lists only `branches`. No `schedule:` unless it is really needed (then weekly at most). Add `workflow_dispatch` for manual runs.
3. **Cancel superseded runs:** `concurrency: { group: ${{ github.workflow }}-${{ github.ref }}, cancel-in-progress: true }`.
4. **Hard time limit** on every job: `timeout-minutes: 10` (tests take about a second; installing takes the rest).
5. **Cheapest runner by default:** `ubuntu-latest` for lint and tests. Add `windows-latest` (the main platform)
   only to the test job. Add `macos-latest` only where macOS behaviour is under test, ideally on
   `pull_request` or `workflow_dispatch` only.
6. **No uv cache** (`enable-cache: false`); install with `uv sync --locked`. Measured in WL-1 on Linux: a cold
   `uv sync` took 2 s and saving the cache 4 s, and setup-uv keys the cache on `pyproject.toml` + `uv.lock`,
   which every task's version bump changes. Turn it on only when timings show it saves time (e.g. packages
   built from source), and never in release or signing jobs.
7. `fail-fast: true` in matrices; one job for lint and tests when possible, with lint only on Linux
   (`if: runner.os == 'Linux'`), because its result doesn't depend on the OS.
8. Artifacts only when needed, with `retention-days: 3`. Release builds only on `release: published` or
   `workflow_dispatch`, never on `push: tags` (every finished task creates a tag).
9. Dependabot (if used): `github-actions` ecosystem, monthly, grouped into one PR.

## Security rules
- Top-level `permissions: contents: read`; widen per job only when a job needs it.
- Pin every third-party action to a full commit SHA with a version comment. Resolve it with
  `gh api repos/<owner>/<repo>/releases/latest --jq .tag_name`, then
  `gh api repos/<owner>/<repo>/commits/<tag> --jq .sha`.
- Never use `pull_request_target` with a checkout of PR code. Never echo secrets.
- `persist-credentials: false` on `actions/checkout` unless the job pushes.
- uv itself: `setup-uv` with `version: latest-known` and `require-checksums: true`, so CI runs the newest uv
  the pinned action has a checksum for. uv moves forward when `update-deps` bumps the `setup-uv` pin.

## Template
The live workflow is `.github/workflows/ci.yml`; copy its current SHA pins rather than resolving new ones.
```yaml
name: CI
on:
  push:
    branches: [main]
    paths: &code-paths
      - "src/**"
      - "tests/**"
      - ".claude/hooks/**"
      - "pyproject.toml"
      - "uv.lock"
      - ".python-version"
      - ".github/workflows/**"
      - "README*.md"
  pull_request:
    paths: *code-paths
  workflow_dispatch:
permissions:
  contents: read
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
jobs:
  test:
    strategy:
      fail-fast: true
      matrix:
        os: [ubuntu-latest, windows-latest]
    runs-on: ${{ matrix.os }}
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@<sha> # vX.Y.Z
        with:
          persist-credentials: false
      - uses: astral-sh/setup-uv@<sha> # vX.Y.Z
        with:
          version: latest-known
          require-checksums: true
          enable-cache: false
      - run: uv sync --locked
      - run: uv run ruff check
        if: runner.os == 'Linux'
      - run: uv run pytest -q
```
On Linux the PySide6 import may need `QT_QPA_PLATFORM=offscreen` and the `libegl1` / `libxkbcommon0` system
packages; the current tests don't import Qt.

## After pushing
Check once: `gh run list --limit 1`. If it failed: `gh run view <id> --log-failed`, fix, push again.
