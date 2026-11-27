"""Network checks: who is to blame, your internet or Valve's servers.

Every check function takes a shared Context and returns a CheckResult.
Only the standard library is used here, so the module also runs without Qt
(`uv run wholagged --cli`).
"""

from __future__ import annotations

import http.client
import ipaddress
import json
import re
import socket
import ssl
import statistics
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from itertools import pairwise
from typing import Any

from . import APP_NAME, __version__, icmp
from .i18n import Msg
from .models import CheckResult, Status

TCP_TIMEOUT_S = 3.0
HTTP_TIMEOUT_S = 8.0
MAX_BODY_BYTES = 4_000_000  # Valve's largest answer (the SDR config) is far below this
USER_AGENT = f"{APP_NAME}/{__version__}"

CM_LIST_URL = (
    "https://api.steampowered.com/ISteamDirectory/GetCMListForConnect/v1/"
    "?cellid=0&format=json"
)
SDR_CONFIG_URL = "https://api.steampowered.com/ISteamApps/GetSDRConfig/v1/?appid=570"
GC_VERSION_URL = "https://api.steampowered.com/IGCVersion_570/GetServerVersion/v1/"

# Plain IPs, so the internet check does not depend on DNS.
INTERNET_PROBES = [
    ("1.1.1.1", 443, "Cloudflare"),
    ("8.8.8.8", 443, "Google"),
    ("9.9.9.9", 443, "Quad9"),
]
STEAM_DNS_NAMES = ["api.steampowered.com", "steamcommunity.com"]
OTHER_DNS_NAMES = ["google.com"]
CONTROL_PING_IPS = ["1.1.1.1", "8.8.8.8"]
# Used when the CM list could not be fetched.
STEAM_FALLBACK_HOSTS = [
    ("store.steampowered.com", 443, "web"),
    ("steamcommunity.com", 443, "web"),
    ("api.steampowered.com", 443, "web"),
]

CM_TARGETS = 6
SHOWN_DATA_CENTERS = 5
# Valve lists a few dozen relay sites. More than this is a bad answer, not a list to cut: dict order could
# drop the nearest site and make the ping look high. Two ping rounds of 128 at 24 workers stay within budget.
MAX_POPS = 128
QUALITY_PINGS = 10
QUALITY_POPS = 3
LOSS_WARN_PCT = 5.0
HIGH_PING_MS = 150.0
JITTER_WARN_MS = 30.0


@dataclass
class Context:
    internet_ok: bool = True
    cm_servers: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class Pop:
    code: str
    desc: str
    ip: str


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _clip(text: str, limit: int = 70) -> str:
    """Someone else's words (the OS's, a server's, a proxy's) as one short line of printable text.

    A proxy's reason phrase or a bad HTTP status line can carry line breaks and terminal escape codes; they
    would fake lines in the report and run in a terminal. Every non-printable character becomes a space.
    """
    text = " ".join("".join(c if c.isprintable() else " " for c in text).split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


VALVE_TEXT_MAX_CHARS = 64  # relay site and data center names ("Washington DC (Sterling)") are far shorter
MAX_HOSTNAME_CHARS = 253  # the DNS limit


def _valve_text(value: object, limit: int = VALVE_TEXT_MAX_CHARS) -> str | None:
    """A text from Valve that is safe to show: a short, printable, one-line `str`, stripped; else None.

    Valve's answers are untrusted input, and their texts end up in the rows and in the report users send to
    their provider: a line break or a control character there could fake a line of the report.
    """
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text if text and len(text) <= limit and text.isprintable() else None


def _ipv4(value: object) -> str | None:
    """A strict, public, unicast IPv4 address from Valve ("155.133.226.1"), or None.

    A malformed address would only fail to ping, which reads as a routing problem. A non-public one is
    never a Valve server, and it can answer: 127.0.0.1 is the PC itself and 192.168.1.1 is often the home
    router, so either would show a perfect ping for a site that wasn't measured. `is_global` rules out
    private, shared (CGNAT), loopback, link-local, documentation, reserved and broadcast addresses; it lets
    multicast through, so that is checked on its own.
    """
    if not isinstance(value, str):
        return None
    try:
        addr = ipaddress.IPv4Address(value)
    except ValueError:
        return None
    return str(addr) if addr.is_global and not addr.is_multicast else None


_HOST_LABEL = re.compile(r"(?!-)[A-Za-z0-9-]{1,63}(?<!-)")
_TOP_LABEL = re.compile(r"[A-Za-z]{2,63}")  # "net": letters only, so "0x7f.0.0.1" can't pass as a name
_LOCAL_NAMES = ("localhost", "local")  # the PC itself, or names any machine on the LAN may answer


def _host(value: str) -> str | None:
    """A server's host from Valve: a strict public IPv4 address or a public DNS name, else None.

    A name has two or more ASCII labels of letters, digits and hyphens and ends in a letters-only label.
    Anything else can't be a Valve server: "cm host" and "[2001:db8::1]" can't be reached, so a list of
    them would blame the provider; "localhost", "0x7f.0.0.1" (127.0.0.1 to the resolver) and one-label LAN
    names reach the PC or the LAN, where the Steam client's own ports would answer. Skipped, a bad list falls
    back to Steam's web servers instead.
    """
    if value.replace(".", "").isdigit():  # all digits: only a strict address ("1.2.3" resolves oddly)
        return _ipv4(value)
    name = value.removesuffix(".")
    labels = name.split(".")
    if (
        len(name) > MAX_HOSTNAME_CHARS
        or len(labels) < 2
        or not all(_HOST_LABEL.fullmatch(label) for label in labels)
        or not _TOP_LABEL.fullmatch(labels[-1])
        or labels[-1].lower() in _LOCAL_NAMES
    ):
        return None
    return value


def short_error(exc: BaseException | str) -> str:
    """A few words on what went wrong: our own (translated) words for the common errors, else the OS's text."""
    if isinstance(exc, str):
        return exc if isinstance(exc, Msg) else _clip(exc)
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return Msg("error.timeout")
    if isinstance(exc, ConnectionRefusedError):
        return Msg("error.refused")
    if isinstance(exc, ConnectionResetError):
        return Msg("error.reset")
    if isinstance(exc, socket.gaierror):
        return Msg("error.dns")
    if isinstance(exc, ssl.SSLError):
        return Msg("error.ssl")
    text = exc.strerror if isinstance(exc, OSError) and exc.strerror else str(exc)
    return _clip(text) or type(exc).__name__  # nothing printable left: at least say what it was


def tcp_probe(host: str, port: int, timeout: float = TCP_TIMEOUT_S) -> tuple[float | None, str | None]:
    """Open a TCP connection and close it. Returns (ms, error)."""
    t0 = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            pass
    except OSError as exc:
        return None, short_error(exc)
    return (time.perf_counter() - t0) * 1000, None


class HttpFailure(Exception):
    def __init__(self, message: str, status: int | None = None, cert_error: str | None = None) -> None:
        super().__init__(message)
        self.message = message  # may be a Msg; `str(exc)` would flatten it to text in one language
        self.status = status
        # Set (to the reason) only when the server's certificate was rejected: system clock, antivirus
        # HTTPS scanning, captive portal or missing CA certificates. Other TLS errors, such as a handshake
        # cut off by a middlebox, stay unflagged because they can be the provider's route.
        self.cert_error = cert_error


def http_get_json(url: str, timeout: float = HTTP_TIMEOUT_S) -> tuple[Any, float]:
    req = urllib.request.Request(  # noqa: S310 - only the constant https URLs above
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - constant https URLs
            body = resp.read(MAX_BODY_BYTES + 1)
    except urllib.error.HTTPError as exc:
        raise HttpFailure(f"HTTP {exc.code}", status=exc.code) from exc
    except urllib.error.URLError as exc:
        reason = exc.reason
        cert = None
        if isinstance(reason, ssl.SSLCertVerificationError):
            cert = _clip(getattr(reason, "verify_message", None) or "") or "certificate verify failed"
        raise HttpFailure(short_error(reason), cert_error=cert) from exc
    except (OSError, http.client.HTTPException) as exc:  # e.g. the link drops while reading the body
        raise HttpFailure(short_error(exc)) from exc
    ms = (time.perf_counter() - t0) * 1000
    if len(body) > MAX_BODY_BYTES:
        raise HttpFailure(Msg("error.too_big"), status=200)
    try:
        return json.loads(body), ms
    except (ValueError, RecursionError) as exc:  # RecursionError: nesting deeper than the parser's stack
        raise HttpFailure(Msg("error.not_json"), status=200) from exc


def parallel[T, R](func: Callable[[T], R], items: Iterable[T], workers: int = 16) -> list[R]:
    items = list(items)
    if not items:
        return []
    with ThreadPoolExecutor(max_workers=min(workers, len(items))) as pool:
        return list(pool.map(func, items))


def fmt_ms(ms: float) -> str:
    return "<1 ms" if ms < 1 else f"{ms:.0f} ms"


# --------------------------------------------------------------------------- #
# 1. Internet
# --------------------------------------------------------------------------- #
def check_internet(ctx: Context) -> CheckResult:
    results = parallel(lambda p: tcp_probe(p[0], p[1]), INTERNET_PROBES)
    details: list[str] = []
    ok: list[float] = []
    for (ip, port, name), (ms, err) in zip(INTERNET_PROBES, results):
        if ms is None:
            details.append(Msg("check.probe_failed", target=f"{name} ({ip}:{port})", error=err))
        else:
            details.append(f"{name} ({ip}:{port}) — {fmt_ms(ms)}")
            ok.append(ms)

    ctx.internet_ok = bool(ok)
    if not ok:
        return CheckResult("internet", Status.FAIL, Msg("check.internet.fail"), details)
    return CheckResult(
        "internet",
        Status.OK,
        Msg("check.internet.ok", ok=len(ok), total=len(INTERNET_PROBES), ms=fmt_ms(min(ok))),
        details,
        latency_ms=min(ok),
    )


# --------------------------------------------------------------------------- #
# 2. DNS
# --------------------------------------------------------------------------- #
def _resolve(name: str) -> tuple[str | None, float | None, str | None]:
    t0 = time.perf_counter()
    try:
        infos = socket.getaddrinfo(name, 443, socket.AF_INET, socket.SOCK_STREAM)
    except OSError as exc:
        return None, None, short_error(exc)
    return infos[0][4][0], (time.perf_counter() - t0) * 1000, None


def check_dns(ctx: Context) -> CheckResult:
    names = STEAM_DNS_NAMES + OTHER_DNS_NAMES
    results = parallel(_resolve, names)
    details: list[str] = []
    failed: list[str] = []
    times: list[float] = []
    for name, (ip, ms, err) in zip(names, results):
        if ip is None:
            failed.append(name)
            details.append(Msg("check.dns.name_failed", name=name, error=err))
        else:
            times.append(ms or 0.0)
            details.append(f"{name} → {ip} ({fmt_ms(ms or 0.0)})")

    steam_failed = any(n in failed for n in STEAM_DNS_NAMES)
    if len(failed) == len(names):
        return CheckResult("dns", Status.FAIL, Msg("check.dns.fail"), details, data={"steam_dns_fail": True})
    if failed:
        return CheckResult(
            "dns",
            Status.WARN,
            Msg("check.dns.some_failed", names=", ".join(failed)),
            details,
            data={"steam_dns_fail": steam_failed},
        )
    return CheckResult("dns", Status.OK, Msg("check.dns.ok", ms=fmt_ms(max(times))), details,
                       latency_ms=max(times))


# --------------------------------------------------------------------------- #
# 3. Steam Web API
# --------------------------------------------------------------------------- #
def check_steam_api(ctx: Context) -> CheckResult:
    try:
        data, ms = http_get_json(CM_LIST_URL)
    except HttpFailure as exc:
        if exc.status is not None:
            # We reached Valve, but Valve answered with an error.
            return CheckResult(
                "steam_api",
                Status.WARN,
                Msg("check.steam_api.server_error", error=exc.message),
                [CM_LIST_URL],
                data={"reached": True, "server_error": True},
            )
        if exc.cert_error:
            # The certificate presented for Valve's name was rejected, so we can't tell whether Valve was
            # reached at all. Usually the PC or a captive portal, not the provider's route.
            return CheckResult(
                "steam_api",
                Status.FAIL,
                Msg("check.steam_api.cert_error", error=exc.message),
                [CM_LIST_URL, Msg("check.steam_api.certificate", reason=exc.cert_error)],
                data={"reached": False, "cert_error": True},
            )
        return CheckResult(
            "steam_api",
            Status.FAIL,
            Msg("check.steam_api.unreachable", error=exc.message),
            [CM_LIST_URL],
            data={"reached": False},
        )

    response = data.get("response") if isinstance(data, dict) else None
    servers = response.get("serverlist") if isinstance(response, dict) else None
    servers = [s for s in servers if isinstance(s, dict)] if isinstance(servers, list) else []
    if not servers:
        return CheckResult(
            "steam_api",
            Status.WARN,
            Msg("check.steam_api.empty"),
            data={"reached": True, "server_error": True},
        )

    ctx.cm_servers = servers
    dcs: list[str] = []
    for s in servers:
        dc = _valve_text(s.get("dc"))
        if dc and dc not in dcs:
            dcs.append(dc)
            if len(dcs) == SHOWN_DATA_CENTERS:  # all that is shown; a longer search is wasted (rule 3)
                break
    return CheckResult(
        "steam_api",
        Status.OK,
        Msg("check.steam_api.ok", ms=fmt_ms(ms), count=len(servers)),
        [Msg("check.steam_api.data_centers", dcs=", ".join(dcs))] if dcs else [],
        latency_ms=ms,
        data={"reached": True},
    )


# --------------------------------------------------------------------------- #
# 4. Steam login (CM) servers
# --------------------------------------------------------------------------- #
def pick_cm_targets(servers: list[dict[str, Any]], limit: int = CM_TARGETS) -> list[tuple[str, int, str]]:
    websockets = [s for s in servers if s.get("type") == "websockets"]
    pool = websockets or servers
    out: list[tuple[str, int, str]] = []
    for s in pool:
        endpoint = _valve_text(s.get("endpoint"), MAX_HOSTNAME_CHARS + 7)  # host, trailing ".", ":", port
        host, sep, port = (endpoint or "").rpartition(":")
        host = _host(host) if sep and host else None
        # ASCII digits only: "²".isdigit() is true, but int("²") raises.
        if not host or not (port.isascii() and port.isdigit() and 0 < int(port) <= 65535):
            continue
        out.append((host, int(port), _valve_text(s.get("dc")) or "?"))
        if len(out) >= limit:
            break
    return out


def check_steam_cm(ctx: Context) -> CheckResult:
    targets = pick_cm_targets(ctx.cm_servers)
    fallback = not targets
    if fallback:
        targets = STEAM_FALLBACK_HOSTS

    results = parallel(lambda t: tcp_probe(t[0], t[1]), targets)
    details: list[str] = []
    ok: list[float] = []
    for (host, port, dc), (ms, err) in zip(targets, results):
        label = f"{host}:{port} [{dc}]"
        if ms is None:
            details.append(Msg("check.probe_failed", target=label, error=err))
        else:
            ok.append(ms)
            details.append(f"{label} — {fmt_ms(ms)}")
    if fallback:
        details.insert(0, Msg("check.steam_cm.fallback"))

    n_ok, n = len(ok), len(targets)
    data = {"fallback": fallback, "ok": n_ok, "total": n}
    # Separate keys for the login and the web servers: a language inflects the words around them differently.
    if n_ok == 0:
        summary = Msg("check.steam_cm.web_fail") if fallback else Msg("check.steam_cm.fail")
        return CheckResult("steam_cm", Status.FAIL, summary, details, data=data)
    median = statistics.median(ok)
    if n_ok * 2 >= n:
        shown = fmt_ms(median)
        summary = (Msg("check.steam_cm.web_ok", ok=n_ok, total=n, ms=shown) if fallback
                   else Msg("check.steam_cm.ok", ok=n_ok, total=n, ms=shown))
        return CheckResult("steam_cm", Status.OK, summary, details, latency_ms=median, data=data)
    return CheckResult("steam_cm", Status.WARN, Msg("check.steam_cm.partial", ok=n_ok, total=n), details,
                       latency_ms=median, data=data)


# --------------------------------------------------------------------------- #
# 5. Dota 2 Game Coordinator (indirect, through the Web API)
# --------------------------------------------------------------------------- #
GC_VERSION_MAX_CHARS = 20  # Valve's version is a number; anything longer is not one


def _gc_note() -> list[str]:
    # Made on every call, not once at import, so it is in the language of the run.
    return [Msg("check.dota_gc.note")]


def _gc_version(result: dict[str, Any]) -> str | None:
    """Valve's GC version as short text, or None when it is missing or not a number / short string."""
    for name in ("active_version", "deploy_version"):
        value = result.get(name)
        if not value or isinstance(value, bool):  # 0 / "" mean "no version": try the next one
            continue
        text = _valve_text(str(value) if isinstance(value, int) else value, GC_VERSION_MAX_CHARS)
        if text:
            return text
    return None


def check_dota_gc(ctx: Context) -> CheckResult:
    try:
        data, ms = http_get_json(GC_VERSION_URL)
    except HttpFailure as exc:
        if exc.status is not None and exc.status >= 500:
            return CheckResult("dota_gc", Status.FAIL, Msg("check.dota_gc.down", error=exc.message),
                               _gc_note(), data={"gc_down": True})
        # 4xx, bad JSON or a network error: we can't judge.
        return CheckResult("dota_gc", Status.SKIP, Msg("check.dota_gc.unknown", error=exc.message), _gc_note(),
                           data={"unknown": True})

    result = data.get("result") if isinstance(data, dict) else None
    if not isinstance(result, dict) or "success" not in result:
        return CheckResult("dota_gc", Status.SKIP, Msg("check.dota_gc.bad_answer"),
                           _gc_note(), data={"unknown": True})
    if result.get("success") is not True:
        return CheckResult("dota_gc", Status.FAIL, Msg("check.dota_gc.down", error="success = false"),
                           _gc_note(), data={"gc_down": True})

    version = _gc_version(result)
    summary = (Msg("check.dota_gc.ok_version", ms=fmt_ms(ms), version=version) if version
               else Msg("check.dota_gc.ok", ms=fmt_ms(ms)))
    return CheckResult("dota_gc", Status.OK, summary, _gc_note(), latency_ms=ms)


# --------------------------------------------------------------------------- #
# 6. Valve game network (SDR relays): ping, packet loss, jitter
# --------------------------------------------------------------------------- #
def parse_sdr_pops(cfg: Any) -> list[Pop]:
    """Valve's relay sites with one IPv4 address each. Entries of the wrong type are skipped, not trusted."""
    pops = cfg.get("pops") if isinstance(cfg, dict) else None
    if not isinstance(pops, dict):
        return []
    out: list[Pop] = []
    for key, pop in pops.items():
        code = _valve_text(key)
        relays = pop.get("relays") if isinstance(pop, dict) else None
        if not code or not isinstance(relays, list):
            continue
        # A strict address, or the site is skipped: one that can't be pinged would look like a routing problem.
        ip = next((addr for r in relays if isinstance(r, dict) and (addr := _ipv4(r.get("ipv4")))), None)
        if ip:
            out.append(Pop(code, _valve_text(pop.get("desc")) or code, ip))
    return out


@dataclass
class Quality:
    pop: Pop
    sent: int
    received: int
    avg_ms: float | None
    jitter_ms: float | None

    @property
    def loss_pct(self) -> float:
        return 100.0 * (self.sent - self.received) / self.sent if self.sent else 0.0


def measure_quality(pop: Pop, count: int = QUALITY_PINGS) -> Quality:
    rtts = icmp.ping_series(pop.ip, count)
    got = [r for r in rtts if r is not None]
    avg = statistics.fmean(got) if got else None
    jitter = statistics.fmean(abs(a - b) for a, b in pairwise(got)) if len(got) >= 2 else None
    return Quality(pop, count, len(got), avg, jitter)


def check_relays(ctx: Context) -> CheckResult:
    try:
        cfg, _ = http_get_json(SDR_CONFIG_URL)
    except HttpFailure as exc:
        return CheckResult("relays", Status.SKIP, Msg("check.relays.list_failed", error=exc.message))
    pops = parse_sdr_pops(cfg)
    if not pops:
        return CheckResult("relays", Status.SKIP, Msg("check.relays.empty"))
    if len(pops) > MAX_POPS:
        return CheckResult("relays", Status.SKIP, Msg("check.relays.list_failed", error=Msg("error.too_big")))

    control = parallel(icmp.ping, CONTROL_PING_IPS)
    first = parallel(lambda p: icmp.ping(p.ip), pops, workers=24)
    rtt = dict(zip(pops, first))
    missing = [p for p in pops if rtt[p] is None]
    for pop, value in zip(missing, parallel(lambda p: icmp.ping(p.ip), missing, workers=24)):
        rtt[pop] = value

    responding = sorted((p for p in pops if rtt[p] is not None), key=lambda p: rtt[p])
    control_ok = any(c is not None for c in control)
    if not responding:
        if control_ok:
            return CheckResult(
                "relays",
                Status.WARN,
                Msg("check.relays.routing"),
                [Msg("check.relays.checked", count=len(pops))],
                data={"routing": True},
            )
        return CheckResult(
            "relays",
            Status.SKIP,
            Msg("check.relays.icmp_blocked"),
            data={"icmp_blocked": True},
        )

    details: list[str] = [f"{p.desc} ({p.code}) — {fmt_ms(rtt[p] or 0.0)}" for p in responding[:6]]
    details.append(Msg("check.relays.responded", ok=len(responding), total=len(pops)))

    quality = parallel(measure_quality, responding[:QUALITY_POPS])
    for q in quality:
        avg = fmt_ms(q.avg_ms) if q.avg_ms is not None else "—"
        jit = fmt_ms(q.jitter_ms) if q.jitter_ms is not None else "—"
        details.append(
            Msg("check.relays.quality", pop=q.pop.desc, sent=q.sent, loss=q.loss_pct, avg=avg, jitter=jit)
        )

    total_sent = sum(q.sent for q in quality)
    total_recv = sum(q.received for q in quality)
    loss = 100.0 * (total_sent - total_recv) / total_sent if total_sent else 0.0
    best = min((q for q in quality if q.avg_ms is not None), key=lambda q: q.avg_ms or 0.0, default=None)
    best_ms = best.avg_ms if best and best.avg_ms is not None else (rtt[responding[0]] or 0.0)
    best_name = best.pop.desc if best else responding[0].desc
    jitters = [q.jitter_ms for q in quality if q.jitter_ms is not None]
    jitter = min(jitters) if jitters else 0.0
    data = {"loss": round(loss, 1), "best_ms": round(best_ms, 1), "jitter": round(jitter, 1)}

    if loss > LOSS_WARN_PCT:
        return CheckResult("relays", Status.WARN, Msg("check.relays.lossy", loss=loss),
                           details, latency_ms=best_ms, data=data | {"lossy": True})
    if best_ms > HIGH_PING_MS:
        return CheckResult("relays", Status.WARN, Msg("check.relays.high_ping", ms=fmt_ms(best_ms), pop=best_name),
                           details, latency_ms=best_ms, data=data | {"high_ping": True})
    if jitter > JITTER_WARN_MS:
        return CheckResult("relays", Status.WARN, Msg("check.relays.jittery", ms=fmt_ms(jitter)),
                           details, latency_ms=best_ms, data=data | {"jittery": True})
    return CheckResult(
        "relays",
        Status.OK,
        Msg("check.relays.ok", pop=best_name, ms=fmt_ms(best_ms), loss=loss),
        details,
        latency_ms=best_ms,
        data=data,
    )


# --------------------------------------------------------------------------- #
# Runner
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class CheckSpec:
    key: str
    title_key: str  # i18n keys; `title` and `hint` look them up in the language current when they are read
    hint_key: str
    func: Callable[[Context], CheckResult]

    @property
    def title(self) -> str:
        return Msg(self.title_key)  # a Msg, so `CheckResult.title` can be shown again in another language

    @property
    def hint(self) -> str:
        return Msg(self.hint_key)


CHECKS: list[CheckSpec] = [
    CheckSpec("internet", "check.internet.title", "check.internet.hint", check_internet),
    CheckSpec("dns", "check.dns.title", "check.dns.hint", check_dns),
    CheckSpec("steam_api", "check.steam_api.title", "check.steam_api.hint", check_steam_api),
    CheckSpec("steam_cm", "check.steam_cm.title", "check.steam_cm.hint", check_steam_cm),
    CheckSpec("dota_gc", "check.dota_gc.title", "check.dota_gc.hint", check_dota_gc),
    CheckSpec("relays", "check.relays.title", "check.relays.hint", check_relays),
]


def run_checks(
    on_start: Callable[[CheckSpec], None] | None = None,
    on_result: Callable[[CheckResult], None] | None = None,
) -> dict[str, CheckResult]:
    ctx = Context()
    results: dict[str, CheckResult] = {}
    for spec in CHECKS:
        if on_start:
            on_start(spec)
        if not ctx.internet_ok:
            res = CheckResult(spec.key, Status.SKIP, Msg("check.skipped_no_internet"))
        else:
            try:
                res = spec.func(ctx)
            except Exception as exc:  # noqa: BLE001 - a bug in a check must not kill the run
                res = CheckResult(spec.key, Status.SKIP, Msg("check.internal_error", error=short_error(exc)))
        res.title = spec.title
        results[spec.key] = res
        if on_result:
            on_result(res)
    return results
