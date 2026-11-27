# Decisions

Decisions taken without asking ([CLAUDE.md](CLAUDE.md) rule 12), newest first.
Each entry: the decision, then why. Revisit an entry by adding a new one; don't rewrite history.

## 2026-11-27

- **The first PyPI upload is v0.3.8, released as it was tagged (WL-101).** It is the first tag whose
  commit has `release.yml`, it passed CI, and a release of an existing tag needs no new version. The name
  was free until then, so the sooner the better. Installing it from PyPI in a clean environment worked:
  both commands are there, and the window module imports.
- **READMEs don't tell users to install from PyPI yet (WL-101).** That is a docs change in two languages
  with its own wording (WL-103), and the alias needs care until WL-102 reserves `dota-netcheck`.

- **WL-15 is split: this repo's side is done, and the first upload is WL-101 (WL-15).** PyPI's docs say a
  pending publisher "does not create a project or reserve a project's name until it is actually used to
  publish", and someone else registering the name first invalidates it. So only a first release reserves
  `wholagged`. Adding the pending publisher needs the owner's PyPI login (there is no API for it). That
  is the one step no session can do, and WL-101 lists the exact form values. Both names were still free on
  PyPI on this date.
- **Build and publish are two jobs, and only publish has `id-token: write` (WL-15).** The OIDC permission
  never reaches the checkout or the build. The publish job uploads the build job's artifact, which
  download-artifact checks by digest. `uv publish --trusted-publishing always` fails rather than fall back to
  a token. The build runs `--offline`, so only uv's bundled `uv_build` can build, and nothing is fetched
  while it does.
- **`uv publish`, not `pypa/gh-action-pypi-publish` (WL-15).** uv is already in every job, and it saves one
  more third-party action to pin and trust. The PyPA action would also make PEP 740 attestations; that can
  be added later if verified provenance on PyPI is wanted.
- **`workflow_dispatch` on `release.yml` only builds (WL-15).** It is the dry run that validates the
  workflow and the package. The publish job runs only for `release: published`, and the `pypi`
  environment accepts only `v*` tags.
- **No required reviewers on the `pypi` environment (WL-15).** The owner works alone, and publishing a
  release already needs write access. A reviewer gate would turn every release into a manual step for the
  owner (rule 12). WL-5 hardens who may create `v*` tags instead.
- **`dota-netcheck` isn't reserved in WL-15 (WL-15).** No doc ever told users to install it from PyPI
  (checked across git history). Reserving it needs a second, alias package, so it is its own card
  (WL-102) after the first release.

- **The window's row states are `status.<status>` (plus `status.running`), its other texts `gui.<what>`
  (WL-26).** `status.*` mirrors `side.*`: one key per enum member, read as `t(f"status.{status}")`. Because
  the key scan can't see a key built at run time, a test checks the catalogue has one for every member.
  The row's "Checking…" and the button's "Checking…" are two keys (`status.running`, `gui.running`). They
  read the same in Armenian, but Russian words them differently ("Проверяется…" / "Проверяю…").
- **The ▸ / ▾ of "Details" and the ✓ of "Copied" stay in code, not in the texts (WL-26).** They are
  layout, like the report's ": ", and one `gui.details` key then serves both states of the toggle.
- **The window's "What to do" reuses `report.advice` (WL-26),** as the card suggested: it was the same word
  in the window and in the report, and one key keeps them in step.
- **The Armenian-letter test scans every module of the package, not a hand-kept list (WL-26).** All move
  cards are done, so a list could only fall behind. A new module is checked without anyone adding it.
  The scan reads files as text: importing `gui.py` would need Qt's system libraries on the Linux runner
  (the GUI smoke test is WL-92).

- **The report's keys are the labels only ("Ժամանակ", "Ում կողմից"); the code adds ": " and the value
  (WL-25).** People send the report to their provider, so its layout must not change with a translation
  (rule 4). A whole-line template such as "Time: {time}" would let a translator move or drop the
  value. The CLI prints the verdict with the same `report.*` labels, so the terminal and the copied report
  read the same, and the translator writes them once.
- **`SIDE_LABELS` became `SIDE_KEYS` plus `side_label(side)` (WL-25).** A dict of rendered strings would
  freeze the language at import. Only `run_cli()` used it, and it is not one of the stable identifiers.
  `side_label()` keeps the old fallback: a side it doesn't know is shown as it is.
- **The report and the CLI use `t()`, not `Msg` (WL-25).** Their text is built and used at once, in
  the current language. Showing a finished run's results in the report in the current language is WL-34
  (`render()`), unchanged.
- **The product line "wholagged <version> · Dota 2" stays in code, not in the catalogue (WL-25).** It has
  no words to translate, and tests and users' reports rely on it as the report's first line. The game
  name moves to the game model in WL-60.

- **Advice keys are named by what the advice says (`advice.use_cable`), not by the verdict that gives it
  (WL-24).** Five pieces of advice appear in more than one verdict (cable, router restart, firewall,
  hotspot, the report for the provider). One key each keeps them worded the same everywhere, and the
  translator writes each one once. For WL-40's per-platform advice, one small helper that picks the
  platform's key replaces the shared key, instead of five copies of a string to change.
- **Advice that differs by even a word keeps its own key (WL-24)** ("download-ները, torrent-ները,
  stream-ները" versus "download-ները և stream-ները", or "Անջատիր VPN-ը / proxy-ն" versus "…, եթե միացված
  է"), so every text stays exactly as it was. A move card changes no wording.
- **The three phrases used inside other advice (steamstat, hotspot, the report for the provider) are
  nested `Msg` params, made once at the top of `decide()` (WL-24).** They used to be module constants glued
  on with `+`. A constant `Msg` would freeze the language at import, and `+` would flatten the result to
  plain text in one language. With a template such as "{steamstat}. If it's red there too, just wait",
  a translator can also move or re-punctuate the phrase.
- **The verdict's numbers follow the check results' convention (WL-24): the loss percentage goes in raw
  with `{loss:.0f}` in the template, and times go in as `fmt_ms()` strings (`{ms}`, `{jitter}`).** The
  first version passed times raw as `{ms:.0f} ms`; the review caught that `{ms}` would then mean "a
  number" in the verdict and "a formatted time" in the check results, and a translator following the
  catalogue notes would drop the " ms". The output is the same either way: both verdicts need more than
  1 ms, so `fmt_ms()` never takes its "<1 ms" branch.
- **The placeholder for a nested phrase is named after its key: `{steamstat}`, `{hotspot}`,
  `{report_to_isp}` (WL-24).** Renamed from `{report}` before the ru and en catalogues exist, when it
  costs one line.

- **The Steam login (CM) check has separate keys for the login and the web servers (WL-23):**
  `check.steam_cm.ok` / `.web_ok` and `.fail` / `.web_fail`. The old code glued the Armenian case endings
  (`-ից`, `-ը`) onto one shared "Steam's login / web servers" word. That can't be translated: Russian and
  English change the words around it differently. Four whole sentences cost the translator a little more
  and read right in every language.
- **Numbers that the text formats keep their format spec in the template (`{loss:.0f}%`)**, and the code
  passes the raw number (WL-23). The rendered text is unchanged, and WL-32 re-renders from the number,
  not from a string rounded in the worker thread. Times stay `fmt_ms()` strings (`{ms}`), as in checks 1–3.
- **The GC note is built on every call (`_gc_note()`), not as the module constant `GC_NOTE` (WL-23).** A
  `Msg` made at import would freeze the language of that moment. Nothing outside `check_dota_gc` used the
  constant.
- **`dota_gc` failures reuse one key, `check.dota_gc.down` ("… ({error})"), for both a 5xx answer and
  `success = false` (WL-23).** Passing `success = false` as the error keeps that text exactly as before,
  and the translator writes the sentence once.
- **Bugs in reading Valve's answers and error texts were fixed in WL-23, not filed (rule 6).** The
  `test-engineer`, `code-reviewer` and `security-auditor` passes found most of them. Every check now goes
  through the same helpers: `_valve_text()` (a short, printable, one-line `str`, else None), `_ipv4()`
  (a strict public unicast address, else None), `_host()` (that, or a public DNS name), `_gc_version()`
  and `_clip()` (anyone else's words as one printable line).
  - **The rule behind them:** bad data from Valve must be skipped (SKIP, or the web-server fallback),
    never blamed on anyone, and never shown as sent.
  - `parse_sdr_pops` trusted the types in the SDR config: a `desc` or `ipv4` that was a list made `Pop`
    unhashable, and `relays: 5` raised `TypeError`. Either one crashed the relay check into "internal
    error". Wrong-typed entries are now skipped, and a missing or unusable `desc` falls back to the site
    code.
  - A relay address that can't be pinged (`"1.2.3.4:27015"`) made every ping fail. With 1.1.1.1 still
    answering, that read as `routing` and **blamed the provider for Valve's bad data**. A non-public one
    can answer: 127.0.0.1 is the PC, and 192.168.1.1 or 10.0.0.1 is often the home router, which would
    give a fake perfect ping and a wrong "network is fine". `_ipv4()` now takes only `is_global`,
    non-multicast addresses. FakeNet's relays moved from 10.0.0.x to 155.133.226.x (Valve's own public
    range) so the tests use addresses the app accepts.
  - A CM host that can't be a server failed every probe while the API answered, which blamed the
    provider. Examples: "cm host", "[2001:db8::1]", or "localhost" and "0x7f.0.0.1" (both the PC, where the
    Steam client's own ports answer), or one-label names any LAN machine may answer. `_host()` takes a
    strict public IPv4 address, or a name of two or more ASCII labels ending in a letters-only one, and
    not `localhost` / `local`. A list with no usable host falls back to Steam's web servers, as an empty
    list already did. IPv6 CM endpoints are not accepted: Valve's list has none, and the checks are
    IPv4-only. A real name that resolves to a private address still gets through; resolving and filtering
    every address would need its own change (WL-100).
  - A CM port such as `"²"` passed `str.isdigit()` and then `int()` raised, crashing the login-server
    check. Ports must now be ASCII digits in 1–65535.
  - Valve's texts (relay site names, data centers, CM endpoints, the GC version) were shown as sent, and
    so were error texts from the OS or a proxy (`short_error()` falls back to `str(exc)`, and a proxy's
    "Tunnel connection failed: 403 …" reason is the proxy's own words). A line break there could fake a
    line in the report, and an escape code would run in a terminal. Valve's texts must now pass
    `_valve_text()`, or they are replaced (site code, `?`) or left out. Error texts are cleaned by
    `_clip()`, every non-printable character becoming a space.
  - A body nested deeper than the JSON parser's stack raised `RecursionError`, which isn't a
    `ValueError`; it is now "the answer is not JSON".
  - Work on Valve's answers is bounded (rule 3). The data-center list stops at the 5 it shows (it was
    quadratic over every server). More than `MAX_POPS = 128` relay sites is treated as a bad answer
    (SKIP), not cut: dict order could drop the nearest site and make the ping look high, which blames the
    user. Valve lists a few dozen sites, and two ping rounds of 128 stay within the run's budget.
  - **Limits:** 64 characters for Valve's names and 20 for the GC version (a number). Hostnames get the
    DNS limit of 253. Checked against Valve's live answers on 2026-11-27: the longest relay site name is
    exactly 40 characters (the first limit, 40, had no margin left), and the old and new parsers keep the
    same 36 relay sites and the same 65 login-server targets. A name that is refused only shows the site
    code instead.
- **The verdict said "ICMP is blocked" whenever the relay check was skipped. It now says so only for
  `icmp_blocked`, and gives a neutral "the relays weren't checked" line otherwise (WL-23).** The fix was
  first planned for WL-24, but WL-23 made the case common: malformed relay lists now end as SKIP instead of
  crashing. The new line is the key `advice.relays_unchecked`, so no new inline Armenian is added; WL-24
  moves the rest of the advice.
- **Two weaknesses older than WL-23 became cards instead of being fixed here: following an https → http
  redirect (WL-98) and timeouts that are per socket call rather than a total deadline (WL-99).** They
  are hardening of the HTTP client, not bugs in the code this card touched, and each needs its own tests.
  WL-99 also covers DNS lookups, which have no timeout of their own.

## 2026-11-25

- **Results carry key + params, as `i18n.Msg`: a `str` subclass that is rendered when it is made and
  also keeps `key` and `params` (WL-22).** The checks and `decide()` run in the worker thread, so any
  rendered text freezes the language of that moment. Of the card's two options, this one lets WL-32
  switch the language of a finished run (rows, verdict, report) with `i18n.render()`, which the plain
  rendered strings could not. Making it a `str` keeps everything that already uses results working
  unchanged: the report, the CLI, Qt labels, `in` / `==` in the tests and the user's report layout.
  A separate key + params object (not a `str`) would have meant changing every reader and test at once.
  - Parameters that are themselves `Msg` (an error word inside a summary) are rendered again too.
    `HttpFailure.message` keeps the `Msg`, because `str(exc)` would flatten it to one language.
  - The GUI keeps showing the text as it was made; re-rendering on display would be needless work while
    the language can't change (rule 3). WL-32 calls `render()` when the language switches, and WL-34
    calls it when the report is built.
  - Texts with no words to translate stay plain f-strings: `api.steampowered.com → 1.2.3.4 (4 ms)`,
    `Cloudflare (1.1.1.1:443) — 12 ms`. `fmt_ms()` keeps "ms", which gamers read the same in all three
    languages. The OS's own error text (`strerror`) and OpenSSL's certificate reason stay as they come.
  - `check.probe_failed` ("{target} — failed ({error})") is shared by every check that probes a list of
    servers, so the translator writes it once; WL-23 reuses it for the Steam login servers.
  - `CheckSpec.title` / `.hint` now return a fresh `Msg` instead of `t()`'s plain text (this revisits the
    WL-21 entry below), so `run_checks()`'s `res.title = spec.title` keeps the key as well.
  - A result can reach the window after a language switch, because `check_done` is a queued signal.
    WL-32 therefore renders every result it shows whenever the run's language differs from the current
    one, not only the rows already on screen at the moment of the switch.
  - `Msg.__reduce__` keeps a copy's text as it was made: `str`'s default would rebuild the copy as
    `Msg(rendered text)`, looking the text up as a key.
- **`CheckSpec` stores i18n keys (`title_key`, `hint_key`) and `title` / `hint` are properties that call
  `t()` on every read (WL-21).** Every place that shows them (the window's rows and status line, the
  CLI, `res.title` in the report) keeps reading `spec.title` and gets the current language; nothing
  caches a rendered title. The keys are written out in `CHECKS` rather than built from `spec.key`, so a
  search for `check.dns.title` finds where it is used. A spec built with plain text instead of a key
  (one existing test does this) still shows that text, because `t()` returns an unknown key as it is.
- **The "move" cards (WL-21 … WL-26) add their keys to `hy.py` only; `ru.py` and `en.py` get them in
  WL-27 / WL-28.** The language is always `hy` until WL-30, so no user sees a missing translation
  meanwhile. Translating the whole catalogue in one pass also lets the translator keep the terms
  consistent across checks, verdicts and the UI.

## 2026-11-23

- **The owner's note on keeping CLAUDE.md short became rule 17,** done as card WL-96 (no card existed;
  the next free QUALITY id). One card, not two: the README change applies the same style rule and is `XS`.
- **CLAUDE.md keeps the rules, the architecture, the commands and the tooling table;** the details went to
  nine `.claude/rules/` files cut by where they apply (checks, gui, i18n, python, packaging, tests, ci,
  claude-tooling, docs). The security essentials stay in rule 9, because secrets and private data matter
  in every file, commit and request, which no `paths:` glob can cover.
- **Every rule now states its why.** The owner gave the what; the whys were inferred from the project and
  kept to one line each. The owner can correct any of them.
- **The size limit is a pytest test** (`tests/test_claude_md.py`), not a CI-only check: the Stop hook runs
  it locally whenever CLAUDE.md or `.claude/rules/` changes, and CI runs it with every task because the
  version bump touches `pyproject.toml`. `CLAUDE.md` is not added to CI's `paths`, so a docs-only fix
  costs no runner minutes (rule 11). The SessionStart hook reports CLAUDE.md past ~200 lines, the soft
  target.
- **The test also requires every `paths:` glob to match a file and every rules file to be listed in
  CLAUDE.md:** a glob broken by a rename makes its rules silently never load, and an unlisted file is
  invisible to anyone reading CLAUDE.md. Brace globs (`{a,b}`) are refused because the test's
  `PurePath.full_match` can't expand them.
- **Rules-file globs are matched against `git ls-files --cached --others --exclude-standard`,** the
  files CI's checkout will hold once the task is committed. A tree walk would also count ignored local
  files (a glob matching only those passes locally and fails in CI). git also never walks `.venv`.
- **The `core.autocrlf` note moved into the finish-task skill:** it matters only when committing, and no
  `paths:` glob covers "running git".

## 2026-11-22

- **Translation catalogues are Python modules, one per language** (`src/wholagged/locales/{hy,ru,en}.py`,
  a `MESSAGES` dict each), as the card suggested: no file I/O or parser, packaged with the code, checked by
  ruff, and only the needed language is imported (lazily, once). Armenian is the source catalogue. They are
  loaded with plain `from .locales import hy` statements, not `importlib` with a computed name, so a
  freezer (PyInstaller or Nuitka, WL-80/81) bundles all three.
- **`t()` never raises for ordinary values (str, int, float, None):** lookup goes current language →
  English → the key itself (an empty translation
  counts as missing), and a field whose parameter is missing stays exactly as written (`{name}`,
  `{pops[0]}`, `{ms!r}`), so a missing text shows up instead of crashing the window. Fields are rendered one
  by one with `string.Formatter`, because `format_map` with a `__missing__` dict indexed or converted the
  stand-in text (`{pops[0]}` became `{`). Parameters are only substituted into our own templates, so
  untrusted values from Valve can't inject format fields.
- **`set_language()` accepts only `hy`, `ru` and `en` (any case) and raises ValueError otherwise.** Mapping OS
  locales such as `hy_AM` or `be` is WL-30's job, and WL-31's `--lang` can show the allowed values from the
  error. The default stays `hy`, so the app looks the same until WL-30.
- **The catalogues start with one real key, `app.subtitle`**, in all three languages (the translator's text
  from WL-10), so the format and the tests work on real data; WL-26 wires it into the window.
- **The I18N "move" cards WL-21 … WL-26 moved from Backlog to To Do**, now that WL-20 unblocks them; WL-15
  waits behind them, since it needs the owner's PyPI account.
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
