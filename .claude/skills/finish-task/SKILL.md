---
name: finish-task
description: Ship a finished task in the wholagged repo - verify, review, update TASKS.md, CHANGELOG, version, READMEs, CLAUDE.md and DECISIONS.md, then commit, push and clean up, without asking. Use every time a task (or a bug fix) is done.
argument-hint: "[WL-id]"
---

# Finish a task

Do every step, in order, without asking the user. All docs are written in English (except the
translated READMEs).

1. **Verify.**
   - `uv run ruff check` and `uv run pytest -q` pass.
   - GUI touched? Smoke-test it headless:
     `QT_QPA_PLATFORM=offscreen uv run python -c "from PySide6.QtWidgets import QApplication; from wholagged.gui import MainWindow; app = QApplication([]); w = MainWindow(); w.show(); app.processEvents(); print('gui ok')"`
   - CLI touched? Run `uv run wholagged --cli` once if a network is available.
2. **Review.** For anything beyond a trivial change, run the `code-reviewer` subagent; also run
   `security-auditor` when networking, subprocess/ctypes, dependencies, workflows, packaging or web parts
   changed. Fix every `blocker`/`should-fix` (and every `critical`/`high`/`medium`) and re-verify.
3. **TASKS.md.** Delete the finished card. Add cards for new work you discovered (small: `XS`/`S`, with
   acceptance criteria). Re-order To Do by priority. Bugs you found were already fixed, not filed.
4. **Version.** Bump with uv: `uv version --bump minor` for a new feature, `uv version --bump patch` for
   anything else (fix, docs, tooling, dependencies). Then set the same value in
   `src/wholagged/__init__.py` (`__version__`); `tests/test_net_helpers.py` checks they match.
5. **CHANGELOG.md.** Add a section `## [x.y.z] - YYYY-MM-DD` at the top with `Added` / `Changed` /
   `Fixed` / `Security` / `Dependencies` entries written for users, each ending with the task id
   (`(WL-12)`). Update the compare links at the bottom.
6. **README.md** (English) for any user-visible change: features, checks table, verdict rules, commands,
   known issues, platform table, project structure. Then have the `translator` subagent mirror the
   changes into `README.hy.md` (and `README.ru.md` when it exists).
7. **CLAUDE.md.** Improve it with what this task taught: new commands, conventions, pitfalls, files.
   Keep it short and current; remove anything that became false.
8. **DECISIONS.md.** Log every decision you made on your own (date, decision, why).
9. **Commit.** Stage explicit paths (`git add <files>`, never secrets; the guard hook scans the commit).
   Message: `WL-<id>: <imperative summary>` (or `fix: …` / `chore: …` for work without a card),
   a short body with the why, and the attribution trailer the harness specifies.
10. **Push and tag.** `git push`. If it is rejected, `git pull --rebase` and push again. Never force-push.
    Then `git tag vX.Y.Z` (the new version) and `git push origin vX.Y.Z`.
    If a CI workflow ran for the push, check it once with `gh run list --limit 1` before the next task.
11. **Clean up.** Run the `cleanup` skill.
12. **Report** to the user in their language: what was done, the version, the commit, and what's next.
