# CLAUDE.md: wholagged

Instructions for Claude Code (and any contributor) in this repository. This file loads into every session,
so it holds only the owner's rules, the architecture and pointers (rule 17). The details are in
`.claude/rules/*.md`, and each of those loads only when Claude reads the files its `paths:` lists.

## The project

**wholagged** answers one question for a gamer whose Dota 2 is stuck on "Searching for Game Coordinator"
or lags: *is it your internet, your provider, or Valve's servers?*
- Six network checks in 10–20 s → whose side the problem is on → practical advice → a plain-text report
  for the provider.
- **Stack:** Python 3.15 · PySide6 (`pyside6-essentials`) for the window · standard library for all
  networking · uv · pytest · ruff.
- **Platforms:** Windows 10/11 fully supported; macOS and Linux run but are still in progress.
- **Names:** product, repo, package (`src/wholagged/`) and command are `wholagged`; `dota-netcheck` is a
  deprecated alias that keeps working. The UI and the User-Agent use `APP_NAME` (never hard-code it).
- **License:** PolyForm Noncommercial 1.0.0. The repo is **public**. External contributions will need a CLA.
- **Status:** v0.3.x. The road to 1.0 is in [TASKS.md](TASKS.md).

## Architecture

```
src/wholagged/
  __init__.py  entry point: GUI by default, --cli for the terminal; __version__, APP_NAME
  checks.py    the six checks (CHECKS) + run_checks(); standard library only
  icmp.py      ping: IcmpSendEcho via ctypes on Windows, the `ping` command elsewhere
  verdict.py   decide(): ordered rules → Verdict (side, headline, explanation, advice)
  report.py    plain-text report
  models.py    CheckResult, Verdict, Status, Side
  gui.py       PySide6 window, design tokens, CheckWorker (QThread)
  i18n.py      t(key, **params), get_language() / set_language(); lookup: language → en → key;
               Msg (a str that keeps key + params, for results and verdicts) and render() to show it again
  locales/     hy.py (source), ru.py, en.py: one MESSAGES dict each
tests/         offline tests; fakes.py (FakeNet) replaces the network
.claude/       agents/, skills/, hooks/, rules/, settings.json (Claude Code tooling, see below)
.github/       workflows/ci.yml (lint + tests), release.yml (PyPI, Trusted Publishing, on release: published)
TASKS.md · CHANGELOG.md · DECISIONS.md · README.md + README.hy.md (README.ru.md planned)
```

- `run_checks()` runs `CHECKS` in order and returns `{key: CheckResult}`; checks with several targets
  fan out with `checks.parallel()`.
- `decide(results)` → `Verdict`; `build_report(results, verdict)` → the text the user copies.
- The window runs the same flow in `CheckWorker` and updates its rows through Qt signals; `--cli` prints
  it without Qt.
- Qt lives only in `gui.py`: every other module must run without Qt, so `--cli` works without PySide6.

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

## The owner's rules (always follow)

1. **Python version = system Python.** `.python-version` and `requires-python` match the newest stable
   CPython on the system; upgrade together with it (`update-deps`). The SessionStart hook reports a mismatch.
   *Why:* one interpreter to maintain, and the project always gets the newest language and speed-ups.
2. **Dependencies first.** At the start of work, check all dependencies (the SessionStart hook does it);
   update what is outdated and adapt the code (`update-deps`).
   *Why:* small regular upgrades are cheap, late big ones break things and leave known holes open.
3. **Optimised code always.** No needless work, I/O or copies; bounded parallelism; no heavy dependency
   where the standard library is enough; nothing slow on the GUI thread.
   *Why:* the diagnosis must finish in 10–20 s and the window must never freeze.
4. **Never break what works.** New code must not break old code: existing commands, flags, check keys,
   `data` flags, the report layout and behaviour keep working. Tests stay green (the Stop hook runs them).
   *Why:* the verdict, the tests and users' reports depend on them.
5. **TASKS.md is the board.** Jira/Trello-style cards, as small as possible (`XS`/`S`). Every session:
   update and improve the cards, delete finished ones, add new work. It must always be current.
   *Why:* any session can pick up exactly where the last one stopped.
6. **Bugs are fixed now.** A bug found during a task is fixed in the same session, never filed as a card.
   Features and improvements go to TASKS.md. *Why:* filed bugs pile up and ship to users.
7. **After every task:** CHANGELOG entry, version bump, README update, and improve CLAUDE.md or the
   matching `.claude/rules/` file. All in **English** (`finish-task`).
   *Why:* the docs stay as current as the code.
8. **Commit and push after every task, without asking** (`finish-task`). Never force-push.
   *Why:* finished work is never lost; force-pushing rewrites published history.
9. **Security is a top priority.** *Why:* the repo is public and the app runs on players' PCs.
   - Never disable TLS verification; Valve's responses are untrusted input; no `shell=True`
     (`.claude/rules/checks.md`, `gui.md`).
   - The app collects and sends no user data. Keep it that way and say so in the privacy policy (WL-84).
   - No secrets in the repo: tokens, keys, certificates (`.pfx` signing files!) and `.env` are gitignored,
     and the guard hook scans every commit.
   - **The owner's private details** (business registration, tax and bank data, address, phone, email)
     never appear in the repo, commits, issues, PRs or requests to external services. The guard reads them
     from `~/.claude/private-patterns.txt` (outside the repo; never copy it in).
   - Keep business strategy, revenue numbers and partner names out of all files. Only what the README
     roadmap already says is public.
   - GitHub secret scanning, push protection and Dependabot alerts are on; `uv audit` runs in `update-deps`.
10. **Clean up after the push:** temp files, caches, scratch (`cleanup`).
    *Why:* junk in the tree ends up in commits and packages.
11. **Save GitHub Actions minutes.** Every workflow is minimal and budgeted (`ci-workflow`,
    `.claude/rules/ci.md`). Run lint and tests locally before every push, then check the run once.
    *Why:* the owner runs Actions in many repositories.
12. **Autonomy.** Always rely on yourself. Don't ask anyone or wait for an answer. Don't hand tasks to the
    user (don't ask them to do something by hand): do everything that needs doing yourself. If something is
    unclear, choose the most reasonable option, note it and why in
    [DECISIONS.md](DECISIONS.md), and carry on. *Why:* the owner wants work to move without them.
13. **Use the project's subagents, skills and hooks** (below). Subagents run on the session's model and
    effort: `model: inherit` and no `effort` field; keep it so for new agents.
    *Why:* they carry the project's checklists; a fixed model would silently differ from the session.
14. **Three languages by default: Armenian (hy), Russian (ru), English (en)** for everything the user sees.
    *Why:* the players are Armenian- and Russian-speaking, and English opens the app to everyone else.
    Details: `.claude/rules/i18n.md`, `docs.md`.
15. **Follow the project's design** and improve the UI/UX where possible; file larger UX ideas as `ux`
    cards. *Why:* one consistent look. Details: `.claude/rules/gui.md`.
16. **Web means Cloudflare.** Any web part (site, download page, privacy policy, API, update feed, licence
    server) is hosted on Cloudflare (Workers with static assets, D1/KV/R2, DNS, Registrar for domains).
    *Why:* one provider for hosting, data and domains.
17. **CLAUDE.md stays short:** about 200 lines, 400 at most.
    *Why:* it loads into every session in full; a long file eats context and its rules are followed worse.
    - Here: only these rules with the same numbers (what and why), the architecture and pointers.
    - Details (features, pitfalls of platforms and libraries, rules for one folder) go to
      `.claude/rules/*.md` with `paths:` in the frontmatter. `paths:` is required: a rules file without it
      loads in every session.
    - No `@` imports: an imported file loads at startup and saves nothing.
    - History ("since version X, task N") goes to CHANGELOG and git.
    - A new feature or pitfall goes into the matching rules file, not here.
    - `tests/test_claude_md.py` fails when CLAUDE.md is longer than 400 lines.
    - READMEs are short lists too, without long paragraphs.

## How a task runs

1. `start-task`: pick the top ready card (or a given `WL-id`), split it if bigger than `S`, move it to
   In Progress, check that tests and lint are green, plan.
2. Implement, following the matching `.claude/rules/` files. Use `test-engineer` for tests and `translator`
   for user-facing text; follow `add-check` for checks and verdict rules, and `ci-workflow` for `.github/`.
3. `finish-task`: verify → `code-reviewer` (+ `security-auditor` when relevant) → TASKS.md → version →
   CHANGELOG → READMEs → CLAUDE.md / rules → DECISIONS.md → commit → push + tag → `cleanup` → report.

## Where the details are

| Rules file (`.claude/rules/`) | Loads with | What is in it |
|---|---|---|
| `checks.md` | `checks.py`, `icmp.py`, `verdict.py`, `models.py`, `report.py` | check contract, blame rules, stable ids, network security |
| `gui.md` | `gui.py` | threads, design tokens, UX principles, smoke test |
| `i18n.md` | `src/wholagged/**/*.py`, `test_i18n.py` | `t()`, adding keys, tone and terms |
| `python.md` | `**/*.py`, `pyproject.toml` | Python 3.15 style, ruff |
| `packaging.md` | `pyproject.toml`, `uv.lock`, `.python-version`, `__init__.py` | version, names, uv pitfalls |
| `tests.md` | `tests/**` | FakeNet, scenarios, pytest pitfalls |
| `ci.md` | `.github/**` | what CI runs, budget, security |
| `claude-tooling.md` | `.claude/**`, `CLAUDE.md`, hook tests | hooks, agents, rules-file format |
| `docs.md` | READMEs, CHANGELOG, TASKS, DECISIONS | doc languages and style |

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
| hook | `session_start.py` | SessionStart: Python, deps, uv_build, leftovers, last CI run, CLAUDE.md size, next tasks |
| hook | `guard.py` | PreToolUse: blocks non-uv Python tooling, lost-work git commands, force pushes, dangerous deletes, running downloads, secrets and private data; asks before private data goes to an external tool |
| hook | `post_edit_lint.py` | PostToolUse: ruff on every edited `.py` file |
| hook | `stop_check.py` | Stop: tests + ruff if code, CLAUDE.md, rules or a README changed; reminds to ship unshipped work |
