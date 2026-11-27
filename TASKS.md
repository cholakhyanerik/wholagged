# TASKS

The task board for **wholagged**, kept like a Jira/Trello board. It is updated in every session
([CLAUDE.md](CLAUDE.md) rule 5): a finished card is deleted (its history goes to
[CHANGELOG.md](CHANGELOG.md)), new work is added as small cards, and the order of **To Do** is the
priority order.

**Card format:** `### WL-<id> · <title>`, then `type · priority · size · epic · depends on`, one line
on why, and acceptance criteria.
Types: `feature` `ux` `chore` `test` `ci` `docs` `security`. Priority: `P1` needed for v1.0, `P2`
should be in v1.0, `P3` nice to have. Size: `XS` ≤ 30 min, `S` ≤ 2 h. Bigger cards are split before
work starts. Bugs are never filed here: they are fixed in the session that finds them.

## Milestone v1.0: wholagged 1.0 on the Microsoft Store

Definition of done:
- the app, the package and the command are called **wholagged**;
- the UI, the verdicts and the report are available in **Armenian, Russian and English**, picked from
  the OS and switchable;
- it tells a **Wi-Fi / router** problem apart from a **provider** problem (gateway ping);
- it covers **Dota 2, CS2 and Deadlock**;
- it runs on Windows 10/11, and on macOS/Linux with native ping and per-platform advice;
- CI runs on every code push (cheaply) and is green on Windows and Linux;
- it is published on the **Microsoft Store** with an AM/RU/EN listing and a privacy policy page.

Epics: `CI` · `BRAND` · `I18N` · `XPLAT` · `NET` · `GAMES` · `UX` · `STORE` · `QUALITY`

---

## In Progress

_Nothing in progress._

---

## To Do

### WL-105 · First upload of `dota-netcheck`, then let the READMEs use the old name
`security` · `P1` · `XS` · BRAND · depends on: WL-102
`release.yml` builds and uploads the `dota-netcheck` package (WL-102), but PyPI accepts it only after the
owner adds a pending publisher (their login, like WL-101). Until then a release uploads wholagged and its
last step fails.
- [ ] the owner adds the pending publisher on https://pypi.org/manage/account/publishing/: PyPI project
      `dota-netcheck`, owner `cholakhyanerik`, repository `wholagged`, workflow `release.yml`, environment `pypi`
- [ ] the release follows the same day: a pending publisher doesn't reserve the name, only the first upload
      does. `gh release create vX.Y.Z --verify-tag` on a task's tag; both packages are on PyPI, and
      `uvx dota-netcheck --cli` from a scratch tool folder runs the checks
- [ ] `https://pypi.org/pypi/dota-netcheck/json` lists the same owner account as wholagged's (`ownership`)
      and no one else; if someone else took the name, the READMEs keep `--from wholagged`
- [ ] `ALLOWED` in `tests/test_docs.py` lists the old name without `--from wholagged` (uvx only: two uv
      tools can't share the `dota-netcheck` command); the READMEs (en/hy) drop the "needs
      `--from wholagged`" bullet; `release.yml`'s "Refused until" comment, `.claude/rules/packaging.md`
      and `ci.md` no longer say it isn't uploaded

### WL-104 · Keep PyPI installs on a tested Qt
`security` · `P2` · `XS` · QUALITY · depends on: —
Found in the WL-103 audit: `uvx` and `uv tool install` ignore `uv.lock`, so players get the newest
`pyside6-essentials` / `shiboken6` on PyPI before CI or `uv audit` has seen them.
- [ ] decide: an upper bound (e.g. `<6.13`, raised on purpose in `update-deps`) or no bound; log it in
      DECISIONS
- [ ] if bounded: `update-deps` raises it together with the lock, and `.claude/rules/packaging.md` says so

---

## Backlog (v1.0)

### WL-3 · macOS job on pull requests and manual runs only
`ci` · `P2` · `XS` · CI · depends on: WL-1
macOS minutes are the most expensive, so not on every push.
- [ ] a `macos-latest` job on `pull_request` / `workflow_dispatch` only, green

### WL-4 · Dependabot for GitHub Actions versions (monthly, grouped)
`security` · `P2` · `XS` · CI · depends on: WL-1
- [ ] `.github/dependabot.yml`: `github-actions` ecosystem, monthly, one grouped PR

### WL-5 · Harden the repo's Actions settings
`security` · `P2` · `XS` · CI · depends on: WL-1
Found in the WL-1 audit: after one merged PR, a contributor's next PR can rewrite `ci.yml` and run without
approval, and SHA pinning is a convention, not enforced.
- [ ] fork PR approval policy `all_external_contributors`
- [ ] `sha_pinning_required: true`, after checking that GitHub's own "Dependency Graph" runs still succeed
- [ ] a tag ruleset for `v*`: no deletion, no force update, and only the Repository admin role may create
      them (bypass), so task tags still work. The `pypi` environment trusts these tag names (WL-15 audit)
- [ ] immutable releases on (`gh api -X PUT repos/cholakhyanerik/wholagged/immutable-releases`), so a
      published release's tag can't be moved (WL-15 audit)
- [ ] settings listed in CLAUDE.md rule 9 and `.claude/rules/ci.md`

### WL-27 · English catalogue
`feature` · `P1` · `S` · I18N · depends on: WL-21 … WL-26
- [ ] every key translated by the `translator` subagent; reads naturally
- [ ] counts (`{count}`, `{ok}/{total}`) are worded so they read right for any number: `t()` has no plurals

### WL-28 · Russian catalogue
`feature` · `P1` · `S` · I18N · depends on: WL-21 … WL-26
- [ ] every key translated by the `translator` subagent; informal `ты`, common gamer terms
- [ ] counts (`{count}`, `{ok}/{total}`) are worded so they read right for any number: `t()` has no plurals

### WL-29 · Test that the three catalogues are complete
`test` · `P1` · `XS` · I18N · depends on: WL-27, WL-28
- [ ] same key set in hy/ru/en (tests/test_i18n.py already checks placeholders against hy and empty texts)

### WL-30 · Pick the language from the OS locale
`feature` · `P1` · `XS` · I18N · depends on: WL-29
- [ ] `hy*` → hy; `ru`, `be`, `kk`, `ky` → ru; anything else → en; unit tests

### WL-31 · `--lang hy|ru|en` command-line option
`feature` · `P2` · `XS` · I18N · depends on: WL-30
- [ ] works for `--cli` and for the window; invalid value prints the allowed ones

### WL-32 · Language switcher in the window header
`ux` · `P1` · `S` · I18N · depends on: WL-30
- [ ] ՀԱՅ / РУС / ENG control in the header, styled like the existing buttons
- [ ] switching updates every visible text without restarting a check: static texts with `t()`, a finished
      run's rows and verdict with `i18n.render()` (results are `Msg`, DECISIONS 2026-11-25)
- [ ] a result or verdict that arrives after a switch, made in the old language mid-run, is shown through
      `i18n.render()` too (WL-22 review)
- [ ] the advice (rich text) is rendered first and escaped after: `_html(render(a))` (WL-24 review)
- [ ] row state words, the chip and the Details toggle are plain `t()` strings, not `Msg`: set them again
      from `res.status` / `verdict.side` / the toggle's state (WL-26 review)

### WL-33 · Remember the chosen language
`ux` · `P2` · `XS` · I18N · depends on: WL-32
- [ ] stored with `QSettings`; an explicit `--lang` wins over the stored value

### WL-34 · Report in the UI language, with app version and language in the header
`feature` · `P2` · `XS` · I18N · depends on: WL-25
- [ ] `build_report()` renders titles, summaries, details and the verdict with `i18n.render()`, so a run
      made in one language is copied in the language shown now

### WL-35 · Russian README and language links in all READMEs
`docs` · `P1` · `S` · I18N · depends on: WL-27
- [ ] `README.ru.md` mirrors README.md; the language bar in all three files lists English · Հայերեն · Русский
- [ ] the "interface is in Armenian" note is replaced by the list of UI languages

### WL-40 · Per-platform advice (Windows / macOS / Linux)
`feature` · `P2` · `S` · XPLAT · depends on: WL-24
- [ ] firewall, DNS-flush, adapter and process-name tips have macOS and Linux variants; tests per platform
- [ ] README known issue "Advice is Windows-specific" removed

### WL-41 · Native unprivileged ICMP on Linux and macOS
`feature` · `P2` · `S` · XPLAT · depends on: —
No `ping` subprocess and no output parsing.
- [ ] `SOCK_DGRAM` + `IPPROTO_ICMP` echo with timeout; falls back to the `ping` command when the OS
      refuses (Linux `net.ipv4.ping_group_range`)

### WL-42 · Unit tests for the ICMP echo packet (build, checksum, parse)
`test` · `P2` · `XS` · XPLAT · depends on: WL-41

### WL-43 · Update the platform table and known issues after XPLAT
`docs` · `P2` · `XS` · XPLAT · depends on: WL-40, WL-41, WL-3

### WL-50 · Find the default gateway (router) address
`feature` · `P1` · `S` · NET · depends on: —
Needed to separate Wi-Fi/router problems from provider problems.
- [ ] Windows: `GetBestRoute2` / `GetIpForwardTable2` via ctypes; Linux: `/proc/net/route`;
      macOS: `route -n get default` (fixed argv); `None` when unknown; unit tests with sample data

### WL-51 · New check "Home network": ping, loss and jitter to the router
`feature` · `P1` · `S` · NET · depends on: WL-50
- [ ] runs before the relay check; SKIP (not FAIL) when the router ignores ping; FakeNet knob

### WL-52 · Verdict rules for the home network
`feature` · `P1` · `S` · NET · depends on: WL-51
- [ ] loss/jitter already at the router → **your Wi-Fi / home network**; clean router but lossy relays →
      **provider**; scenario tests for both; README verdict list updated

### WL-53 · Time the Steam CM connection without the DNS lookup
`chore` · `P3` · `XS` · NET · depends on: —
- [ ] resolve first, then time only `connect()`; same fallback over all addresses as today

### WL-54 · Reuse one ICMP handle per thread on Windows
`chore` · `P3` · `XS` · NET · depends on: —
- [ ] `IcmpCreateFile` once per worker thread instead of once per ping; same results

### WL-98 · Never follow a redirect out of HTTPS
`security` · `P2` · `XS` · NET · depends on: —
Found in the WL-23 audit: `urlopen`'s default opener follows a 3xx from Valve's https URL to `http://` or
`ftp://`, after which anyone on the path controls the JSON.
- [ ] one module-level opener whose redirect handler refuses any target that isn't `https` (the 3xx then
      becomes `HttpFailure` with its status); https → https redirects still work
- [ ] unit tests for the handler; TLS verification and timeouts unchanged

### WL-99 · Total deadline for each HTTP request and DNS lookup
`security` · `P2` · `S` · NET · depends on: —
Found in the WL-23 audit: `timeout=` applies to each socket call, so a middlebox trickling a segment every
few seconds keeps `resp.read()` going far past `HTTP_TIMEOUT_S`, and `getaddrinfo` has no timeout at all.
- [ ] `http_get_json` reads in chunks against a monotonic deadline and raises `HttpFailure(error.timeout)`
- [ ] DNS lookups (`_resolve`, `tcp_probe`) give up after a bounded time without blocking the run
- [ ] the run stays within 10–20 s with a trickling fake server; offline tests

### WL-100 · Probe a Steam login server only at public addresses
`security` · `P3` · `XS` · NET · depends on: WL-53
Found in the WL-23 audit: `_host()` refuses `localhost` and numeric tricks, but a real DNS name can still
resolve to 127.0.0.1 or a LAN address, where the Steam client's own ports would answer.
- [ ] resolve each CM host once (with WL-53) and connect only to addresses that pass `_ipv4()`; a host with
      none counts as unusable, like a malformed one

### WL-60 · Game model: Dota 2, CS2, Deadlock
`feature` · `P2` · `S` · GAMES · depends on: WL-11
- [ ] a `Game` record (name, appid 570 / 730 / 1422450, SDR and GC URLs); Dota 2 stays the default

### WL-61 · Relay list and GC check for the selected game
`feature` · `P2` · `S` · GAMES · depends on: WL-60
- [ ] `GetSDRConfig?appid=<game>`; the GC check is SKIP for a game without a public GC endpoint

### WL-62 · Game selector in the window and `--game` in the CLI
`ux` · `P2` · `S` · GAMES · depends on: WL-61
- [ ] `--game dota2|cs2|deadlock`; a selector in the header next to the language switcher

### WL-63 · Game-specific advice texts in three languages
`feature` · `P2` · `S` · GAMES · depends on: WL-62, WL-29
- [ ] "verify game files", process names and launch options per game

### WL-70 · Keyboard shortcuts
`ux` · `P2` · `XS` · UX · depends on: —
- [ ] Enter starts / restarts the check, Ctrl+Shift+C copies the report; shown in button tooltips

### WL-71 · Show elapsed seconds while checking
`ux` · `P3` · `XS` · UX · depends on: —

### WL-72 · Accessible names for status dots and buttons
`ux` · `P2` · `XS` · UX · depends on: WL-26
- [ ] `setAccessibleName` / `setAccessibleDescription` so a screen reader reads each row's status

### WL-73 · Minimum window size and High-DPI check
`ux` · `P2` · `XS` · UX · depends on: —
- [ ] nothing is cut off at 125 % and 150 % scaling or at the minimum size

### WL-74 · "Save report" to a text file
`ux` · `P2` · `XS` · UX · depends on: —

### WL-75 · About dialog
`ux` · `P2` · `XS` · UX · depends on: WL-10
- [ ] version, license (noncommercial), GitHub and Sponsors links

### WL-76 · App icon
`ux` · `P1` · `S` · UX · depends on: WL-10
- [ ] `.ico` and PNG sizes for the window, taskbar and Store; matches the accent colour `#c8402e`

### WL-80 · Choose the Windows freezer (PyInstaller, Nuitka or Briefcase)
`chore` · `P1` · `XS` · STORE · depends on: —
- [ ] decision with size, start-up time and antivirus false-positive risk logged in DECISIONS.md

### WL-81 · Local Windows build that starts without uv or Python
`chore` · `P1` · `S` · STORE · depends on: WL-80
- [ ] one-folder build, GUI and `--cli` work on a clean Windows user account

### WL-82 · MSIX package
`chore` · `P1` · `S` · STORE · depends on: WL-81, WL-76
- [ ] manifest with only the `internetClient` capability, visual assets, installs and runs locally

### WL-83 · Release workflow
`ci` · `P1` · `S` · STORE · depends on: WL-82, WL-2
- [ ] builds the MSIX on `release: published` or `workflow_dispatch` only (not on every tag);
      artifact `retention-days: 3`

### WL-84 · Privacy policy page on Cloudflare
`docs` · `P1` · `S` · STORE · depends on: —
- [ ] static page in AM/RU/EN ("the app collects no data") on Cloudflare (Workers static assets),
      security headers set; URL ready for the Store listing
- [ ] any install command on the site's pages goes through the same reviewed list as the READMEs
      (`tests/test_docs.py`, WL-103 audit)

### WL-85 · Store listing texts and screenshots in AM/RU/EN
`docs` · `P1` · `S` · STORE · depends on: WL-35, WL-32

### WL-86 · `--version` command-line option
`feature` · `P3` · `XS` · STORE · depends on: —

### WL-90 · Decide on `ruff format`
`chore` · `P3` · `XS` · QUALITY · depends on: WL-1
- [ ] either one reformat commit plus a format check in CI, or a logged decision not to

### WL-91 · Type checking with `ty` (Astral)
`chore` · `P3` · `S` · QUALITY · depends on: WL-1
- [ ] `ty check` clean; added to CI and to the Stop hook

### WL-92 · Headless GUI smoke test in pytest
`test` · `P2` · `XS` · QUALITY · depends on: —
- [ ] `QT_QPA_PLATFORM=offscreen`, builds `MainWindow`, runs a check against `FakeNet`, sees the verdict card
- [ ] asserts `windowTitle()` and the `title` label equal `APP_NAME` (WL-10 checked this only by hand)
- [ ] asserts the Armenian row states, the "Details ▸ / ▾" toggle, the chips and "Պատճենվեց ✓": the code
      adds the ▸ / ▾ / ✓, and only the words are tested so far (WL-26)
- [ ] passes in CI: on `ubuntu-latest` Qt needs `libegl1` and `libxkbcommon0` (install them in `ci.yml`, or
      skip the test cleanly when Qt can't load)

### WL-95 · Test the Windows ctypes ping on the Windows runner
`test` · `P2` · `XS` · QUALITY · depends on: —
Found in WL-2: CI runs on Windows, but FakeNet replaces `icmp.ping`, so `_ping_windows` (`IcmpSendEcho`)
is never executed by any test.
- [ ] a Windows-only test (`skipif` elsewhere) loads `iphlpapi.dll` via `_load_iphlpapi()` and pings
      `127.0.0.1` through `_ping_windows`, getting a number; loopback only, so the suite stays offline
      (hosted runners block outbound ICMP). If loopback ICMP fails on the runner, check the reply parsing
      with a fake reply buffer instead
- [ ] a timeout or unreachable reply returns `None`, not an exception

### WL-97 · Test that the translated READMEs keep the English structure
`test` · `P3` · `XS` · QUALITY · depends on: —
README changes are mirrored by hand (the `translator` subagent); nothing catches a missed section or list.
Found in WL-96.
- [ ] a test compares `README.md` with `README.hy.md` (and `README.ru.md` once it exists): the same
      number of `##` / `###` headings, table rows, code blocks and links, and identical code blocks
- [ ] passes on the current files

### WL-93 · SECURITY.md
`security` · `P2` · `XS` · QUALITY · depends on: —
- [ ] how to report a vulnerability privately (GitHub private vulnerability reporting enabled)

### WL-94 · CONTRIBUTING.md with a CLA
`docs` · `P2` · `S` · QUALITY · depends on: —
External contributions need a CLA so commercial licences can still be sold.
- [ ] contribution rules (uv, tests, languages) and the CLA text; PR template checkbox

---

## Later (after v1.0)

Epics that get split into cards when they are pulled into a milestone.

- **PRO · Background monitoring (paid).** Ping and loss to relays and the router all day, local storage,
  graphs, and a PDF report for the provider.
- **AFF · Recommendations.** Optional third-party suggestion, only for provider-route or packet-loss
  verdicts, clearly marked as a recommendation and an affiliate link, with tests proving it never changes
  the verdict (README → Transparency).
- **IPv6** checks next to IPv4.
- **Light theme** that follows the OS.
- **Cancel** button for a running check.
