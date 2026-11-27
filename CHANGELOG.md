# Changelog

All notable changes to wholagged are listed here, newest first.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/) (0.x until the 1.0 release).

## [0.3.7] - 2026-11-27

### Changed
- The window's buttons, row states, verdict chips, subtitle and "Details" toggles now come from the
  translation catalogue, like the checks, the verdict and the report before them. Every text the app
  shows is now ready to be translated. Everything reads exactly as before. (WL-26)
- For contributors: the tests now fail on any Armenian letter left in the app's code (outside the
  catalogues), and they find new modules by themselves. (WL-26)

## [0.3.6] - 2026-11-27

### Changed
- The labels of the copied report ("Time", "System", the verdict heading, whose side it is, "What to do")
  and of the `--cli` output now come from the translation catalogue. The report keeps its exact layout,
  and everything reads exactly as before. (WL-25)
- For contributors: `report.SIDE_LABELS` is replaced by `report.side_label(side)`, which returns the
  label in the current language. (WL-25)

## [0.3.5] - 2026-11-27

### Changed
- The verdict's headline, explanation and advice now come from the translation catalogue. A verdict
  remembers which texts it is made of, so it can later be shown again in another language without
  running the checks again. Everything reads exactly as before. (WL-24)

## [0.3.4] - 2026-11-27

### Changed
- The results of the Steam login server, Dota 2 Game Coordinator and Valve game network checks now come
  from the translation catalogue, and so do "skipped because there is no internet" and the "internal
  error" note. Like the first three checks, a finished result can later be shown again in another
  language. Everything reads exactly as before. (WL-23)

### Fixed
- A malformed relay list from Valve no longer crashes the game network check into "internal error".
  Relay addresses that can't be Valve's no longer mislead the verdict either. An address that doesn't
  answer used to blame your provider; your own PC or home router answered like a perfect relay. Such
  entries are skipped, so the check says it couldn't tell. (WL-23)
- A Steam login server list with unusable addresses (a malformed name, `localhost`, an odd port) no longer
  crashes the check or makes the verdict blame your provider; Steam's web servers are checked instead.
  (WL-23)
- When the game network check is skipped for any reason other than a blocked ping, the advice no longer
  says that your network blocks ICMP. (WL-23)
- Names and versions from Valve, and error messages from the system or a proxy, are shown as one short
  line of plain text, so a malformed answer can't add fake lines to the report you send your provider or
  send control codes to your terminal. (WL-23)
- A very long or deeply nested answer from Valve no longer slows the run or crashes a check. (WL-23)

## [0.3.3] - 2026-11-25

### Changed
- The results of the internet, DNS and Steam Web API checks, and the short error words such as
  "timeout", now come from the translation catalogue. Each result also remembers which text it is, so
  a finished check can later be shown again in another language without running it again. Everything
  reads exactly as before. (WL-22)

## [0.3.2] - 2026-11-25

### Changed
- The names and short descriptions of the six checks now come from the translation catalogue, so they
  can be shown in Russian and English once those translations exist. They read exactly as before.
  (WL-21)

## [0.3.1] - 2026-11-23

### Changed
- The READMEs are easier to scan: long paragraphs are now short lists, and version history moved out of
  them into this changelog. The app itself doesn't change. (WL-96)
- For contributors: `CLAUDE.md` is down to the project rules, the architecture and pointers (170 lines,
  was 235). The details now live in `.claude/rules/`, one file per topic, each loaded only when the files
  it covers are read. A new rule 17 keeps it that way, and a test fails if `CLAUDE.md` grows past 400
  lines or a rules file isn't scoped to existing files. (WL-96)

## [0.3.0] - 2026-11-22

### Added
- Translation support, the base for the Armenian, Russian and English interface: the app now has one
  catalogue of texts per language and is ready to switch between them. Nothing you see changes yet: the
  window stays in Armenian until its texts move into the catalogues and get their Russian and English
  versions. (WL-20)

## [0.2.4] - 2026-11-22

### Changed
- The READMEs (English and Armenian) now show the `wholagged` command, and the finished "one name
  everywhere" roadmap item is gone. (WL-14)

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

[0.3.7]: https://github.com/cholakhyanerik/wholagged/compare/v0.3.6...v0.3.7
[0.3.6]: https://github.com/cholakhyanerik/wholagged/compare/v0.3.5...v0.3.6
[0.3.5]: https://github.com/cholakhyanerik/wholagged/compare/v0.3.4...v0.3.5
[0.3.4]: https://github.com/cholakhyanerik/wholagged/compare/v0.3.3...v0.3.4
[0.3.3]: https://github.com/cholakhyanerik/wholagged/compare/v0.3.2...v0.3.3
[0.3.2]: https://github.com/cholakhyanerik/wholagged/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/cholakhyanerik/wholagged/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/cholakhyanerik/wholagged/compare/v0.2.4...v0.3.0
[0.2.4]: https://github.com/cholakhyanerik/wholagged/compare/v0.2.3...v0.2.4
[0.2.3]: https://github.com/cholakhyanerik/wholagged/compare/v0.2.2...v0.2.3
[0.2.2]: https://github.com/cholakhyanerik/wholagged/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/cholakhyanerik/wholagged/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/cholakhyanerik/wholagged/compare/v0.1.3...v0.2.0
[0.1.3]: https://github.com/cholakhyanerik/wholagged/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/cholakhyanerik/wholagged/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/cholakhyanerik/wholagged/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/cholakhyanerik/wholagged/releases/tag/v0.1.0
