import errno
import socket
import ssl

import pytest

from wholagged.checks import parse_sdr_pops, pick_cm_targets, short_error
from wholagged.i18n import Msg, t

from fakes import CM_LIST, SDR


def test_pick_cm_targets_prefers_websockets():
    targets = pick_cm_targets(CM_LIST["response"]["serverlist"], limit=10)
    assert len(targets) == 4
    assert targets[0] == ("ext1-fra1.steamserver.net", 27019, "fra1")
    assert all(not host[0].isdigit() for host, _, _ in targets)


def test_pick_cm_targets_skips_bad_endpoints():
    servers = [{"endpoint": "nohost"}, {"endpoint": ":80"}, {"endpoint": "a.b:x"}, {"endpoint": "ok.host:443"}]
    assert pick_cm_targets(servers) == [("ok.host", 443, "?")]


def test_parse_sdr_pops():
    pops = parse_sdr_pops(SDR)
    assert {p.code for p in pops} == {"sto", "vie", "fra", "dxb", "sgp"}
    assert parse_sdr_pops({}) == []
    assert parse_sdr_pops("garbage") == []


def test_short_error_clips():
    assert short_error("x" * 200).endswith("…")
    assert short_error(TimeoutError()) == "timeout"


@pytest.mark.parametrize(
    ("exc", "key"),
    [
        (TimeoutError(), "error.timeout"),
        (TimeoutError("timed out"), "error.timeout"),  # socket.timeout is the same class
        (ConnectionRefusedError(10061, "No connection could be made"), "error.refused"),
        (ConnectionResetError(10054, "An existing connection was forcibly closed"), "error.reset"),
        (socket.gaierror(11001, "getaddrinfo failed"), "error.dns"),
        (socket.gaierror(), "error.dns"),
        (ssl.SSLError(1, "wrong version number"), "error.ssl"),
        (ssl.SSLCertVerificationError(1, "certificate verify failed"), "error.ssl"),
        (ssl.SSLEOFError(8, "EOF occurred in violation of protocol"), "error.ssl"),
    ],
    ids=lambda v: type(v).__name__ if isinstance(v, BaseException) else v,
)
def test_short_error_names_common_errors_in_our_own_words_even_when_the_os_has_text(exc, key):
    word = short_error(exc)
    assert isinstance(word, Msg)  # so a finished run can show it again in another language
    assert word.key == key
    assert word.params == {}
    assert word == t(key)


def test_short_error_returns_a_msg_whole_and_unclipped():
    word = Msg("error.ssl")
    assert short_error(word) is word
    long = Msg("check.probe_failed", target="Cloudflare (1.1.1.1:443) " * 4, error=Msg("error.timeout"))
    assert len(long) > 70  # longer than the clip limit for plain text
    same = short_error(long)
    assert same is long
    assert (same.key, same.params["error"].key) == ("check.probe_failed", "error.timeout")
    assert "…" not in same


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (OSError(errno.EHOSTUNREACH, "No route to host"), "No route to host"),
        (ConnectionAbortedError(10053, "Software caused connection abort"), "Software caused connection abort"),
        (RuntimeError("bug"), "bug"),
        (RuntimeError(), "RuntimeError"),
        ("unknown url type: ftp", "unknown url type: ftp"),
    ],
    ids=["oserror-strerror", "aborted-strerror", "exception-text", "exception-name", "plain-str"],
)
def test_short_error_keeps_the_systems_own_words_as_plain_text(exc, expected):
    word = short_error(exc)
    assert word == expected
    assert type(word) is str  # nothing to translate: no key


def test_short_error_still_clips_a_long_os_text():
    word = short_error(OSError(errno.EHOSTUNREACH, "x" * 200))
    assert type(word) is str
    assert len(word) == 70
    assert word.endswith("…")
