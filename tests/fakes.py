"""A fake network so the checks can be tested without internet."""

from __future__ import annotations

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


class FakeNet:
    """Each attribute is a knob a test can turn to break one part of the network."""

    def __init__(self) -> None:
        self.internet = True
        self.dns = True
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
            return None, "timeout"
        if host[0].isdigit() and host.count(".") == 3 and host in CONTROL | {"9.9.9.9": 0}:
            return 12.0, None
        if not self.dns:
            return None, "DNS-ը չգտավ հասցեն"
        return (35.0, None) if self.tcp_ok else (None, "timeout")

    def resolve(self, name):
        if self.internet and self.dns:
            return "1.2.3.4", 4.0, None
        return None, None, "DNS-ը չգտավ հասցեն"

    def http_get_json(self, url, timeout=0):
        if not (self.internet and self.dns and self.tcp_ok):
            raise checks.HttpFailure("timeout")
        if not self.cert_ok:
            raise checks.HttpFailure("SSL սխալ", cert_error="certificate has expired")
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
