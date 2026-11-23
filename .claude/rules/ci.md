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
  `pyproject.toml`, `uv.lock`, `.python-version`, workflows.
- Docs-only commits and tag pushes don't run it; a task's version bump does.
- After a push, check the run once: `gh run list --workflow ci.yml --limit 1`.

## Budget
- Narrow `paths`, `concurrency` cancel-in-progress, `timeout-minutes: 10`.
- No uv cache (measured slower); a checksum-verified uv.
- Windows only for tests; macOS only on PRs or manual runs.
- Release builds only on `release: published` / `workflow_dispatch`. No cron jobs.

## Security
- Least-privilege `permissions`, SHA-pinned actions, `persist-credentials: false`.
- On GitHub: secret scanning, push protection and Dependabot alerts are enabled.

## Pitfalls
- Local `actionlint` via `uvx` is refused by the auto-mode classifier; the first CI run validates a workflow.
