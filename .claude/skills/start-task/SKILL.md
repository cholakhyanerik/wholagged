---
name: start-task
description: Start work on the next task from TASKS.md (or the WL-id given as argument) - pick it, split it if it is too big, move it to In Progress and plan it. Use at the start of any piece of work in the wholagged repo.
argument-hint: "[WL-id]"
---

# Start a task

1. Read `TASKS.md`. Take the task `$ARGUMENTS` if given; otherwise the first card in **To Do** whose
   `Depends` are all done (no longer on the board). If To Do is empty, pull the top card from **Backlog**.
2. If the card is bigger than size `S` (about two hours), split it into `XS`/`S` cards with new ids first,
   and take the first of them.
3. Move the card to **In Progress** (only one card at a time).
4. Make sure the base is sound before building on it: `uv run pytest -q` and `uv run ruff check` pass.
   If something was already broken, fix it first (bugs are fixed in the session, never filed as tasks).
5. Read the code the task touches and write a 3–6 bullet plan in your reply. No questions to the user:
   where something is unclear, pick the most reasonable option and log it in `DECISIONS.md`.
6. Implement following `CLAUDE.md`. Use the subagents where they help: `test-engineer` for tests,
   `translator` for user-facing text, `code-reviewer` / `security-auditor` before committing.
7. When the acceptance criteria are met, run the `finish-task` skill.
