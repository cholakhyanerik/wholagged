# Decisions

Decisions taken without asking (see [CLAUDE.md](CLAUDE.md) → Autonomy), newest first.
Each entry: the decision, then why. Revisit an entry by adding a new one; don't rewrite history.

## 2026-11-22

- **"System Python" means the newest stable CPython installed outside the project's `.venv`**
  (`uv python list --only-installed`). The project pins its `major.minor` in `.python-version` and
  `requires-python`. Today that is 3.15.2 → 3.15, so no change was needed. The SessionStart hook reports a
  mismatch, and the `update-deps` skill moves the project, after checking that PySide6 has wheels for it.
- **Subagents use `model: inherit` and set no `effort`**, so they run on the session's model and effort
  level (documented Claude Code behaviour). Skills set neither field either.
- **Hooks are Python scripts run with `uv run --no-project python`** (uv-only rule; about 0.1 s each).
  The guard fails open, so a bug in it can't lock the session; `tests/test_claude_hooks.py` covers it instead.
- **The owner's private details are listed in `~/.claude/private-patterns.txt`, outside the repo.** The
  guard blocks them in commands, in files written inside the repo and in commits. Putting the values into
  the repo, even inside a hook, would publish them.
- **An HTTPS certificate failure is a "your side" verdict (`Side.YOU`)**, not `Side.PC`: the PC side shows a
  green "network is fine" chip, which would mislead. It isn't `Side.ISP` either: the usual causes are the
  clock, antivirus HTTPS scanning, a captive portal or missing CA certificates.
- **Known issues listed in the README were fixed now, not filed** (macOS `-W`, Linux locale, SSL blamed on
  the provider), following the bug rule. "Advice is Windows-specific" stays a feature card (WL-40),
  because it needs new texts in three languages.
- **ruff is the linter: its default rules plus flake8-bandit (`S`).** `ruff format` is not adopted yet,
  because it would rewrite every file (WL-90).
- **Versioning:** SemVer, 0.x until 1.0. Every finished task bumps the version (minor for a feature, patch
  for everything else), gets a CHANGELOG entry and a `vX.Y.Z` git tag. `v0.1.0` is tagged on commit
  `0789ab9` (the state before this session) and `v0.1.1` on the commit that ships these changes.
- **The certificate flag is `cert_error`, and it means a rejected certificate only**
  (`ssl.SSLCertVerificationError`). Other TLS failures keep the earlier route-based verdicts, because a
  handshake cut off by a provider's filter must not be called "your PC". The name was settled before
  the first release, so no compatibility alias is needed.
- **External tools (web, artifacts, MCP connectors) are scanned too.** A secret is always blocked. One of
  the owner's private details makes Claude Code ask the owner first, because only they may approve sending
  that data to a specific service.
- **Documents and spreadsheets are not committed by default** (pdf, docx, xlsx, csv): such files often hold
  private data. A file that is public by design goes into `.claude/hooks/allowed-documents.txt`.
- **The `uv run *` permission rule stays.** The guard checks the command inside `uv run`, so that rule
  can't be used to run a blocked command.
- **Languages:** the UI defaults are Armenian, Russian and English (I18N epic). `CLAUDE.md`, `CHANGELOG.md`,
  `TASKS.md` and `DECISIONS.md` are English only. `README.md` is the English source; `README.hy.md` and
  `README.ru.md` mirror it.
- **No CI yet in this session.** WL-1 … WL-4 add it per the `ci-workflow` skill. The repo is public, so
  standard runners are free, but workflows are written as if metered, because the owner runs Actions in
  many repositories.
- **Dependabot alerts on, Dependabot security-update PRs off**: each PR would start CI runs. Updates go
  through the `update-deps` skill instead. With alerts on, GitHub runs its own "Dependency Graph" job when
  the lockfile changes; it's free on a public repo and appears in `gh run list`.
- **Cloudflare for anything web.** There is no web part yet. The privacy-policy page for the Store (WL-84)
  and any later download page, update feed or licence server go on Cloudflare (Workers static assets,
  DNS, Registrar).
- **Task ids use the `WL-` prefix**, and only `XS`/`S` cards may be worked on. Bigger ones are split first.
- **The pytest cache provider is off**, to keep the tree clean (rule 10). As a result `--lf` isn't available.
