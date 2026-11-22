# CLAUDE.md: wholagged

Instructions for Claude Code (and any contributor) working in this repository. Keep this file short,
true and current: improve it after every task (rule 7).

## The project

**wholagged** is a small desktop tool that answers one question for a gamer whose Dota 2 is stuck on
"Searching for Game Coordinator" or lags: *is it your internet, your provider, or Valve's servers?*
It runs six network checks in 10–20 seconds, decides whose side the problem is on, gives practical
advice and builds a plain-text report the user can send to their provider.

- **Stack:** Python 3.15 · PySide6 (`pyside6-essentials`) for the window · standard library for all
  networking · uv · pytest · ruff.
- **Platforms:** Windows 10/11 fully supported; macOS and Linux run but are still in progress.
- **Names:** the product and repo are `wholagged`; the UI shows `APP_NAME` from `__init__.py` (never
  hard-code the name). The project, the package (`src/wholagged/`) and the command are `wholagged`.
  `dota-netcheck` is a deprecated alias script for the same `main`; keep it working (a test checks both).
- **License:** PolyForm Noncommercial 1.0.0. The repo is **public**. External contributions will need a CLA.
- **Status:** v0.2.x. The road to 1.0 is in [TASKS.md](TASKS.md).

```
src/wholagged/
  __init__.py  entry point: GUI by default, --cli for the terminal; __version__, APP_NAME
  checks.py    the six checks + run_checks(); standard library only
  icmp.py      ping: IcmpSendEcho via ctypes on Windows, the `ping` command elsewhere
  verdict.py   decide(): ordered rules → Verdict (side, headline, explanation, advice)
  report.py    plain-text report
  models.py    CheckResult, Verdict, Status, Side
  gui.py       PySide6 window, design tokens, CheckWorker (QThread)
tests/         offline tests: fakes.py (FakeNet), scenarios, parsing, helpers, hook tests
.claude/       agents/, skills/, hooks/, settings.json (Claude Code tooling, see below)
.github/       workflows/ci.yml (lint + tests)
TASKS.md · CHANGELOG.md · DECISIONS.md · README.md (+ README.hy.md, README.ru.md planned)
```

## Commands

uv is mandatory: never `pip`, `venv`, `requirements.txt` or a bare `python` (the guard hook blocks them).

```powershell
uv sync                              # install exactly what uv.lock says
uv run wholagged                     # the window (dota-netcheck is the old alias)
uv run wholagged --cli               # the same checks in the terminal (real network)
uv run pytest -q                     # all tests, offline, ~1 s
uv run ruff check                    # lint (default rules + security rules)
uv add <pkg> / uv add --dev <pkg>    # dependencies: never hand-edit the lists in pyproject.toml
uv tree --outdated --depth 1         # what is behind;  uv audit  # known vulnerabilities
uv version --bump patch|minor        # then set the same __version__ in src/wholagged/__init__.py
uv run --no-project python .claude/skills/cleanup/cleanup.py   # remove junk
```
Headless GUI smoke test:
`QT_QPA_PLATFORM=offscreen uv run python -c "from PySide6.QtWidgets import QApplication; from wholagged.gui import MainWindow; app = QApplication([]); w = MainWindow(); w.show(); app.processEvents(); print('gui ok')"`

## The owner's rules (always follow)

1. **Python version = system Python.** The project's Python (`.python-version`, `requires-python`) must
   match the newest stable CPython installed on the system. When the system one is upgraded, upgrade the
   project too (`update-deps` skill). The SessionStart hook reports a mismatch.
2. **Dependencies first.** At the start of work, check all dependencies (the SessionStart hook does it). If
   anything is outdated, update it and adapt the code (`update-deps` skill).
3. **Optimised code always.** No needless work, I/O or copies; bounded parallelism; no heavy dependency
   where the standard library is enough; nothing slow on the GUI thread.
4. **Never break what works.** New code must not break old code: existing commands, flags, check keys,
   `data` flags, report layout and behaviour keep working. Tests must stay green (the Stop hook runs them).
5. **TASKS.md is the board.** Cards in Jira/Trello style, as small as possible (`XS`/`S`). In every session:
   update and improve the cards, delete the finished ones, add new work. It must always be current.
6. **Bugs are fixed now.** A bug or defect found during a task is fixed in the same session, never filed
   as a card. New features and improvements go to TASKS.md.
7. **After every task:** CHANGELOG entry, version bump, README update, and improve this CLAUDE.md. All of
   these are written in **English** (`finish-task` skill).
8. **Commit and push after every task, without asking** (`finish-task` skill). Never force-push.
9. **Security is a top priority.** See [Security](#security).
10. **Clean up after the push:** temp files, caches, scratch (`cleanup` skill).
11. **Save GitHub Actions minutes.** The owner runs Actions in many repositories: every workflow is
    minimal and budgeted (`ci-workflow` skill).
12. **Autonomy.** Always rely on yourself. Don't ask anyone or wait for an answer. Don't hand tasks to the
    user (don't ask them to do something by hand). Do everything that needs doing yourself. If something
    is unclear, choose the most reasonable option, note the decision and why in
    [DECISIONS.md](DECISIONS.md), and carry on.
13. **Use the project's subagents, skills and hooks** (below). Subagents run on the model and effort of the
    current session: `model: inherit` and no `effort` field. Keep it that way for new agents.
14. **Three languages by default: Armenian (hy), Russian (ru), English (en)** for everything the user sees.
    See [Languages](#languages).
15. **Follow the project's design** ([Design](#design)) and improve the UI/UX where possible. File larger
    UX ideas as `ux` cards.
16. **Web means Cloudflare.** Any web part (site, download page, privacy policy, API, update feed, licence
    server) is hosted on Cloudflare (Workers with static assets, D1/KV/R2, DNS, Registrar for domains).

## How a task runs

1. `start-task`: pick the top ready card (or a given `WL-id`), split it if bigger than `S`, move it to
   In Progress, check that tests and lint are green, plan.
2. Implement. Use `test-engineer` for tests and `translator` for user-facing text; follow `add-check` for
   checks and verdict rules, and `ci-workflow` for `.github/`.
3. `finish-task`: verify → `code-reviewer` (+ `security-auditor` when relevant) → TASKS.md → version →
   CHANGELOG → READMEs → CLAUDE.md → DECISIONS.md → commit → push + tag → `cleanup` → report.

Commit messages: `WL-<id>: <imperative summary>` (`fix:` / `chore:` / `docs:` for work without a card),
a body with the why, and the attribution trailer the harness specifies. Stage explicit paths.
Every version gets a `vX.Y.Z` tag.

## Code conventions

- `checks.py` and `icmp.py` use the **standard library only**, so `--cli` runs without Qt. Every socket,
  HTTP and ping call has a timeout. Fan out with `checks.parallel()`.
- Qt lives only in `gui.py`. The checks run in `CheckWorker` (a `QThread`). The UI is updated only through
  its signals, never from the worker thread directly.
- A check returns `CheckResult(key, status, summary, details, latency_ms, data)`. **`SKIP` means "can't
  tell" and never blames anyone.** Facts for the verdict go in `data` flags.
- Blame carefully: only evidence that points one way may decide the side. Example: `cert_error` is set only
  for a rejected certificate (`ssl.SSLCertVerificationError`), not for any TLS error, because a handshake cut
  off by a middlebox can be the provider.
- **Stable identifiers:** check keys (`internet`, `dns`, `steam_api`, `steam_cm`, `dota_gc`, `relays`) and
  `data` flags are an API for the verdict, the tests and users' reports. Don't rename them.
- `verdict.decide()` rules run top to bottom; the first match wins. Keep the numbered comments in order and
  the README verdict list in sync.
- Modern typed Python 3.15: `from __future__ import annotations`, dataclasses, `StrEnum`, PEP 695 generics.
- ruff must be clean. `# noqa: <code> - <reason>` only with a reason.
- The version lives in `pyproject.toml` and `__init__.__version__`; a test fails if they differ.
- User-facing strings: Armenian, inline, until the i18n core lands (WL-20). After that, every string goes
  through `t()` with hy/ru/en entries.

## Languages

- **App (UI, verdicts, advice, report, CLI):** hy, ru and en; the language comes from the OS, can be switched,
  and the choice is remembered (I18N epic). Until then the app is Armenian only.
- Tone: informal and direct (hy `դու`, ru `ты`, en "you"). Keep gamer and network terms as the existing
  Armenian UI does (ping, packet loss, jitter, relay, router, provider in Latin script). Details are in
  `.claude/agents/translator.md`.
- **Docs:** `README.md` (English) is the source. `README.hy.md` (and `README.ru.md`, WL-35) mirror it in
  every change. `CLAUDE.md`, `CHANGELOG.md`, `TASKS.md` and `DECISIONS.md` are English only.

## Design

The look is defined in `gui.py`; reuse it, don't invent new styles.
- Dark theme: background `#111317`, card `#1a1d23`, raised `#21252c`, border `#2b3038`, text `#e9e7e4`,
  muted `#8d939e`, accent (primary button, progress) `#c8402e` (hover `#d9503d`), running `#58a6ff`.
- Status colours: OK `#3fb950`, WARN `#d29922`, FAIL `#f85149`, SKIP `#6e7681`. Verdict-side chips: you
  `#f85149`, provider `#d29922`, Valve `#a371f7`, PC / fine `#3fb950`.
- Components by object name: `card` (radius 10, 1 px border), `primary` / `link` buttons (radius 8),
  `title` 21 pt bold, `headline` 15 pt bold, `rowTitle` 11 pt semibold, `muted`, `details` 9 pt.
  Segoe UI 10 on Windows. Window 760×860, margins 28/24, spacing 12.
- UX principles: one big obvious action; results appear as each check finishes; problem details open
  automatically; the verdict comes first; every piece of advice is something the user can do now.

## Testing

- Offline only. `tests/fakes.py::FakeNet` replaces the network (`tcp_probe`, `_resolve`, `http_get_json`,
  `icmp.ping`, `time.sleep`); each attribute is a knob that breaks one thing (`internet`, `dns`, `tcp_ok`,
  `cert_ok`, `relays_ok`, `control_ok`, `loss_every`, `relay_extra_ms`, `http[url]`).
- Each verdict branch has a scenario in `test_scenarios.py`. Helpers are tested in `test_parsing.py` and
  `test_net_helpers.py`. `test_claude_hooks.py` tests the guard hook.
- Don't weaken an assertion to make a change pass: a failing old test means old behaviour broke.

## Security

- Never disable TLS verification. Valve's responses are untrusted input: check types before use, cap
  their size (`MAX_BODY_BYTES`), and show them in Qt as plain text (`Qt.TextFormat.PlainText`; rich text only
  for our own strings, escaped with `_html`). No `shell=True`; `subprocess` gets a fixed argv; ping accepts
  only a strict IPv4 address (`ipaddress`).
- The app collects and sends no user data. Keep it that way, and say so in the privacy policy (WL-84).
- No secrets in the repo: tokens, keys, certificates (`.pfx` signing files!) and `.env` are gitignored, and
  the guard hook scans every commit.
- **The owner's private details** (business registration, tax and bank data, address, phone, email) must
  never appear in the repo, commits, issues, PRs or requests to external services. The guard reads them
  from `~/.claude/private-patterns.txt` (outside the repo; never copy it in).
- The repo is public: keep business strategy, revenue numbers and partner names out of all files. Only
  what the README roadmap already says is public.
- On GitHub: secret scanning, push protection and Dependabot alerts are enabled. `uv audit` runs in
  `update-deps`. Workflows use least-privilege `permissions` and SHA-pinned actions.

## GitHub Actions budget

`.github/workflows/ci.yml` runs `uv sync --locked` and pytest on `ubuntu-latest` + `windows-latest` (ruff
on Linux only) for code pushes to `main` and PRs (the `paths` list: `src`, `tests`, `.claude/hooks`,
`pyproject.toml`, `uv.lock`, `.python-version`, workflows). Docs-only commits and tag pushes don't run it,
but a task's version bump does. The Windows job runs the same tests as Linux: FakeNet replaces `icmp.ping`,
so the ctypes ping isn't covered yet (WL-95). Every change under `.github/` follows the `ci-workflow`
skill: narrow `paths`, `concurrency` cancel-in-progress, `timeout-minutes: 10`, no uv cache (measured
slower), SHA-pinned actions, a checksum-verified uv, Windows only for tests, macOS only on PRs or manual
runs, release builds only on `release: published` / `workflow_dispatch`, no cron jobs. Run lint and tests
locally before every push, then check the run once (`gh run list --workflow ci.yml --limit 1`).
Local `actionlint` via `uvx` is refused by the auto-mode classifier; the first CI run validates a workflow.

## Claude Code tooling in `.claude/`

| Kind | Name | Use |
|---|---|---|
| agent | `code-reviewer` | read-only review of pending changes before a commit |
| agent | `security-auditor` | read-only security audit (network, subprocess, deps, workflows, web) |
| agent | `translator` | hy/ru/en strings and translated READMEs |
| agent | `test-engineer` | offline tests with FakeNet, runs the suite |
| skill | `start-task` / `finish-task` | the task workflow above |
| skill | `update-deps` | rules 1–2: Python version, packages, uv_build, action pins |
| skill | `cleanup` | rule 10 |
| skill | `add-check` | recipe for a new check or verdict rule |
| skill | `ci-workflow` | cheap and safe GitHub Actions |
| hook | `session_start.py` | SessionStart: Python/deps/uv_build status, leftovers, last CI run, next tasks |
| hook | `guard.py` | PreToolUse: blocks non-uv Python tooling, lost-work git commands, force pushes, dangerous deletes, running downloads, secrets and private data in commands, repo files, commits and pushes; asks before private data goes to an external tool |
| hook | `post_edit_lint.py` | PostToolUse: ruff on every edited `.py` file |
| hook | `stop_check.py` | Stop: tests + ruff if code changed; reminds to finish/commit/push unshipped work |

Hooks run with `uv run --no-project python`. The guard fails open (a crash lets the call run), so keep
`tests/test_claude_hooks.py` green when changing it. It also checks commands nested in `uv run`, `bash -c`,
`powershell -Command` and `cmd /c`. Documents and spreadsheets (pdf, docx, xlsx, csv) are not committed
unless listed in `.claude/hooks/allowed-documents.txt`.

## Notes and pitfalls

- Python 3.15 runs in UTF-8 mode by default, so printing Armenian to a Windows console or pipe is safe.
- Git has `core.autocrlf=true` here; "LF will be replaced by CRLF" warnings are harmless.
- ruff 0.17's default rule set is broad (`BLE`, `RUF`, `PLW`, `I`, …). `fakes` is configured as a local
  module for import sorting.
- pytest runs with `-p no:cacheprovider` (no `.pytest_cache`), so `--lf` is not available.
- Tests import `fakes` because pytest's default `prepend` import mode puts `tests/` on `sys.path`; there is
  no `conftest.py`.
- Hooks use `uv run --frozen` so they never rewrite `uv.lock`.
- Agents and skills added to `.claude/` load only in the next session. In the session that creates them,
  run a `general-purpose` agent and tell it to follow the agent file.
- The Claude Code auto-mode classifier may refuse edits to permission rules in `.claude/settings.json`.
  Don't work around it; mention it to the owner.
- After renaming the project (distribution) or a script, `uv run` (inexact sync) installs the new one next to
  the old one, and the next `uv sync` (exact) removes the old one with every script both list (v0.2.2:
  `dota-netcheck.exe` vanished). Run `uv sync` before any `uv run` after such a rename, or repair with
  `uv sync --reinstall-package wholagged`. `test_both_commands_are_installed` catches it.
- This shell has `.venv\Scripts` on PATH, so `uv run <cmd>` in another checkout silently falls back to this
  venv's script. Take it off PATH when reproducing install problems elsewhere.
