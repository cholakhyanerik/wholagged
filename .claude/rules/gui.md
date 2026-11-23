---
paths:
  - "src/wholagged/gui.py"
---

# The window (`gui.py`)

## Threads
- Qt lives only in `gui.py`.
- The checks run in `CheckWorker` (a `QThread`). The UI is updated only through its signals, never from
  the worker thread directly.
- Nothing slow on the GUI thread (rule 3).

## Text and safety
- Text from Valve is shown as plain text (`Qt.TextFormat.PlainText`).
- Rich text only for our own strings, escaped with `_html`.
- Opened URLs are constants.
- Labels go through `t()` (`.claude/rules/i18n.md`); don't add new inline strings.

## Design (reuse it, don't invent new styles)
- Dark theme: background `#111317`, card `#1a1d23`, raised `#21252c`, border `#2b3038`, text `#e9e7e4`,
  muted `#8d939e`, accent (primary button, progress) `#c8402e` (hover `#d9503d`), running `#58a6ff`.
- Status colours: OK `#3fb950`, WARN `#d29922`, FAIL `#f85149`, SKIP `#6e7681`.
- Verdict-side chips: you `#f85149`, provider `#d29922`, Valve `#a371f7`, PC / fine `#3fb950`.
- Components by object name: `card` (radius 10, 1 px border), `primary` / `link` buttons (radius 8),
  `title` 21 pt bold, `headline` 15 pt bold, `rowTitle` 11 pt semibold, `muted`, `details` 9 pt.
- Segoe UI 10 on Windows. Window 760×860, margins 28/24, spacing 12.

## UX principles
- One big obvious action.
- Results appear as each check finishes.
- Problem details open automatically.
- The verdict comes first.
- Every piece of advice is something the user can do now.
- Larger UX ideas become `ux` cards in TASKS.md (rule 15).

## Headless smoke test
`QT_QPA_PLATFORM=offscreen uv run python -c "from PySide6.QtWidgets import QApplication; from wholagged.gui import MainWindow; app = QApplication([]); w = MainWindow(); w.show(); app.processEvents(); print('gui ok')"`
