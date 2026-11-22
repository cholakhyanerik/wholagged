"""Low-level helpers: HTTP error classification, the ping command, version sync."""

from __future__ import annotations

import http.client
import ssl
import subprocess
import tomllib
import urllib.error
from pathlib import Path

import pytest

import wholagged
from wholagged import checks, icmp


def _raise(exc: BaseException):
    def fake_urlopen(*args, **kwargs):
        raise exc

    return fake_urlopen


def test_certificate_error_is_flagged(monkeypatch):
    cert_error = ssl.SSLCertVerificationError(1, "certificate verify failed")
    monkeypatch.setattr(checks.urllib.request, "urlopen", _raise(urllib.error.URLError(cert_error)))
    with pytest.raises(checks.HttpFailure) as info:
        checks.http_get_json("https://example.invalid/")
    assert info.value.cert_error
    assert info.value.status is None


def test_cut_off_handshake_is_not_a_certificate_error(monkeypatch):
    # A middlebox closing the connection mid-handshake can be the provider: no "your PC" verdict.
    eof = ssl.SSLEOFError(8, "EOF occurred in violation of protocol")
    monkeypatch.setattr(checks.urllib.request, "urlopen", _raise(urllib.error.URLError(eof)))
    with pytest.raises(checks.HttpFailure) as info:
        checks.http_get_json("https://example.invalid/")
    assert info.value.cert_error is None


def test_broken_body_becomes_an_http_failure(monkeypatch):
    monkeypatch.setattr(checks.urllib.request, "urlopen", _raise(http.client.IncompleteRead(b"")))
    with pytest.raises(checks.HttpFailure):
        checks.http_get_json("https://example.invalid/")


def test_oversized_answer_is_refused(monkeypatch):
    class Big:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self, n):
            return b"x" * n

    monkeypatch.setattr(checks.urllib.request, "urlopen", lambda *a, **k: Big())
    with pytest.raises(checks.HttpFailure) as info:
        checks.http_get_json("https://example.invalid/")
    assert info.value.status == 200


def test_plain_network_error_is_not_tls(monkeypatch):
    monkeypatch.setattr(checks.urllib.request, "urlopen", _raise(urllib.error.URLError(TimeoutError())))
    with pytest.raises(checks.HttpFailure) as info:
        checks.http_get_json("https://example.invalid/")
    assert info.value.cert_error is None
    assert str(info.value) == "timeout"


def test_ping_command_uses_milliseconds_on_macos():
    assert icmp.ping_command("1.1.1.1", 1000, platform="darwin") == ["ping", "-c", "1", "-W", "1000", "1.1.1.1"]


def test_ping_command_uses_seconds_on_linux():
    assert icmp.ping_command("1.1.1.1", 1000, platform="linux") == ["ping", "-c", "1", "-W", "1", "1.1.1.1"]
    assert icmp.ping_command("1.1.1.1", 200, platform="linux")[4] == "1"  # never 0 (= wait forever)


def test_ping_subprocess_runs_in_a_neutral_locale(monkeypatch):
    seen = {}

    def fake_run(args, **kwargs):
        seen.update(kwargs)
        return subprocess.CompletedProcess(args, 0, stdout="64 bytes: icmp_seq=0 ttl=57 time=12.5 ms\n")

    monkeypatch.setattr(icmp.subprocess, "run", fake_run)
    assert icmp._ping_subprocess("1.1.1.1", 1000) == 12.5
    assert seen["env"]["LC_ALL"] == "C"


@pytest.mark.parametrize("bad", ["1", "127.1", "1.2.3.4 -c 9", "", None, 5, "::1"])
def test_ping_rejects_anything_but_a_plain_ipv4(bad):
    assert icmp.ping(bad) is None


def test_version_is_the_same_everywhere():
    pyproject = tomllib.loads((Path(__file__).parents[1] / "pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["project"]["version"] == wholagged.__version__
    assert checks.USER_AGENT.endswith("/" + wholagged.__version__)


def test_product_name_is_wholagged():
    assert wholagged.APP_NAME == "wholagged"
