# Changelog

All notable changes to wholagged are listed here, newest first.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/) (0.x until the 1.0 release).

## [0.2.3] - 2026-11-22

### Changed
- Requests to Steam now identify the app as `wholagged/<version>` (they said `dota-netcheck/<version>`),
  and the Windows ping packet carries `wholagged` in its 32-byte payload. Nothing else about the
  checks changes. (WL-13)

## [0.2.2] - 2026-11-22

### Added
- A `wholagged` command: `uv run wholagged` opens the window, `uv run wholagged --cli` runs in the
  terminal. (WL-12)

### Changed
- The project is now named `wholagged` (it was `dota-netcheck`). If, in a clone made before v0.2.2,
  `uv run dota-netcheck` says "Failed to spawn" after an update, run
  `uv sync --reinstall-package wholagged` once; a plain `uv sync` right after `git pull` avoids it. (WL-12)

### Deprecated
- The `dota-netcheck` command. It still works exactly as before and starts the same app; use `wholagged`
  instead. (WL-12)

### Security
- Builds also leave out `.dev.vars`, `.pypirc`, `.npmrc`, `.netrc` and SSH key files, matching
  `.gitignore` and the guard hook. (WL-12)

## [0.2.1] - 2026-11-22

### Changed
- The Python package is renamed from `dota_netcheck` to `wholagged` (`src/wholagged/`). The
  `dota-netcheck` command works exactly as before. `python -m dota_netcheck` is now
  `python -m wholagged`, and code that imported `dota_netcheck` must import `wholagged`. (WL-11)

### Fixed
- Armenian README: four article and case-ending slips ("կոճակն", "clipboard-ում", "uv-ն", "Tool-ն"). (WL-11)

### Security
- Builds leave out secret and junk files even if one is dropped into `src/` (`.env*`, `.pem`, `.key`,
  `.pfx`, `.p12`, temp and backup files): uv_build doesn't read `.gitignore`. (WL-11)

## [0.2.0] - 2026-11-22

### Changed
- The app is now called **wholagged** everywhere you see it: the window title, the header, the terminal
  output and the copied report (it was "Dota 2 Network Check"). The subtitle says the app checks your
  Dota 2 connection. (WL-10)
- The report and the terminal output now start with the app version and the game (`wholagged 0.2.0 · Dota 2`), so a pasted
  report shows which version produced it. (WL-10)

## [0.1.3] - 2026-11-22

### Added
- CI now also runs the tests on Windows, the main platform, next to Linux. If one platform fails, the
  other job stops at once. (WL-2)

### Changed
- CI lints only on Linux (the result doesn't depend on the OS) and no longer keeps a uv cache: on Linux a fresh
  install took 2 s, saving the cache took 4 s, and every version bump made the cache unusable anyway.
  (WL-2)

## [0.1.2] - 2026-11-22

### Added
- Continuous integration: every push to `main` and every pull request that changes code, tests, the
  dependencies or the Python version is linted (ruff) and tested (pytest) on Linux. Docs-only changes and
  tag pushes don't start it. A CI badge is in the README. (WL-1)

### Security
- The workflow has read-only repository access, pins its actions to full commit SHAs, doesn't keep the
  checkout token and installs a checksum-verified uv. (WL-1)

### Development
- The `ci-workflow` skill's trigger list now also covers `.claude/hooks/**` (the guard hook has tests) and
  `.python-version`. The skill now requires a checksum-verified uv tied to the `setup-uv` pin, and leaves
  the uv cache on its default (`auto`), with no cache in release or signing jobs. (WL-1)

## [0.1.1] - 2026-11-22

### Fixed
- macOS: the relay ping check no longer always fails. The system `ping` now gets its timeout in
  milliseconds on macOS (it was given 1, which macOS reads as 1 ms) and in seconds on Linux.
- macOS and Linux: `ping` runs in a neutral locale, so reading its output no longer depends on the
  system language.
- An HTTPS certificate failure towards Steam is no longer blamed on your provider. It now gets its own
  verdict ("your side") with advice: check the system clock, turn off the antivirus HTTPS scanning, log
  in on the Wi-Fi page, install CA certificates on macOS.
- A TLS handshake that is cut off, for example by a provider's filter, is not mistaken for a certificate
  problem. Only a rejected certificate gives the new verdict, and the report shows the reason.
- A connection that drops while Valve's answer is being read now counts as a failed request instead of
  ending the check as an internal error.
- The HTTP User-Agent now carries the real app version instead of a fixed `0.1`.

### Changed
- Jitter is computed with `itertools.pairwise` (same result, no list copy).

### Security
- Dependabot vulnerability alerts are enabled for the repository (secret scanning and push protection
  were already on).
- ruff now also runs the flake8-bandit security rules.
- Text that comes from Valve's API is always shown as plain text in the window, never as rich text.
- Answers from Valve larger than 4 MB are refused, and the login-server list is type-checked before use.
- Ping accepts only a strict IPv4 address, so a malformed relay address from the API is ignored.

### Dependencies
- `uv lock --upgrade`: all packages were already at their latest versions (PySide6 6.12.0,
  pytest 9.2.0); `uv audit` reports no known vulnerabilities.
- Build backend range raised to `uv_build>=0.13.9,<0.14.0` to match uv 0.13.
- New dev dependency: `ruff` 0.17.6.

### Development
- `CLAUDE.md` with the project rules, `TASKS.md` with the v1.0 board, `DECISIONS.md`, and this changelog.
- Claude Code tooling in `.claude/`: subagents (code-reviewer, security-auditor, translator,
  test-engineer), skills (start-task, finish-task, update-deps, cleanup, add-check, ci-workflow) and hooks
  (session status, security and uv guard, lint on edit, tests before stopping).
- Tests for all fixes above and for the guard hook (24 → 118 tests). pytest no longer creates a
  `.pytest_cache` folder.

## [0.1.0] - 2026-11-22

### Added
- First version: six network checks (internet, DNS, Steam Web API, Steam login servers, Dota 2 Game
  Coordinator, Valve relays with ping, packet loss and jitter), a verdict on whose side the problem is
  with practical advice, a copyable report, a PySide6 window and a `--cli` mode. Armenian interface.
- License: PolyForm Noncommercial 1.0.0.

[0.2.3]: https://github.com/cholakhyanerik/wholagged/compare/v0.2.2...v0.2.3
[0.2.2]: https://github.com/cholakhyanerik/wholagged/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/cholakhyanerik/wholagged/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/cholakhyanerik/wholagged/compare/v0.1.3...v0.2.0
[0.1.3]: https://github.com/cholakhyanerik/wholagged/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/cholakhyanerik/wholagged/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/cholakhyanerik/wholagged/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/cholakhyanerik/wholagged/releases/tag/v0.1.0
