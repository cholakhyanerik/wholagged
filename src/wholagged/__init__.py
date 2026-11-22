"""wholagged: is it your internet, your provider or Valve's servers? (Dota 2 for now.)"""

from __future__ import annotations

import sys

__version__ = "0.2.1"
APP_NAME = "wholagged"  # the product name shown in the window, the CLI and the report


def run_cli() -> int:
    from .checks import run_checks
    from .report import MARKS, SIDE_LABELS
    from .verdict import decide

    print(f"{APP_NAME} {__version__} · Dota 2 — ստուգում եմ...\n", flush=True)

    def on_result(res):
        print(f"{MARKS[res.status]} {res.title}: {res.summary}", flush=True)
        for line in res.details:
            print(f"       {line}", flush=True)

    verdict = decide(run_checks(on_result=on_result))
    print("\n" + "=" * 60)
    print(f"ԵԶՐԱԿԱՑՈՒԹՅՈՒՆ: {verdict.headline}")
    print(f"Ում կողմից: {SIDE_LABELS.get(verdict.side, verdict.side)}")
    print(verdict.explanation)
    print("\nԻնչ անել:")
    for i, tip in enumerate(verdict.advice, 1):
        print(f"  {i}. {tip}")
    return 0


def main() -> int:
    if "--cli" in sys.argv[1:]:
        return run_cli()
    from .gui import run_gui

    return run_gui()
