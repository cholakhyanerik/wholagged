**English** · [Հայերեն](README.hy.md)

# Dota 2 Network Check

[![Python 3.15+](https://img.shields.io/badge/python-3.15%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows-0078D6?logo=windows&logoColor=white)](#requirements)
[![GUI: PySide6](https://img.shields.io/badge/GUI-PySide6-41CD52?logo=qt&logoColor=white)](https://doc.qt.io/qtforpython-6/)
[![Sponsor](https://img.shields.io/badge/sponsor-GitHub%20Sponsors-EA4AAA?logo=githubsponsors&logoColor=white)](#support-the-project)

**Dota 2 is stuck on "Searching for Game Coordinator". Is the problem your internet, your provider, or Valve's servers?**

Dota 2 Network Check is a small Windows desktop tool that answers that one question in about 10–20 seconds.
It runs six network checks, from basic connectivity to ping and packet loss on Valve's game relays,
and gives you a verdict on where the problem is, with steps to fix it.

> **Note:** the app's interface is in Armenian. An Armenian version of this README is available in [README.hy.md](README.hy.md).

## Features

- **One-click diagnosis.** Six checks run one after another, and the window updates as each one finishes.
- **A clear verdict.** The tool tells you whose side the problem is on (yours, your provider's, Valve's, or your PC / Steam client) and lists what to do next.
- **A report you can copy.** The *Copy report* button copies all results to the clipboard as plain text, so you can send them to your ISP's support team as evidence.
- **No admin rights needed.** Ping uses the Windows `IcmpSendEcho` API directly, so there is no UAC prompt, no console window flashes up, and the results don't depend on the Windows language.
- **GUI or terminal.** The tool opens a PySide6 window by default, and `--cli` prints the same checks as text in the terminal.
- **Quick links** to [steamstat.us](https://steamstat.us/) and [isdown.app](https://isdown.app/status/dota-2), so you can compare with what other players are seeing.

## Requirements

- Windows 10 or 11
- [uv](https://docs.astral.sh/uv/) (it downloads Python 3.15 for you if you don't have it)

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
```

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

The rules in [`verdict.py`](src/dota_netcheck/verdict.py) are checked from top to bottom, and the first one that matches decides the verdict:

1. No internet → **your side**
2. DNS can't resolve Steam → **your side (DNS)**
3. Valve answers with a 5xx error or an empty server list, or the GC reports `success=false` → **Valve's side**
4. The internet works, but no Steam server is reachable → **Valve or your provider** (check steamstat.us and try a phone hotspot)
5. Only some Steam servers are reachable → **provider, firewall or VPN**
6. Steam is reachable and 1.1.1.1 answers ping, but Valve's relays don't → **your provider's route to Valve**
7. Packet loss > 5%, ping > 150 ms or jitter > 30 ms → **connection quality**
8. Everything passes → **the network is fine; the problem is on your PC or in the Steam client**

Each verdict comes with practical advice, such as restarting the router, switching DNS to 1.1.1.1 / 8.8.8.8,
allowing `steam.exe` and `dota2.exe` through the firewall, testing over a phone hotspot, or verifying the game files.

## Limitations

- Checking the Game Coordinator directly would require logging in with a Steam account, so the tool checks it indirectly through the Web API.
  If that endpoint changes, the check is marked as skipped, and the tool does not blame Valve.
- The data endpoint behind steamstat.us is not a public API, and its owners ask people not to use it, so the tool only opens the site in your browser.
- If ICMP is blocked on your network, relay ping can't be measured, and that check is marked as skipped.
- Only Windows is fully supported. On other systems, ping falls back to the system `ping` command, which is meant for development only.

## Project structure

```
src/dota_netcheck/
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
```

## Support the project

If this tool saved you some frustration while waiting in the queue, you can support its development on GitHub Sponsors:

[![Sponsor on GitHub](https://img.shields.io/badge/Sponsor-%E2%9D%A4-EA4AAA?style=for-the-badge&logo=githubsponsors&logoColor=white)](https://github.com/sponsors/cholakhyanerik)

## Disclaimer

Dota 2 and Steam are trademarks of Valve Corporation. This project is not affiliated with or endorsed by Valve.
