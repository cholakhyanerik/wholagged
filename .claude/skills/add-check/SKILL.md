---
name: add-check
description: Step-by-step recipe for adding or changing a network check or a verdict rule in wholagged (checks.py, verdict.py, FakeNet, tests, README, translations). Use when a task adds a diagnostic such as gateway ping, a new game's servers, or a new failure mode.
---

# Add or change a check / verdict rule

## The check (`src/wholagged/checks.py`)
- Standard library only (the CLI must run without Qt). Every socket/HTTP call has a timeout
  (`TCP_TIMEOUT_S`, `HTTP_TIMEOUT_S`, `icmp.DEFAULT_TIMEOUT_MS`). Fan out with `parallel()`.
- Signature `def check_x(ctx: Context) -> CheckResult`. Share data between checks through `Context`.
- Return `Status.OK / WARN / FAIL / SKIP`. **SKIP means "we can't tell"** and must never lead to blaming
  anyone. Put machine-readable facts for the verdict in `data` (e.g. `{"tls_error": True}`).
- Exceptions are caught by `run_checks`, but don't rely on it: handle expected failures yourself.
- Add `check.<key>.title` and `check.<key>.hint` to `locales/hy.py` first, then a
  `CheckSpec(key, "check.<key>.title", "check.<key>.hint", func)` to `CHECKS` in the order it should run.
  Pass the keys, never the text: `t()` shows an unknown key as it is, so inline text would look right in
  Armenian and silently skip translation. The GUI builds its rows from `CHECKS`, so nothing else is
  needed there.
- **Compatibility:** never rename existing keys or `data` flags; tests, the verdict and users' reports
  depend on them. The whole run must stay within about 10–20 seconds.

## The verdict (`src/wholagged/verdict.py`)
- Rules run top to bottom; the first match wins. Place the new rule by priority: hard failures on the
  user's side first, then Valve, then the route, then quality, then "the network is fine".
- Each `Verdict` has a side, a headline, an explanation and 3–5 practical advice items, in the same tone
  as the existing ones. Keep the numbered rule comments in order.
- Affiliate or commercial suggestions must never change the verdict (README → Transparency).

## Tests
- Add a knob to `tests/fakes.py::FakeNet` that breaks exactly the new thing.
- Add a scenario to `tests/test_scenarios.py` for every new outcome, asserting the status, the `data`
  flags and the verdict side. Add parser/helper unit tests to `tests/test_parsing.py` or
  `tests/test_net_helpers.py`. The `test-engineer` subagent can do this part.

## Text and docs
- User-facing strings in every UI language (rule 14, `.claude/rules/i18n.md`); use the `translator` subagent.
- `README.md`: the "What it checks" table and "How the verdict is decided" list; then sync the translated
  READMEs.
- Finish with the `finish-task` skill.
