"""Plain-text report that can be pasted into a chat or sent to the provider.

The labels are looked up with `t()` when the report is built, so they are in the language shown at that
moment. The layout (marks, colons, indents, numbering) stays here in code: people send this text to their
provider, so it must not change with a translation.
"""

from __future__ import annotations

import platform
from datetime import datetime

from . import APP_NAME, __version__
from .i18n import t
from .models import CheckResult, Side, Status, Verdict

MARKS = {Status.OK: "[OK]", Status.WARN: "[ ! ]", Status.FAIL: "[XX]", Status.SKIP: "[ - ]"}

SIDE_KEYS = {
    Side.YOU: "side.you",
    Side.ISP: "side.isp",
    Side.VALVE: "side.valve",
    Side.PC: "side.pc",
    Side.UNCLEAR: "side.unclear",
}


def side_label(side: str) -> str:
    """Whose side the problem is on, in words, in the current language (a side we don't know: as it is)."""
    key = SIDE_KEYS.get(side)
    return t(key) if key else str(side)


def build_report(results: dict[str, CheckResult], verdict: Verdict | None) -> str:
    lines = [
        f"{APP_NAME} {__version__} · Dota 2",
        f"{t('report.time')}: {datetime.now().astimezone():%Y-%m-%d %H:%M:%S %Z}",
        f"{t('report.system')}: {platform.system()} {platform.release()}",
        "",
    ]
    for res in results.values():
        lines.append(f"{MARKS[res.status]} {res.title}: {res.summary}")
        lines.extend(f"       {d}" for d in res.details)
    if verdict:
        lines += [
            "",
            f"{t('report.verdict')}: {verdict.headline}",
            f"{t('report.side')}: {side_label(verdict.side)}",
            verdict.explanation,
            "",
            f"{t('report.advice')}:",
        ]
        lines += [f"  {i}. {a}" for i, a in enumerate(verdict.advice, 1)]
    return "\n".join(lines)
