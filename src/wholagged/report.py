"""Plain-text report that can be pasted into a chat or sent to the provider."""

from __future__ import annotations

import platform
from datetime import datetime

from . import APP_NAME, __version__
from .models import CheckResult, Status, Verdict

MARKS = {Status.OK: "[OK]", Status.WARN: "[ ! ]", Status.FAIL: "[XX]", Status.SKIP: "[ - ]"}

SIDE_LABELS = {
    "you": "Քո internet-ը / կապը",
    "isp": "Provider-ի route-ը, VPN-ը կամ firewall-ը",
    "valve": "Valve-ի սերվերները",
    "pc": "Համակարգիչը / Steam client-ը",
    "unclear": "Valve-ը կամ provider-ը (տես խորհուրդները)",
}


def build_report(results: dict[str, CheckResult], verdict: Verdict | None) -> str:
    lines = [
        f"{APP_NAME} {__version__} · Dota 2",
        f"Ժամանակ: {datetime.now().astimezone():%Y-%m-%d %H:%M:%S %Z}",
        f"Համակարգ: {platform.system()} {platform.release()}",
        "",
    ]
    for res in results.values():
        lines.append(f"{MARKS[res.status]} {res.title}: {res.summary}")
        lines.extend(f"       {d}" for d in res.details)
    if verdict:
        lines += [
            "",
            f"ԵԶՐԱԿԱՑՈՒԹՅՈՒՆ: {verdict.headline}",
            f"Ում կողմից: {SIDE_LABELS.get(verdict.side, verdict.side)}",
            verdict.explanation,
            "",
            "Ինչ անել:",
        ]
        lines += [f"  {i}. {a}" for i, a in enumerate(verdict.advice, 1)]
    return "\n".join(lines)
