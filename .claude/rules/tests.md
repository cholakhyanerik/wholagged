---
paths:
  - "tests/**"
---

# Tests

- Offline only; the whole suite runs in about a second. Never touch the real network.
- `tests/fakes.py::FakeNet` replaces `tcp_probe`, `_resolve`, `http_get_json`, `icmp.ping` and `time.sleep`.
- Each `FakeNet` attribute is a knob that breaks one thing: `internet`, `dns`, `unresolved` (a set of
  names), `tcp_ok`, `cert_ok`, `relays_ok`, `control_ok`, `loss_every`, `relay_extra_ms`, `http[url]`.
  Add a knob instead of patching ad hoc.
- FakeNet's error words come from `checks.short_error()`, so they are `i18n.Msg` like the real ones.
- Each verdict branch has a scenario in `test_scenarios.py`.
- Helpers are tested in `test_parsing.py` and `test_net_helpers.py`.
- `test_i18n.py` covers `t()` and `Msg` (lookup, fallbacks, placeholders, rendering a finished run again)
  and checks that every catalogue uses the same placeholders as `hy`. It also scans `src/` (with `ast`) so
  every `t("…")` / `Msg("…")` key is in `hy.py` with the right params. Its autouse fixture restores the
  language and the catalogue cache: tests that switch the language belong there.
- `test_claude_hooks.py` tests the guard hook; `test_claude_md.py` checks CLAUDE.md and `.claude/rules/`.
- Don't weaken an assertion to make a change pass: a failing old test means old behaviour broke.
- The Windows CI job runs the same tests. FakeNet replaces `icmp.ping`, so the ctypes ping isn't covered
  yet (WL-95).

## Pitfalls
- pytest runs with `-p no:cacheprovider` (no `.pytest_cache`), so `--lf` is not available.
- Tests import `fakes` because pytest's default `prepend` import mode puts `tests/` on `sys.path`;
  there is no `conftest.py`.
