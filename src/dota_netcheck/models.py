from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class Status(StrEnum):
    OK = "ok"
    WARN = "warn"
    FAIL = "fail"
    SKIP = "skip"


@dataclass
class CheckResult:
    key: str
    status: Status
    summary: str
    details: list[str] = field(default_factory=list)
    latency_ms: float | None = None
    # Machine-readable flags for the verdict engine (e.g. {"routing": True}).
    data: dict[str, Any] = field(default_factory=dict)
    title: str = ""


class Side(StrEnum):
    YOU = "you"  # your internet / connection quality
    ISP = "isp"  # the provider's route to Valve, VPN or firewall
    VALVE = "valve"  # Valve's servers
    PC = "pc"  # network is fine: the PC / Steam client
    UNCLEAR = "unclear"


@dataclass
class Verdict:
    side: Side
    headline: str
    explanation: str
    advice: list[str] = field(default_factory=list)
