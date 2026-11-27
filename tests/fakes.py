"""A fake network so the checks can be tested without internet."""

from __future__ import annotations

import socket
import ssl
from urllib.parse import urlsplit

from wholagged import checks, icmp

CM_LIST = {
    "response": {
        "serverlist": [
            {"endpoint": "ext1-fra1.steamserver.net:27019", "type": "websockets", "dc": "fra1"},
            {"endpoint": "ext2-fra1.steamserver.net:27019", "type": "websockets", "dc": "fra1"},
            {"endpoint": "ext1-sto1.steamserver.net:27019", "type": "websockets", "dc": "sto1"},
            {"endpoint": "ext1-vie1.steamserver.net:443", "type": "websockets", "dc": "vie1"},
            {"endpoint": "155.133.248.34:27017", "type": "netfilter", "dc": "fra1"},
        ],
        "success": True,
    }
}
SDR = {
    "revision": 1,
    "pops": {
        "sto": {"desc": "Stockholm", "relays": [{"ipv4": "155.133.226.1", "port_range": [27015, 27060]}]},
        "vie": {"desc": "Vienna", "relays": [{"ipv4": "155.133.226.2", "port_range": [27015, 27060]}]},
        "fra": {"desc": "Frankfurt", "relays": [{"ipv4": "155.133.226.3", "port_range": [27015, 27060]}]},
        "dxb": {"desc": "Dubai", "relays": [{"ipv4": "155.133.226.4", "port_range": [27015, 27060]}]},
        "sgp": {"desc": "Singapore", "relays": [{"ipv4": "155.133.226.5", "port_range": [27015, 27060]}]},
        "nocfg": {"desc": "No relays"},
    },
}
GC_OK = {"result": {"success": True, "deploy_version": 7001, "active_version": 7001}}
RELAY_MS = {
    "155.133.226.1": 58.0,
    "155.133.226.2": 47.0,
    "155.133.226.3": 52.0,
    "155.133.226.4": 71.0,
    "155.133.226.5": 160.0,
}
CONTROL = {"1.1.1.1": 9.0, "8.8.8.8": 11.0}
LOOPBACK_MS = 0.1


# The error words the real helpers give: `short_error()` of the exception they would catch, so the fake
# network returns the same `i18n.Msg` texts as production, in the language current when the check runs.
def _timeout() -> str:
    return checks.short_error(TimeoutError())


def _no_such_name() -> str:
    return checks.short_error(socket.gaierror())


def _bad_certificate() -> str:
    return checks.short_error(ssl.SSLCertVerificationError(1, "certificate verify failed"))


def _refused() -> str:
    return checks.short_error(ConnectionRefusedError())


class FakeNet:
    """Each attribute is a knob a test can turn to break one part of the network."""

    def __init__(self) -> None:
        self.internet = True
        self.dns = True
        self.unresolved: set[str] = set()  # names that don't resolve while the rest of DNS works
        self.refused_hosts: set[str] = set()  # names that resolve but refuse TCP (a firewall, a blocked route)
        # url -> the JSON answer; an int is that HTTP status; an exception is raised as is (a bug in the check)
        self.http: dict[str, object] = {
            checks.CM_LIST_URL: CM_LIST,
            checks.SDR_CONFIG_URL: SDR,
            checks.GC_VERSION_URL: GC_OK,
        }
        self.tcp_ok = True
        self.cert_ok = True  # False: HTTPS certificate check fails (clock, antivirus, captive portal)
        self.relays_ok = True
        self.control_ok = True
        self.loss_every: int | None = None  # drop every Nth ping to each relay
        self.relay_extra_ms = 0.0
        self.relay_jitter_ms = 0.0  # every 2nd ping to each relay is this much slower; control pings aren't
        # Pings per relay IP. Counted per IP, not in total: the relays are pinged in parallel threads, and a
        # shared counter would hand out the dropped or slow pings in whatever order the threads ran.
        self._pings: dict[str, int] = {}
        self.pinged: list[str] = []  # every ping, control ones too, for "no ping was sent" asserts

    def install(self, monkeypatch) -> FakeNet:
        monkeypatch.setattr(checks, "tcp_probe", self.tcp_probe)
        monkeypatch.setattr(checks, "_resolve", self.resolve)
        monkeypatch.setattr(checks, "http_get_json", self.http_get_json)
        monkeypatch.setattr(icmp, "ping", self.ping)
        monkeypatch.setattr(icmp.time, "sleep", lambda s: None)
        return self

    def tcp_probe(self, host, port, timeout=0):
        if not self.internet:
            return None, _timeout()
        if host[0].isdigit() and host.count(".") == 3 and host in CONTROL | {"9.9.9.9": 0}:
            return 12.0, None
        if not self.dns or host in self.unresolved:
            return None, _no_such_name()
        if host in self.refused_hosts:
            return None, _refused()
        return (35.0, None) if self.tcp_ok else (None, _timeout())

    def resolve(self, name):
        if self.internet and self.dns and name not in self.unresolved:
            return "1.2.3.4", 4.0, None
        return None, None, _no_such_name()

    def http_get_json(self, url, timeout=0):
        if not (self.internet and self.dns and self.tcp_ok):
            raise checks.HttpFailure(_timeout())
        host = urlsplit(url).hostname
        if host in self.unresolved:
            raise checks.HttpFailure(_no_such_name())
        if host in self.refused_hosts:
            raise checks.HttpFailure(_refused())
        if not self.cert_ok:
            raise checks.HttpFailure(_bad_certificate(), cert_error="certificate has expired")
        value = self.http[url]
        if isinstance(value, BaseException):
            raise value
        if isinstance(value, int):
            raise checks.HttpFailure(f"HTTP {value}", status=value)
        return value, 120.0

    def ping(self, ip, timeout_ms=1000):
        self.pinged.append(ip)  # list.append is atomic: safe from the ping threads
        if ip.startswith("127."):
            return LOOPBACK_MS  # the PC itself answers, whatever the network does
        if not self.internet:
            return None
        if ip in CONTROL:
            return CONTROL[ip] if self.control_ok else None
        if not self.relays_ok:
            return None
        n = self._pings[ip] = self._pings.get(ip, 0) + 1  # one thread at a time pings a given relay
        if self.loss_every and n % self.loss_every == 0:
            return None
        base = RELAY_MS.get(ip)
        if base is None:
            return None
        return base + self.relay_extra_ms + (self.relay_jitter_ms if n % 2 == 0 else 0.0)
