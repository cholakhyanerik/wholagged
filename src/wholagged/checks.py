"""Network checks: who is to blame, your internet or Valve's servers.

Every check function takes a shared Context and returns a CheckResult.
Only the standard library is used here, so the module also runs without Qt
(`uv run wholagged --cli`).
"""

from __future__ import annotations

import http.client
import json
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
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def short_error(exc: BaseException | str) -> str:
    if isinstance(exc, str):
        return _clip(exc)
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return "timeout"
    if isinstance(exc, ConnectionRefusedError):
        return "կապը մերժվեց"
    if isinstance(exc, ConnectionResetError):
        return "կապը խզվեց"
    if isinstance(exc, socket.gaierror):
        return "DNS-ը չգտավ հասցեն"
    if isinstance(exc, ssl.SSLError):
        return "SSL սխալ"
    if isinstance(exc, OSError) and exc.strerror:
        return _clip(exc.strerror)
    return _clip(str(exc) or type(exc).__name__)


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
            cert = getattr(reason, "verify_message", None) or "certificate verify failed"
        raise HttpFailure(short_error(reason), cert_error=cert) from exc
    except (OSError, http.client.HTTPException) as exc:  # e.g. the link drops while reading the body
        raise HttpFailure(short_error(exc)) from exc
    ms = (time.perf_counter() - t0) * 1000
    if len(body) > MAX_BODY_BYTES:
        raise HttpFailure("պատասխանը չափազանց մեծ է", status=200)
    try:
        return json.loads(body), ms
    except ValueError as exc:
        raise HttpFailure("պատասխանը JSON չէ", status=200) from exc


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
            details.append(f"{name} ({ip}:{port}) — չհաջողվեց ({err})")
        else:
            details.append(f"{name} ({ip}:{port}) — {fmt_ms(ms)}")
            ok.append(ms)

    ctx.internet_ok = bool(ok)
    if not ok:
        return CheckResult(
            "internet",
            Status.FAIL,
            "Internet չկա. ոչ մի արտաքին սերվերի չհաջողվեց միանալ",
            details,
        )
    return CheckResult(
        "internet",
        Status.OK,
        f"Internet-ն աշխատում է ({len(ok)}/{len(INTERNET_PROBES)}, {fmt_ms(min(ok))})",
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
            details.append(f"{name} — չլուծվեց ({err})")
        else:
            times.append(ms or 0.0)
            details.append(f"{name} → {ip} ({fmt_ms(ms or 0.0)})")

    steam_failed = any(n in failed for n in STEAM_DNS_NAMES)
    if len(failed) == len(names):
        return CheckResult("dns", Status.FAIL, "DNS-ը չի աշխատում. ոչ մի հասցե չլուծվեց", details,
                           data={"steam_dns_fail": True})
    if failed:
        return CheckResult(
            "dns",
            Status.WARN,
            "Որոշ հասցեներ չլուծվեցին՝ " + ", ".join(failed),
            details,
            data={"steam_dns_fail": steam_failed},
        )
    return CheckResult("dns", Status.OK, f"Բոլոր հասցեները լուծվեցին ({fmt_ms(max(times))})",
                       details, latency_ms=max(times))


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
                f"Steam-ը պատասխանեց սխալով ({exc})",
                [CM_LIST_URL],
                data={"reached": True, "server_error": True},
            )
        if exc.cert_error:
            # The certificate presented for Valve's name was rejected, so we can't tell whether Valve was
            # reached at all. Usually the PC or a captive portal, not the provider's route.
            return CheckResult(
                "steam_api",
                Status.FAIL,
                f"Steam-ի հետ անվտանգ (HTTPS) կապը չհաստատվեց ({exc})",
                [CM_LIST_URL, f"Սերտիֆիկատ՝ {exc.cert_error}"],
                data={"reached": False, "cert_error": True},
            )
        return CheckResult(
            "steam_api",
            Status.FAIL,
            f"Steam Web API-ին չհաջողվեց հասնել ({exc})",
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
            "Steam-ը պատասխանեց, բայց login սերվերների ցուցակը դատարկ է",
            data={"reached": True, "server_error": True},
        )

    ctx.cm_servers = servers
    dcs: list[str] = []
    for s in servers:
        dc = s.get("dc")
        if isinstance(dc, str) and dc and dc not in dcs:
            dcs.append(dc)
    return CheckResult(
        "steam_api",
        Status.OK,
        f"Steam Web API-ն պատասխանեց ({fmt_ms(ms)}, {len(servers)} login սերվեր)",
        [f"Ամենամոտ data center-ները՝ {', '.join(dcs[:5])}"] if dcs else [],
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
        endpoint = s.get("endpoint")
        host, sep, port = (endpoint if isinstance(endpoint, str) else "").rpartition(":")
        if not sep or not host or not port.isdigit():
            continue
        dc = s.get("dc")
        out.append((host, int(port), dc if isinstance(dc, str) and dc else "?"))
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
            details.append(f"{label} — չհաջողվեց ({err})")
        else:
            ok.append(ms)
            details.append(f"{label} — {fmt_ms(ms)}")
    if fallback:
        details.insert(0, "Login սերվերների ցուցակը չստացվեց, ստուգվում են Steam-ի web սերվերները")

    n_ok, n = len(ok), len(targets)
    data = {"fallback": fallback, "ok": n_ok, "total": n}
    what = "Steam-ի web սերվերներ" if fallback else "Steam-ի login սերվերներ"
    if n_ok == 0:
        return CheckResult("steam_cm", Status.FAIL, f"{what}ից ոչ մեկին չհաջողվեց միանալ", details, data=data)
    median = statistics.median(ok)
    if n_ok * 2 >= n:
        return CheckResult("steam_cm", Status.OK, f"{what}ը հասանելի են ({n_ok}/{n}, մեդիան {fmt_ms(median)})",
                           details, latency_ms=median, data=data)
    return CheckResult("steam_cm", Status.WARN, f"Հասանելի է միայն {n_ok}/{n} սերվեր", details,
                       latency_ms=median, data=data)


# --------------------------------------------------------------------------- #
# 5. Dota 2 Game Coordinator (indirect, through the Web API)
# --------------------------------------------------------------------------- #
GC_NOTE = "Անուղղակի ստուգում է Web API-ի միջոցով. լրիվ վստահության համար նայիր steamstat.us"


def check_dota_gc(ctx: Context) -> CheckResult:
    try:
        data, ms = http_get_json(GC_VERSION_URL)
    except HttpFailure as exc:
        if exc.status is not None and exc.status >= 500:
            return CheckResult("dota_gc", Status.FAIL, f"Dota GC-ն չի պատասխանում ({exc})",
                               [GC_NOTE], data={"gc_down": True})
        # 4xx, bad JSON or a network error: we can't judge.
        return CheckResult("dota_gc", Status.SKIP, f"Չհաջողվեց ստուգել ({exc})", [GC_NOTE],
                           data={"unknown": True})

    result = data.get("result") if isinstance(data, dict) else None
    if not isinstance(result, dict) or "success" not in result:
        return CheckResult("dota_gc", Status.SKIP, "Պատասխանը սպասված ձևով չէ. չենք կարող գնահատել",
                           [GC_NOTE], data={"unknown": True})
    if result.get("success") is not True:
        return CheckResult("dota_gc", Status.FAIL, "Dota GC-ն չի պատասխանում (success = false)",
                           [GC_NOTE], data={"gc_down": True})

    version = result.get("active_version") or result.get("deploy_version")
    suffix = f", version {version}" if version else ""
    return CheckResult("dota_gc", Status.OK, f"Dota GC-ն պատասխանում է ({fmt_ms(ms)}{suffix})",
                       [GC_NOTE], latency_ms=ms)


# --------------------------------------------------------------------------- #
# 6. Valve game network (SDR relays): ping, packet loss, jitter
# --------------------------------------------------------------------------- #
def parse_sdr_pops(cfg: Any) -> list[Pop]:
    pops = cfg.get("pops") if isinstance(cfg, dict) else None
    if not isinstance(pops, dict):
        return []
    out: list[Pop] = []
    for code, pop in pops.items():
        if not isinstance(pop, dict):
            continue
        relays = pop.get("relays") or []
        ip = next((r.get("ipv4") for r in relays if isinstance(r, dict) and r.get("ipv4")), None)
        if ip:
            out.append(Pop(code, pop.get("desc") or code, ip))
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
        return CheckResult("relays", Status.SKIP, f"Չհաջողվեց ստանալ relay-ների ցուցակը ({exc})")
    pops = parse_sdr_pops(cfg)
    if not pops:
        return CheckResult("relays", Status.SKIP, "Relay-ների ցուցակը դատարկ է")

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
                "Valve-ի relay-ները ping-ին չեն պատասխանում, թեև մնացած internet-ը պատասխանում է",
                [f"Ստուգված relay-ներ՝ {len(pops)}"],
                data={"routing": True},
            )
        return CheckResult(
            "relays",
            Status.SKIP,
            "Այս ցանցում ICMP ping-ը կարծես փակ է. relay-ները չենք կարող ստուգել",
            data={"icmp_blocked": True},
        )

    details = [f"{p.desc} ({p.code}) — {fmt_ms(rtt[p] or 0.0)}" for p in responding[:6]]
    details.append(f"Պատասխանեց {len(responding)}/{len(pops)} relay")

    quality = parallel(measure_quality, responding[:QUALITY_POPS])
    for q in quality:
        avg = fmt_ms(q.avg_ms) if q.avg_ms is not None else "—"
        jit = fmt_ms(q.jitter_ms) if q.jitter_ms is not None else "—"
        details.append(
            f"{q.pop.desc}: {q.sent} ping, կորուստ {q.loss_pct:.0f}%, միջինը {avg}, jitter {jit}"
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
        return CheckResult("relays", Status.WARN, f"Packet loss {loss:.0f}%. կապն անկայուն է",
                           details, latency_ms=best_ms, data=data | {"lossy": True})
    if best_ms > HIGH_PING_MS:
        return CheckResult("relays", Status.WARN, f"Ping-ը բարձր է՝ {fmt_ms(best_ms)} ({best_name})",
                           details, latency_ms=best_ms, data=data | {"high_ping": True})
    if jitter > JITTER_WARN_MS:
        return CheckResult("relays", Status.WARN, f"Ping-ը տատանվում է (jitter {fmt_ms(jitter)})",
                           details, latency_ms=best_ms, data=data | {"jittery": True})
    return CheckResult(
        "relays",
        Status.OK,
        f"Լավագույնը՝ {best_name}, {fmt_ms(best_ms)}, կորուստ {loss:.0f}%",
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
    title: str
    hint: str
    func: Callable[[Context], CheckResult]


CHECKS: list[CheckSpec] = [
    CheckSpec("internet", "Internet կապ", "Միանում է Cloudflare, Google, Quad9 սերվերներին", check_internet),
    CheckSpec("dns", "DNS", "Լուծում է Steam-ի և Google-ի հասցեները", check_dns),
    CheckSpec("steam_api", "Steam Web API", "Valve-ից ստանում է login սերվերների ցուցակը", check_steam_api),
    CheckSpec("steam_cm", "Steam login սերվերներ", "Միանում է Steam-ի մոտակա CM սերվերներին", check_steam_cm),
    CheckSpec("dota_gc", "Dota 2 Game Coordinator", "Հարցնում է GC-ի version-ը Web API-ից", check_dota_gc),
    CheckSpec("relays", "Valve-ի խաղային ցանց", "Ping, packet loss և jitter Valve-ի relay-ներին", check_relays),
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
            res = CheckResult(spec.key, Status.SKIP, "Բաց թողնվեց, քանի որ internet չկա")
        else:
            try:
                res = spec.func(ctx)
            except Exception as exc:  # noqa: BLE001 - a bug in a check must not kill the run
                res = CheckResult(spec.key, Status.SKIP, f"Ստուգման ներքին սխալ՝ {short_error(exc)}")
        res.title = spec.title
        results[spec.key] = res
        if on_result:
            on_result(res)
    return results
