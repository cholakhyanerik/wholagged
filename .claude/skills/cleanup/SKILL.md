---
name: cleanup
description: Remove temporary and generated junk (caches, build output, temp/backup files) from the wholagged repo after a task is pushed. Use as the last step of finish-task, or whenever the tree has leftovers.
---

# Cleanup

1. Preview: `uv run --no-project python .claude/skills/cleanup/cleanup.py --dry-run`
2. Clean: `uv run --no-project python .claude/skills/cleanup/cleanup.py`
3. Read the list of untracked files it kept. For each one decide: it is real work (commit it in the
   current task) or scratch (delete it by its exact path). Never leave scratch files in the repo.
4. Also delete anything you created outside the repo for this task that is no longer needed (for
   example files in the session scratchpad that the user won't need).

Never delete `.venv`, `.git`, `uv.lock` or tracked files, and never use `git clean -x` (it deletes
`.venv`; the guard hook blocks it).
