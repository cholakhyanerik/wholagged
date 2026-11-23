---
paths:
  - "**/*.py"
  - "pyproject.toml"
---

# Python style

- Modern typed Python 3.15: `from __future__ import annotations`, dataclasses, `StrEnum`, PEP 695 generics.
- ruff must be clean. `# noqa: <code> - <reason>` only with a reason.
- ruff's default rule set is broad (`BLE`, `RUF`, `PLW`, `I`, …); the project adds `S` (security).
- `fakes` is configured as a local module for import sorting.
- uv only: never `pip`, `venv`, `requirements.txt` or a bare `python` (the guard hook blocks them).

## Pitfalls
- Python 3.15 runs in UTF-8 mode by default, so printing Armenian to a Windows console or pipe is safe.
