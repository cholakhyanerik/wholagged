---
paths:
  - "tests/**"
---

# Tests

- Offline only; the whole suite runs in about a second. Never touch the real network.
- `tests/fakes.py::FakeNet` replaces `tcp_probe`, `_resolve`, `http_get_json`, `icmp.ping` and `time.sleep`.
- Each `FakeNet` attribute is a knob that breaks one thing: `internet`, `dns`, `unresolved` and
  `refused_hosts` (sets of names), `tcp_ok`, `cert_ok`, `relays_ok`, `control_ok`, `loss_every`,
  `relay_extra_ms`, `relay_jitter_ms` (every 2nd relay ping slower), `http[url]` (a JSON answer, an int
  HTTP status, or an exception raised as is to crash a check). Add a knob instead of patching ad hoc.
- Relay pings are counted per IP, so `loss_every` and `relay_jitter_ms` give the same per-site lines on
  every run although the relays are pinged in parallel. Control pings are never dropped or slowed;
  pings to `127.x` always answer (0.1 ms), like a real PC. `net.pinged` records every ping (control
  ones too), for "no ping was sent" asserts.
- Fake relays sit at public `155.133.226.N`: `_ipv4` refuses private, loopback and other non-global
  addresses, so a `10.x` relay would be dropped as unusable.
- FakeNet's error words come from `checks.short_error()`, so they are `i18n.Msg` like the real ones.
- Each verdict branch has a scenario in `test_scenarios.py`.
- Helpers are tested in `test_parsing.py` and `test_net_helpers.py`.
- `test_i18n.py` covers `t()` and `Msg` (lookup, fallbacks, placeholders, rendering a finished run and
  its verdict again) and checks that every catalogue uses the same placeholders as `hy`. It also scans `src/` (with `ast`) so
  every `t("…")` / `Msg("…")` key is in `hy.py` with the right params, and fails on any Armenian letter in a
  package module outside `locales/`. The window's texts are tested from the catalogue (`WINDOW_HY` pins the
  Armenian words), never by importing `gui.py`: on the Linux runner Qt needs system libraries (WL-92).
  Its autouse fixture restores the language and the catalogue cache: tests that switch the language belong there.
- `test_claude_hooks.py` tests the guard hook and the SessionStart task line (with a scratch `TASKS.md`);
  `test_claude_md.py` checks CLAUDE.md and `.claude/rules/`.
- `test_docs.py` keeps README commands to its reviewed lists (`ALLOWED`, `HARMLESS`); every list entry
  must still be used. It reads the `dota-netcheck` package's README too (its PyPI page). Add a lookalike
  that should be caught to `BAD` (checked in five Markdown forms) rather than loosening `FETCHES` or the
  Markdown reader. Lookalikes use a typo (`dota-netchek`): the old name itself is allowed through uvx.
  A program keeps its path (a network share runs a remote file), and `# comment` is cut only after the
  line is split at `;` / `&` / `|` (cmd.exe and zsh don't read `#` as a comment).
- `test_alias.py` keeps `alias/dota-netcheck/` a no-code package at wholagged's version, with the same
  metadata, `[build-system]` and `LICENSE`.
- `test_packaging.py` keeps each runtime dependency at `name>=A.B[.C…],<A.B+1`, matching the minor in
  `uv.lock`, and `shiboken6` locked at PySide6's version (WL-104).
- Don't weaken an assertion to make a change pass: a failing old test means old behaviour broke.
- The Windows CI job runs the same tests. FakeNet replaces `icmp.ping`, so the ctypes ping isn't covered
  yet (WL-95).

## Pitfalls
- pytest runs with `-p no:cacheprovider` (no `.pytest_cache`), so `--lf` is not available.
- Tests import `fakes` because pytest's default `prepend` import mode puts `tests/` on `sys.path`;
  there is no `conftest.py`.
- Write invisible characters as `chr(0x2028)` or `"\x85"`, never raw: an edit can turn a `\u` escape into
  the raw character, and ruff catches only some of them (PLE2502).
