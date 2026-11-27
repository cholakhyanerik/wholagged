---
paths:
  - ".github/**"
---

# GitHub Actions (rule 11)

Every change under `.github/` follows the `ci-workflow` skill (budget rules, template, SHA pins).

## What runs
- `.github/workflows/ci.yml`: `uv sync --locked` and pytest on `ubuntu-latest` + `windows-latest`;
  ruff on Linux only.
- Triggers: code pushes to `main` and PRs. The `paths` list: `src`, `tests`, `.claude/hooks`,
  `pyproject.toml`, `uv.lock`, `.python-version`, workflows, `README*.md` (`tests/test_docs.py`
  checks the install commands players copy, so a README-only PR or web edit is tested too), `alias/**`
  (the `dota-netcheck` package, `tests/test_alias.py`) and `LICENSE` (the alias ships a copy).
- Other docs-only commits and tag pushes don't run it; a task's version bump does.
- After a push, check the run once: `gh run list --workflow ci.yml --limit 1`.
- `.github/workflows/release.yml`: on `release: published`, checks that the tag is `v<version>`, builds
  wholagged and `alias/dota-netcheck` offline with uv's bundled backend (`uv build --no-sources --offline`,
  after `uv python install`), checks that `dist` holds exactly both at that version, and uploads with
  `uv publish --trusted-publishing always --check-url …`: wholagged first, then dota-netcheck in its own
  step, never `continue-on-error`: a refused upload of the old name turns the run red. `--check-url`
  skips files already uploaded, so a failed publish job can be re-run ("Re-run failed jobs") while its
  artifact lasts (3 days); after that, publish a new release. A manual run only builds:
  `gh workflow run release.yml` is the dry run. A task's tag never publishes; only a published release does.

## Budget
- Narrow `paths`, `concurrency` cancel-in-progress, `timeout-minutes: 10`.
- No uv cache (measured slower); a checksum-verified uv.
- Windows only for tests; macOS only on PRs or manual runs.
- Release builds only on `release: published` / `workflow_dispatch`. No cron jobs.

## Security
- Least-privilege `permissions`, SHA-pinned actions, `persist-credentials: false`.
- On GitHub: secret scanning, push protection and Dependabot alerts are enabled.
- PyPI: Trusted Publishing (OIDC) only, never a token. PyPI trusts `release.yml` + the `pypi` environment
  (one publisher for both projects), which only tags `v*` may deploy to. `id-token: write` is on the
  publish job alone, which runs no checkout or build: it uploads the build job's artifact. Renaming
  `release.yml` or the environment breaks publishing until the PyPI publisher is changed too.

## Pitfalls
- Local `actionlint` via `uvx` is refused by the auto-mode classifier; the first CI run validates a workflow.
