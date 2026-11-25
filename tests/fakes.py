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
        "sto": {"desc": "Stockholm", "relays": [{"ipv4": "10.0.0.1", "port_range": [27015, 27060]}]},
        "vie": {"desc": "Vienna", "relays": [{"ipv4": "10.0.0.2", "port_range": [27015, 27060]}]},
        "fra": {"desc": "Frankfurt", "relays": [{"ipv4": "10.0.0.3", "port_range": [27015, 27060]}]},
        "dxb": {"desc": "Dubai", "relays": [{"ipv4": "10.0.0.4", "port_range": [27015, 27060]}]},
        "sgp": {"desc": "Singapore", "relays": [{"ipv4": "10.0.0.5", "port_range": [27015, 27060]}]},
        "nocfg": {"desc": "No relays"},
    },
}
GC_OK = {"result": {"success": True, "deploy_version": 7001, "active_version": 7001}}
RELAY_MS = {"10.0.0.1": 58.0, "10.0.0.2": 47.0, "10.0.0.3": 52.0, "10.0.0.4": 71.0, "10.0.0.5": 160.0}
CONTROL = {"1.1.1.1": 9.0, "8.8.8.8": 11.0}


# The error words the real helpers give: `short_error()` of the exception they would catch, so the fake
# network returns the same `i18n.Msg` texts as production, in the language current when the check runs.
def _timeout() -> str:
    return checks.short_error(TimeoutError())


def _no_such_name() -> str:
    return checks.short_error(socket.gaierror())


def _bad_certificate() -> str:
    return checks.short_error(ssl.SSLCertVerificationError(1, "certificate verify failed"))


class FakeNet:
    """Each attribute is a knob a test can turn to break one part of the network."""

    def __init__(self) -> None:
        self.internet = True
        self.dns = True
        self.unresolved: set[str] = set()  # names that don't resolve while the rest of DNS works
        self.http: dict[str, object] = {
            checks.CM_LIST_URL: CM_LIST,
            checks.SDR_CONFIG_URL: SDR,
            checks.GC_VERSION_URL: GC_OK,
        }
        self.tcp_ok = True
        self.cert_ok = True  # False: HTTPS certificate check fails (clock, antivirus, captive portal)
        self.relays_ok = True
        self.control_ok = True
        self.loss_every: int | None = None  # drop every Nth relay ping
        self.relay_extra_ms = 0.0
        self._count = 0

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
        return (35.0, None) if self.tcp_ok else (None, _timeout())

    def resolve(self, name):
        if self.internet and self.dns and name not in self.unresolved:
            return "1.2.3.4", 4.0, None
        return None, None, _no_such_name()

    def http_get_json(self, url, timeout=0):
        if not (self.internet and self.dns and self.tcp_ok):
            raise checks.HttpFailure(_timeout())
        if urlsplit(url).hostname in self.unresolved:
            raise checks.HttpFailure(_no_such_name())
        if not self.cert_ok:
            raise checks.HttpFailure(_bad_certificate(), cert_error="certificate has expired")
        value = self.http[url]
        if isinstance(value, int):
            raise checks.HttpFailure(f"HTTP {value}", status=value)
        return value, 120.0

    def ping(self, ip, timeout_ms=1000):
        if not self.internet:
            return None
        if ip in CONTROL:
            return CONTROL[ip] if self.control_ok else None
        if not self.relays_ok:
            return None
        self._count += 1
        if self.loss_every and self._count % self.loss_every == 0:
            return None
        base = RELAY_MS.get(ip)
        return None if base is None else base + self.relay_extra_ms
