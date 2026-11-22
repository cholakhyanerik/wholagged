**English** · [Հայերեն](README.hy.md)

# wholagged

[![CI](https://github.com/cholakhyanerik/wholagged/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/cholakhyanerik/wholagged/actions/workflows/ci.yml)
[![Python 3.15+](https://img.shields.io/badge/python-3.15%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows-0078D6?logo=windows&logoColor=white)](#requirements)
[![GUI: PySide6](https://img.shields.io/badge/GUI-PySide6-41CD52?logo=qt&logoColor=white)](https://doc.qt.io/qtforpython-6/)
[![License: PolyForm Noncommercial](https://img.shields.io/badge/license-PolyForm%20Noncommercial-blue)](LICENSE)
[![Sponsor](https://img.shields.io/badge/sponsor-GitHub%20Sponsors-EA4AAA?logo=githubsponsors&logoColor=white)](#support-the-project)

**Dota 2 is stuck on "Searching for Game Coordinator". Is the problem your internet, your provider, or Valve's servers?**

wholagged is a small desktop tool for Windows (macOS and Linux support is in progress) that answers that one question in about 10–20 seconds.
It runs six network checks, from basic connectivity to ping and packet loss on Valve's game relays,
and gives you a verdict on where the problem is, with steps to fix it.

> **Note:** the app's interface is in Armenian. An Armenian version of this README is available in [README.hy.md](README.hy.md).

## Features

- **One-click diagnosis.** Six checks run one after another, and the window updates as each one finishes.
- **A clear verdict.** The tool tells you whose side the problem is on (yours, your provider's, Valve's, or your PC / Steam client) and lists what to do next.
- **A report you can copy.** The *Copy report* button copies all results to the clipboard as plain text, headed by the app name and version, so you can send them to your ISP's support team as evidence.
- **No admin rights needed.** Ping uses the Windows `IcmpSendEcho` API directly, so there is no UAC prompt, no console window flashes up, and the results don't depend on the Windows language.
- **GUI or terminal.** The tool opens a PySide6 window by default, and `--cli` prints the same checks as text in the terminal.
- **Quick links** to [steamstat.us](https://steamstat.us/) and [isdown.app](https://isdown.app/status/dota-2), so you can compare with what other players are seeing.

## Requirements

- Windows 10 or 11 (for macOS and Linux, see [Platform support](#platform-support))
- [uv](https://docs.astral.sh/uv/) by Astral. **uv is required:** the project is managed only with uv
  (`pyproject.toml` + `uv.lock`). There is no `requirements.txt`, and `pip install` is not supported.
  uv also downloads Python 3.15 for you if you don't have it.

## Getting started

```powershell
git clone https://github.com/cholakhyanerik/wholagged.git
cd wholagged
uv sync
uv run dota-netcheck          # opens the window
```

Other commands:

```powershell
uv run dota-netcheck --cli    # runs in the terminal, no window
uv run pytest                 # runs the tests (offline, uses a fake network)
uv run ruff check             # lints the code
```

Updating an existing clone:

```powershell
git pull
uv sync
```

The project was renamed to wholagged in v0.2.2. If the old `dota-netcheck` command says "Failed to spawn"
after updating a clone from an older version, run `uv sync --reinstall-package wholagged` once. The new
`wholagged` command works either way.

## What it checks

| # | Check | How | What it tells you |
|---|---|---|---|
| 1 | Internet connection | TCP connection to port 443 on 1.1.1.1, 8.8.8.8 and 9.9.9.9 (plain IPs, no DNS) | Are you online at all? |
| 2 | DNS | Resolves `api.steampowered.com`, `steamcommunity.com` and `google.com` | Can your DNS find Steam? |
| 3 | Steam Web API | `ISteamDirectory/GetCMListForConnect` | Can you reach Valve, and does Valve answer normally? |
| 4 | Steam login servers | TCP connection to the 6 nearest connection manager (CM) servers | Can the Steam client log in? |
| 5 | Dota 2 Game Coordinator | `IGCVersion_570/GetServerVersion` | Is the GC answering? (indirect check) |
| 6 | Valve's game network | ICMP ping to Valve's SDR relays (from `GetSDRConfig`), then 10 pings to each of the 3 fastest | Ping, packet loss, jitter and routing problems |

If there is no internet, the remaining checks are skipped. If the CM server list can't be fetched, check 4 tests
Steam's web servers instead. If a check crashes, it is marked as skipped and the remaining checks still run.

## How the verdict is decided

The rules in [`verdict.py`](src/wholagged/verdict.py) are checked from top to bottom, and the first one that matches decides the verdict:

1. No internet → **your side**
2. DNS can't resolve Steam → **your side (DNS)**
3. HTTPS to Steam fails the certificate check → **your side** (wrong system clock, antivirus HTTPS scanning, a Wi-Fi login page or missing CA certificates; not your provider)
4. Valve answers with a 5xx error or an empty server list, or the GC reports `success=false` → **Valve's side**
5. The internet works, but no Steam server is reachable → **Valve or your provider** (check steamstat.us and try a phone hotspot)
6. Only some Steam servers are reachable → **provider, firewall or VPN**
7. Steam is reachable and 1.1.1.1 answers ping, but Valve's relays don't → **your provider's route to Valve**
8. Packet loss > 5%, ping > 150 ms or jitter > 30 ms → **connection quality**
9. Everything passes → **the network is fine; the problem is on your PC or in the Steam client**

Each verdict comes with practical advice, such as restarting the router, switching DNS to 1.1.1.1 / 8.8.8.8,
allowing `steam.exe` and `dota2.exe` through the firewall, testing over a phone hotspot, or verifying the game files.

## Limitations

- Checking the Game Coordinator directly would require logging in with a Steam account, so the tool checks it indirectly through the Web API.
  If that endpoint changes, the check is marked as skipped, and the tool does not blame Valve.
- The data endpoint behind steamstat.us is not a public API, and its owners ask people not to use it, so the tool only opens the site in your browser.
- If ICMP is blocked on your network, relay ping can't be measured, and that check is marked as skipped.

## Platform support

The goal is for the tool to run on Windows, macOS and Linux. For now, only Windows is fully supported.

| Platform | Status |
|---|---|
| Windows 10 / 11 | ✅ Fully supported |
| Linux | ⚠️ Runs, with known issues |
| macOS | ⚠️ Runs, not yet tested on a real Mac |

### Known issues (fixes planned)

- **macOS and Linux: ping uses the system `ping` command.** Since v0.1.1 it passes the timeout in the right unit
  (milliseconds on macOS, seconds on Linux) and runs in a neutral locale, so the output doesn't depend on the system
  language. A native implementation without the `ping` command, like the one on Windows, is planned.
- **Advice is Windows-specific.** Some tips mention Windows Firewall, `ipconfig /flushdns`, network adapter settings
  and `steam.exe` / `dota2.exe`. These don't apply on macOS or Linux.
- **No CI on macOS yet.** Every code push to `main` and every pull request that changes code is tested on
  Windows and Linux; a macOS run is planned. The tests use a fake network, so they don't cover the issues above.

### Minimum system versions

These come from the PySide6 wheels in `uv.lock`:

- macOS 14 Sonoma or newer
- Linux x86_64 with glibc 2.34+ (for example Ubuntu 22.04+, Debian 12+)
- Linux ARM64 with glibc 2.39+ (for example Ubuntu 24.04+)
- On Linux with X11, Qt also needs the `libxcb-cursor0` system package (`sudo apt install libxcb-cursor0` on Debian/Ubuntu)

## Project structure

```
src/wholagged/
  __init__.py   entry point (GUI by default, --cli for the terminal)
  checks.py     the six network checks (standard library only)
  icmp.py       ping on Windows via IcmpSendEcho (ctypes)
  verdict.py    turns the check results into a verdict
  report.py     plain-text report
  models.py     data classes: CheckResult, Verdict, Status, Side
  gui.py        PySide6 window
tests/
  fakes.py            fake network with switches to break each part
  test_scenarios.py   end-to-end scenarios: break one thing, expect one verdict
  test_parsing.py     parsing of Valve's API responses
  test_net_helpers.py HTTP error handling, the ping command, version sync
  test_claude_hooks.py the guard hook used by Claude Code in this repo
```

Development notes: planned work is in [TASKS.md](TASKS.md), the history of changes in [CHANGELOG.md](CHANGELOG.md),
and the rules for contributors and AI agents in [CLAUDE.md](CLAUDE.md).

## Roadmap

The checker is free for personal use, and all of its source code, including the future Pro version, will stay public.

Planned:

- **Cross-platform:** fix the [known issues](#known-issues-fixes-planned) and run the tests on macOS in CI too
  (Windows and Linux already run).
- **Your network vs your provider:** also ping your own router, so the tool can tell a bad Wi-Fi connection apart
  from a problem on your provider's side.
- **More Valve games:** CS2 and Deadlock use the same Valve relay network, so the same checks can cover them.
  The name wholagged isn't tied to any game, so it stays the same.
- **One name everywhere:** the window, the terminal output and the report already say wholagged (since v0.2.0).
  The Python package is `wholagged` too (since v0.2.1), and so is the command (since v0.2.2; `dota-netcheck`
  keeps working).
- **Background monitoring (paid Pro version):** record ping and packet loss for the whole day, show graphs,
  and build a PDF report you can send to your provider as evidence.
- **Microsoft Store** release.

### Transparency

In the future, the app may suggest a third-party service, such as a gaming route optimizer, and some of these
suggestions may be affiliate links. If that happens, these suggestions will:

- always be clearly marked as a recommendation and as an affiliate link;
- appear only when the verdict points to your provider's route or an unstable connection, where such a service can actually help;
- never appear when the problem is on Valve's side, on your Wi-Fi or on your PC;
- never change the verdict itself. The verdict logic is public in [`verdict.py`](src/wholagged/verdict.py), so anyone can check this.

## Support the project

If this tool saved you some frustration while waiting in the queue, you can support its development on GitHub Sponsors:

[![Sponsor on GitHub](https://img.shields.io/badge/Sponsor-%E2%9D%A4-EA4AAA?style=for-the-badge&logo=githubsponsors&logoColor=white)](https://github.com/sponsors/cholakhyanerik)

## License

wholagged is **source-available** under the [PolyForm Noncommercial License 1.0.0](LICENSE).
The code is public, but it is not open source in the OSI sense.

- ✅ **Free for noncommercial use:** personal use, gaming, hobby projects and study, and use by charities,
  schools and other noncommercial organizations. You may change the code and share it, as long as it stays
  noncommercial and comes with the license.
- ❌ **Commercial use requires a separate license from the author.** This includes selling the software or
  anything based on it, offering it as a paid service, and using it inside a business (for example, a computer club or an office).

For a commercial license, [open an issue](https://github.com/cholakhyanerik/wholagged/issues) or contact the author on GitHub.

## Disclaimer

Dota 2 and Steam are trademarks of Valve Corporation. This project is not affiliated with or endorsed by Valve.
