---
paths:
  - "README*.md"
  - "CHANGELOG.md"
  - "TASKS.md"
  - "DECISIONS.md"
---

# Docs

## Languages
- `README.md` (English) is the source. `README.hy.md` (and `README.ru.md`, WL-35) mirror it in every
  change (the `translator` subagent).
- `CLAUDE.md`, `CHANGELOG.md`, `TASKS.md`, `DECISIONS.md` and everything in `.claude/` are English only.

## Style
- READMEs use short lists and tables. No long paragraphs: at most a sentence or two of intro per section.
- History ("since v0.x", "in WL-n") goes to CHANGELOG and git, not into READMEs or CLAUDE.md.
  A version a user needs in order to act (for example in troubleshooting) is not history.
- Keep the README checks table in sync with `CHECKS`, and the verdict list with `verdict.py`.

## Files
- CHANGELOG: Keep a Changelog, entries written for users, each ending with the task id; update the
  compare links (`finish-task`).
- TASKS.md: the card format is in its header.
- DECISIONS.md: newest first; date, decision, why. Revisit by adding an entry, never by rewriting one.
- The repo is public: no business strategy, revenue numbers or partner names. Only what the README
  roadmap says is public.
