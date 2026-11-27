"""Low-level helpers: HTTP error classification, the ping command, version sync."""

from __future__ import annotations

import http.client
import json
import shutil
import socket
import ssl
import subprocess
import sysconfig
import tomllib
import urllib.error
from collections.abc import Callable
from pathlib import Path

import pytest

import wholagged
from wholagged import checks, icmp
from wholagged.i18n import Msg


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


def _certificate_failure(monkeypatch, verify_message) -> checks.HttpFailure:
    cert_error = ssl.SSLCertVerificationError(1, "certificate verify failed")
    cert_error.verify_message = verify_message  # OpenSSL's reason, from whatever certificate was presented
    monkeypatch.setattr(checks.urllib.request, "urlopen", _raise(urllib.error.URLError(cert_error)))
    with pytest.raises(checks.HttpFailure) as info:
        checks.http_get_json("https://example.invalid/")
    return info.value


@pytest.mark.parametrize(
    ("verify_message", "expected"),
    [
        ("certificate has expired", "certificate has expired"),
        ("certificate has expired\r\n[OK] Valve: fine", "certificate has expired [OK] Valve: fine"),
        ("self-signed\x1b[2J certificate", "self-signed [2J certificate"),
        ("x" * 200, "x" * 69 + "…"),
    ],
    ids=["plain", "line-break", "terminal-escape", "long"],
)
def test_certificate_reason_is_one_printable_line(monkeypatch, verify_message, expected):
    failure = _certificate_failure(monkeypatch, verify_message)
    assert failure.cert_error == expected
    assert failure.cert_error.isprintable()
    assert len(failure.cert_error.splitlines()) == 1


@pytest.mark.parametrize("verify_message", ["\r\n", "\x00\x1b", "   ", "", None], ids=repr)
def test_certificate_reason_without_printable_text_still_flags_the_certificate(monkeypatch, verify_message):
    failure = _certificate_failure(monkeypatch, verify_message)
    assert failure.cert_error == "certificate verify failed"  # truthy: the verdict still says "certificate"
    assert failure.status is None


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


def _answer(body: Callable[[int], bytes]):
    """A fake `urlopen` whose response body is `body(n)` for `read(n)`."""

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self, n):
            return body(n)

    return lambda *a, **k: Response()


DEEP_JSON = b"[" * 200_000  # far below MAX_BODY_BYTES, far deeper than the JSON parser's stack


def test_deep_json_raises_recursion_error_in_the_parser():
    # Why the "too-deep" case below matters: json.loads doesn't raise ValueError for this, it overflows.
    assert len(DEEP_JSON) < checks.MAX_BODY_BYTES
    with pytest.raises(RecursionError):
        json.loads(DEEP_JSON)


@pytest.mark.parametrize(
    ("body", "key"),
    [
        (lambda n: b"x" * n, "error.too_big"),
        (lambda n: b"<html>Service Unavailable</html>", "error.not_json"),
        (lambda n: DEEP_JSON, "error.not_json"),  # a RecursionError, not a crash of the check
        (lambda n: b'{"a": ' * 100_000, "error.not_json"),
    ],
    ids=["too-big", "not-json", "too-deep", "too-deep-objects"],
)
def test_bad_answer_keeps_its_reason_as_a_msg(monkeypatch, body, key):
    monkeypatch.setattr(checks.urllib.request, "urlopen", _answer(body))
    with pytest.raises(checks.HttpFailure) as info:
        checks.http_get_json("https://example.invalid/")
    message = info.value.message
    assert isinstance(message, Msg)  # `str(exc)` would have flattened it to one language
    assert message.key == key
    assert str(info.value) == message  # code that formats the exception still gets the text
    assert info.value.status == 200
    assert info.value.cert_error is None


@pytest.mark.parametrize(
    ("raised", "key"),
    [
        (urllib.error.URLError(TimeoutError()), "error.timeout"),
        (urllib.error.URLError(socket.gaierror(11001, "getaddrinfo failed")), "error.dns"),
        (urllib.error.URLError(ConnectionRefusedError(10061, "refused")), "error.refused"),
        (urllib.error.URLError(ssl.SSLCertVerificationError(1, "certificate verify failed")), "error.ssl"),
        (urllib.error.URLError(ssl.SSLEOFError(8, "EOF occurred in violation of protocol")), "error.ssl"),
        (ConnectionResetError(10054, "reset"), "error.reset"),  # the link drops while the body is read
    ],
    ids=["timeout", "dns", "refused", "certificate", "handshake-cut", "reset"],
)
def test_network_failure_keeps_the_error_word_as_a_msg(monkeypatch, raised, key):
    monkeypatch.setattr(checks.urllib.request, "urlopen", _raise(raised))
    with pytest.raises(checks.HttpFailure) as info:
        checks.http_get_json("https://example.invalid/")
    assert isinstance(info.value.message, Msg)
    assert info.value.message.key == key
    assert info.value.status is None


def test_http_error_message_is_the_status_code(monkeypatch):
    error = urllib.error.HTTPError("https://example.invalid/", 503, "Service Unavailable", None, None)
    monkeypatch.setattr(checks.urllib.request, "urlopen", _raise(error))
    with pytest.raises(checks.HttpFailure) as info:
        checks.http_get_json("https://example.invalid/")
    assert info.value.message == "HTTP 503"
    assert not isinstance(info.value.message, Msg)  # a status code, the same in every language
    assert info.value.status == 503


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


def test_network_identity_uses_the_new_name():
    """Valve sees `wholagged/<version>`; the ICMP echo payload names us and stays 32 bytes like Windows ping (WL-13)."""
    assert checks.USER_AGENT == f"wholagged/{wholagged.__version__}"
    assert icmp._PAYLOAD.startswith(b"wholagged")
    assert len(icmp._PAYLOAD) == 32


def test_both_commands_start_the_same_app():
    """`wholagged` is the command; `dota-netcheck` stays as an alias so old commands keep working (WL-12)."""
    project = tomllib.loads((Path(__file__).parents[1] / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["name"] == "wholagged"
    assert project["scripts"] == {"wholagged": "wholagged:main", "dota-netcheck": "wholagged:main"}
    assert callable(wholagged.main)


def test_both_commands_are_installed():
    """The scripts exist in this environment, not just in pyproject.toml (a rename can delete one, WL-12)."""
    scripts = sysconfig.get_path("scripts")
    missing = [name for name in ("wholagged", "dota-netcheck") if shutil.which(name, path=scripts) is None]
    assert not missing, f"{missing} not in {scripts}: run `uv sync --reinstall-package wholagged`"
