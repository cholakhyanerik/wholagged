---
paths:
  - "README*.md"
  - "alias/*/README.md"
  - "CHANGELOG.md"
  - "TASKS.md"
  - "DECISIONS.md"
---

# Docs

## Languages
- `README.md` (English) is the source. `README.hy.md` (and `README.ru.md`, WL-35) mirror it in every
  change (the `translator` subagent).
- `alias/dota-netcheck/README.md` (its PyPI page) holds en, hy and ru in one file: change all three
  together (the `translator` subagent). PyPI renders no heading anchors, so no in-page language links.
- `CLAUDE.md`, `CHANGELOG.md`, `TASKS.md`, `DECISIONS.md` and everything in `.claude/` are English only.

## Style
- READMEs use short lists and tables. No long paragraphs: at most a sentence or two of intro per section.
- History ("since v0.x", "in WL-n") goes to CHANGELOG and git, not into READMEs or CLAUDE.md.
  A version a user needs in order to act (for example in troubleshooting) is not history.
- Keep the README checks table in sync with `CHECKS`, and the verdict list with `verdict.py`.
- Getting started puts PyPI first (`uvx`, `uv tool install`) and the clone under "From source".
- Every line of a code block must be in `ALLOWED` (fetches something) or `HARMLESS` in
  `tests/test_docs.py`, word for word; so must any inline command that installs or downloads. Add one
  only after checking what it fetches. The old name only through uvx (`uvx dota-netcheck`),
  never as `uv tool install dota-netcheck`: two uv tools can't share its command.
- Tag command blocks `powershell`; tag blocks that aren't commands (the project structure) `text`.
- Show commands only as fenced or inline code: prose and indented blocks aren't read. Never put a
  command not to type in code: say it in words.

## Files
- CHANGELOG: Keep a Changelog, entries written for users, each ending with the task id; update the
  compare links (`finish-task`).
- TASKS.md: the card format is in its header.
- DECISIONS.md: newest first; date, decision, why. Revisit by adding an entry, never by rewriting one.
- The repo is public: no business strategy, revenue numbers or partner names. Only what the README
  roadmap says is public.
