# Decisions

Decisions taken without asking (see [CLAUDE.md](CLAUDE.md) → Autonomy), newest first.
Each entry: the decision, then why. Revisit an entry by adding a new one; don't rewrite history.

## 2026-11-22

- **The User-Agent is built from `APP_NAME`; the ICMP payload stays a literal (WL-13).** `checks.py` already
  imports from the package, so the name has one source there. `icmp.py` keeps a fixed 32-byte literal
  (`wholagged-ping-0123456789abcdefg`) so its size can't drift; a test checks the prefix and the length.
- **`[tool.uv.build-backend] module-name` is removed (WL-12):** with the project named `wholagged`, uv_build
  finds `src/wholagged/` by itself, so the line would only repeat the default.
- **The `dota-netcheck` alias prints no deprecation notice.** The CHANGELOG marks it deprecated; a runtime
  notice would need a new user-facing string in three languages (before i18n exists) and would only add noise
  to a command that keeps working.
- **The upgrade break in old clones is documented, not worked around.** A plain `uv sync` after `git pull`
  uninstalls `dota-netcheck` and then installs `wholagged`, and both commands work. The break needs an inexact
  `uv run` first (it installs `wholagged` next to the old distribution), then an exact `uv sync`, which removes
  the old distribution and the `dota-netcheck` script both list. `uv sync --reinstall-package wholagged` repairs
  it from any state, and the next change to `pyproject.toml` (every release) heals it. The automatic
  alternative, `[tool.uv] reinstall-package = ["wholagged"]`, rebuilds the project on every `uv run` (rule 3).
  A test now checks that both commands are installed, so a broken dev venv fails the Stop hook with the fix.
- **No `dota_netcheck` import shim after the package rename (WL-11).** wholagged is an app, not a library:
  nothing outside the repo imports the package or runs it with `python -m`, and the `dota-netcheck` command
  (what users run) keeps working. A shim would be a second top-level module in the wheel for no user.
- **The build excludes secret and junk patterns (`source-exclude`)**, because uv_build ignores `.gitignore`;
  the WL-11 audit showed a `.pfx` dropped into `src/wholagged/` would ship. Verified with planted files.
- **Reserving `wholagged` on PyPI is a card (WL-15), not done here:** it needs the owner's PyPI account, and
  nothing installs from PyPI today (the README says `uv` from a clone only).
- **Until WL-12, `[tool.uv.build-backend] module-name = "wholagged"`** tells uv_build where the package is,
  because it otherwise derives the module from the project name (`dota-netcheck` → `dota_netcheck`).
- **The product name lives in one constant, `APP_NAME` in the package `__init__`**, next to `__version__`.
  The window, the CLI banner and the report use it, so the name isn't scattered again.
- **The report header and the CLI banner carry the version and the game (`wholagged 0.2.0 · Dota 2`).** The card only asked for the
  name. A pasted report is most useful when you can tell which version wrote it, and the layout stays the
  same: the header is still a single line.
- **The subtitle, the CLI banner and the report header name the game ("Dota 2")**, so when CS2 and Deadlock arrive the game becomes
  a `{game}` placeholder (the translator suggested hy `Ստուգում է {game}-ի կապը՝ …`). The window title and
  the big title label in the window are just "wholagged".
- **WL-10 bumps the minor version (0.2.0)**: its card type is `feature` and the name is visible to users.
- **CI keeps no uv cache (`enable-cache: false`), against WL-1's "uv cache" criterion.** The first run
  measured on Linux a cold `uv sync --locked` (Python 3.15 and PySide6 included) at 2 s and the cache save at 4 s, and
  the cache key changes with every version bump. The `ci-workflow` skill now says so; turn the cache back on
  only if timings show it pays off.
- **ruff runs only in the Linux job of the matrix:** lint results don't depend on the OS, so the Windows job
  only syncs and tests.
- **CI also triggers on `.claude/hooks/**` and `.python-version`**, beyond the skill's original list:
  `tests/test_claude_hooks.py` loads the guard hook, and `.python-version` picks the Python that uv installs
  in CI. The `paths` list is written once as a YAML anchor (supported by GitHub Actions) and reused for
  `pull_request`, so the two lists can't drift apart.
- **CI installs the full lock (`uv sync --locked`), PySide6 included**, though today's tests don't import
  Qt: it proves the lock installs on the runner, and the headless GUI test (WL-92) will need it. The uv
  cache doesn't make this cheap: setup-uv keys it on the hash of `pyproject.toml` and `uv.lock`, and every
  task bumps the version in both, so task pushes miss it; only re-runs and unchanged PR pushes hit.
  Whether to keep it is decided from the first runs' timings (WL-2).
- **WL-1 and WL-2 ship as two versions** (0.1.2, then 0.1.3): one card in progress at a time, and one
  commit, tag and CHANGELOG entry per finished task.
- **CI uses `setup-uv` with `version: latest-known` and `require-checksums: true`, and leaves `enable-cache` on
  its default (`auto`)**, following the WL-1 security audit. uv in CI moves only with a reviewed bump of the
  action pin. `auto` caches on these triggers, and it won't restore a possibly poisoned cache in a future
  release job. The audit's repo-setting findings (fork PR approval, enforced SHA pinning) became WL-5 rather
  than being changed here: they are outside this card, and enforced pinning first needs a check that it
  doesn't break GitHub's own Dependency Graph job.
- **"A docs-only push does not start CI" rests on the `paths` filter.** The push filter lists only
  `branches`, so tag pushes don't start it either. A finished docs task still runs CI, because its version
  bump touches `pyproject.toml` and `uv.lock`; only commits without a bump are free.
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
