---
paths:
  - ".claude/**"
  - "CLAUDE.md"
  - "tests/test_claude_hooks.py"
  - "tests/test_claude_md.py"
---

# Claude Code tooling (`.claude/`) and keeping CLAUDE.md short

## Hooks
- Hooks run with `uv run --no-project python` and call `uv run --frozen`, so they never rewrite `uv.lock`.
- `guard.py` fails open (a crash lets the call run): keep `tests/test_claude_hooks.py` green when changing it.
- The guard also checks commands nested in `uv run`, `bash -c`, `powershell -Command` and `cmd /c`.
- Documents and spreadsheets (pdf, docx, xlsx, csv) are not committed unless listed in
  `.claude/hooks/allowed-documents.txt`.
- `stop_check.py` runs the tests when code, `CLAUDE.md`, `.claude/rules/` or a README changed.
- `session_start.py` reports CLAUDE.md growing past ~200 lines.

## Agents and skills
- Subagents use `model: inherit` and no `effort` field (rule 13).
- Agents and skills added to `.claude/` load only in the next session. In the session that creates them,
  run a `general-purpose` agent and tell it to follow the agent file.
- The auto-mode classifier may refuse edits to permission rules in `.claude/settings.json`. Don't work
  around it; mention it to the owner.

## CLAUDE.md and `.claude/rules/` (rule 17)
- CLAUDE.md holds only the owner's rules, the architecture and pointers. Aim for ~200 lines; 400 is the limit.
- Everything else goes into a `.claude/rules/<topic>.md` file that starts with a `paths:` list:
  ```
  ---
  paths:
    - "src/wholagged/gui.py"
  ---
  ```
- `paths:` is required: a rules file without it loads in every session.
- Globs are relative to the repo root. Write each one out; no `{a,b}` braces.
- Every glob must match at least one file, or the file silently never loads (for example after a rename).
- List every rules file in CLAUDE.md's "Where the details are" table.
- Keep rules files short; split one when it grows.
- `tests/test_claude_md.py` checks all of the above, the 400-line limit and that CLAUDE.md has no `@` imports.
