import errno
import http.client
import ipaddress
import socket
import ssl

import pytest

from wholagged.checks import (
    GC_VERSION_MAX_CHARS,
    MAX_HOSTNAME_CHARS,
    VALVE_TEXT_MAX_CHARS,
    Pop,
    _clip,
    _gc_version,
    _host,
    _ipv4,
    _valve_text,
    parse_sdr_pops,
    pick_cm_targets,
    short_error,
)
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


def _one_pop(pop: object) -> list[Pop]:
    return parse_sdr_pops({"pops": {"fra": pop}})


RELAY = [{"ipv4": "155.133.226.3"}]


@pytest.mark.parametrize("desc", [["Frankfurt"], "", None, 7, {"en": "Frankfurt"}], ids=repr)
def test_parse_sdr_pops_names_a_site_by_its_code_when_its_desc_is_not_text(desc):
    pops = _one_pop({"desc": desc, "relays": RELAY})
    assert pops == [Pop("fra", "fra", "155.133.226.3")]
    assert {pops[0]}  # hashable: check_relays keys a dict by Pop


def test_parse_sdr_pops_keeps_a_text_desc():
    assert _one_pop({"desc": "Frankfurt", "relays": RELAY}) == [Pop("fra", "Frankfurt", "155.133.226.3")]


@pytest.mark.parametrize(
    "relays",
    [5, {"ipv4": "155.133.226.3"}, "155.133.226.3", None, [], ["155.133.226.3"]],
    ids=["int", "dict", "str", "none", "empty", "list-of-str"],
)
def test_parse_sdr_pops_skips_a_site_without_a_relay_list(relays):
    assert _one_pop({"desc": "Frankfurt", "relays": relays}) == []


def test_parse_sdr_pops_skips_a_site_with_no_relays_key():
    assert _one_pop({"desc": "Frankfurt"}) == []


@pytest.mark.parametrize("ipv4", [["155.133.226.9"], 7, "", None, {"ip": "155.133.226.9"}, True], ids=repr)
def test_parse_sdr_pops_skips_a_relay_whose_ipv4_is_not_text_and_takes_the_next(ipv4):
    relays = [{"ipv4": ipv4}, "junk", {"port_range": [1, 2]}, {"ipv4": "155.133.226.3"}, {"ipv4": "155.133.226.4"}]
    assert _one_pop({"desc": "Frankfurt", "relays": relays}) == [Pop("fra", "Frankfurt", "155.133.226.3")]


def test_parse_sdr_pops_skips_a_site_whose_relays_all_lack_a_text_ipv4():
    assert _one_pop({"desc": "Frankfurt", "relays": [{"ipv4": ["155.133.226.9"]}, {"ipv4": 7}, {}]}) == []


def test_parse_sdr_pops_keeps_the_good_sites_among_bad_ones():
    cfg = {
        "pops": {
            "lst": {"desc": "List", "relays": [{"ipv4": ["155.133.226.9"]}]},
            "int": {"desc": "Int", "relays": 5},
            "str": "Stockholm",
            "vie": {"desc": "Vienna", "relays": [{"ipv4": "155.133.226.2"}]},
            "fra": {"desc": ["Frankfurt"], "relays": [{"ipv4": 7}, {"ipv4": "155.133.226.3"}]},
        }
    }
    assert parse_sdr_pops(cfg) == [Pop("vie", "Vienna", "155.133.226.2"), Pop("fra", "fra", "155.133.226.3")]


@pytest.mark.parametrize("pops", [[], ["fra"], "fra", 5, None], ids=repr)
def test_parse_sdr_pops_without_a_pops_mapping_is_empty(pops):
    assert parse_sdr_pops({"pops": pops}) == []


@pytest.mark.parametrize(
    ("result", "expected"),
    [
        ({"active_version": 7001, "deploy_version": 7000}, "7001"),
        ({"active_version": "7001"}, "7001"),
        ({"active_version": " 7001 "}, "7001"),  # surrounding spaces are not part of it
        ({"active_version": -1}, "-1"),
        ({"active_version": 0, "deploy_version": 7000}, "7000"),  # 0 means unknown: try deploy_version
        ({"deploy_version": 7000}, "7000"),
        ({"active_version": "", "deploy_version": "7000"}, "7000"),
        ({"active_version": "x" * GC_VERSION_MAX_CHARS}, "x" * GC_VERSION_MAX_CHARS),  # just fits
        ({"active_version": "7001\nVERDICT", "deploy_version": 7000}, "7000"),  # an injected line is no version
        ({"active_version": 10**25, "deploy_version": 7000}, "7000"),  # a 26-digit int is too long
    ],
    ids=[
        "int",
        "str",
        "spaces",
        "negative",
        "zero-then-deploy",
        "deploy-only",
        "empty-then-deploy",
        "max-length",
        "newline-then-deploy",
        "huge-int-then-deploy",
    ],
)
def test_gc_version_is_a_short_text_number(result, expected):
    assert _gc_version(result) == expected


@pytest.mark.parametrize(
    "value",
    [
        True,
        False,
        {"v": 7001},
        [7001],
        7001.0,
        None,
        "x" * (GC_VERSION_MAX_CHARS + 1),
        "\n",
        "   ",
        "7001\n7002",
        "70\x0001",
        chr(0x202E) + "1007",  # a right-to-left override: not printable
    ],
    ids=repr,
)
def test_gc_version_ignores_a_value_that_is_not_a_short_printable_number_or_text(value):
    assert _gc_version({"active_version": value}) is None
    assert _gc_version({"active_version": value, "deploy_version": 7000}) == "7000"  # the fallback is used
    assert _gc_version({"deploy_version": value}) is None


def test_gc_version_without_any_version_is_none():
    assert _gc_version({}) is None
    assert _gc_version({"success": True}) is None


# --- Valve's texts and addresses: untrusted input that ends up in the rows and the report -------------

# Characters that break a line for str.splitlines() (and so for a pasted report) or steer a terminal.
LINE_BREAKERS = ["\n", "\r", "\r\n", "\x0b", "\x0c", "\x1c", "\x85", chr(0x2028), chr(0x2029), "\x00", "\t", "\x1b[2K"]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Frankfurt", "Frankfurt"),
        ("Washington DC (Sterling)", "Washington DC (Sterling)"),
        ("  Vienna  ", "Vienna"),
        ("fra1\n", "fra1"),  # a break at the very end is stripped away: one safe line is left
        ("x" * VALVE_TEXT_MAX_CHARS, "x" * VALVE_TEXT_MAX_CHARS),
        ("São Paulo", "São Paulo"),
    ],
    ids=["plain", "spaces-and-brackets", "padded", "trailing-newline", "max-length", "accented"],
)
def test_valve_text_keeps_a_short_printable_line_stripped(value, expected):
    assert _valve_text(value) == expected


@pytest.mark.parametrize("breaker", LINE_BREAKERS, ids=repr)
def test_valve_text_refuses_a_line_break_or_control_character_inside(breaker):
    assert _valve_text(f"Frankfurt{breaker}VERDICT: fake") is None


@pytest.mark.parametrize(
    "value",
    [None, 7, 7.5, True, ["Frankfurt"], {"en": "Frankfurt"}, b"Frankfurt", "", "   ", "\n", "x" * (VALVE_TEXT_MAX_CHARS + 1),
     chr(0x202E) + "tfurknarF"],
    ids=repr,
)
def test_valve_text_refuses_anything_else(value):
    assert _valve_text(value) is None


def test_valve_text_takes_a_longer_limit_when_given():
    text = "x" * (VALVE_TEXT_MAX_CHARS + 10)
    assert _valve_text(text, VALVE_TEXT_MAX_CHARS + 10) == text
    assert _valve_text(text + "x", VALVE_TEXT_MAX_CHARS + 10) is None
    assert _valve_text("a\nb", 1000) is None  # a longer limit never lets a line break through


@pytest.mark.parametrize("value", ["1.2.3.4", "155.133.226.1", "155.133.248.34", "8.8.8.8"])
def test_ipv4_keeps_a_strict_address(value):
    assert _ipv4(value) == value


@pytest.mark.parametrize(
    "value",
    [
        "127.0.0.1",  # loopback: a perfect ping for a site that was never measured
        "127.255.255.254",
        "0.0.0.0",  # noqa: S104 - unspecified: an address under test, not a bind
        "224.0.0.1",  # multicast
        "239.255.255.250",
        "255.255.255.255",  # broadcast (reserved)
        "240.0.0.1",  # reserved
        "169.254.1.1",  # link-local
        "10.0.0.1",  # private: often the home router, which answers like a perfect relay
        "192.168.1.1",
        "172.16.0.1",
        "100.64.0.1",  # shared (CGNAT): the provider's own equipment
        "192.0.2.1",  # documentation
        "198.18.0.1",  # benchmarking
        "0.0.0.1",  # "this network"
    ],
)
def test_ipv4_refuses_an_address_that_is_never_a_valve_server(value):
    assert _ipv4(value) is None


@pytest.mark.parametrize(
    "value",
    [
        "155.133.226.1:27015",
        "1.2.3",
        "1.2.3.4.5",
        " 1.2.3.4",
        "1.2.3.4 ",
        "1.2.3.4\n",
        "155.133.226.01",  # leading zeros: octal on some systems
        "0155.133.226.1",
        "1.2.3.256",
        "a.b.c.d",
        "::1",
        "2001:db8::1",
        "155.133.226.0/8",
        "",
        int(ipaddress.IPv4Address("155.133.226.1")),  # IPv4Address would take an int, but Valve sends text
        None,
        ["1.2.3.4"],
        b"1.2.3.4",
    ],
    ids=repr,
)
def test_ipv4_refuses_anything_but_a_strict_dotted_address(value):
    assert _ipv4(value) is None


@pytest.mark.parametrize(
    ("desc", "shown"),
    [
        ("Frankfurt\nVERDICT: fake", "fra"),
        ("Frankfurt" + chr(0x2028) + "VERDICT: fake", "fra"),
        ("x" * (VALVE_TEXT_MAX_CHARS + 1), "fra"),
        ("   ", "fra"),
        ("  Frankfurt  ", "Frankfurt"),
    ],
    ids=["newline", "line-separator", "too-long", "blank", "padded"],
)
def test_parse_sdr_pops_shows_only_a_safe_desc_else_the_code(desc, shown):
    assert _one_pop({"desc": desc, "relays": RELAY}) == [Pop("fra", shown, "155.133.226.3")]


@pytest.mark.parametrize(
    "code", ["", "   ", "fra\nVERDICT: fake", "fra\x00", "x" * (VALVE_TEXT_MAX_CHARS + 1)], ids=repr
)
def test_parse_sdr_pops_skips_a_site_whose_code_is_not_safe_text(code):
    cfg = {"pops": {code: {"desc": "Frankfurt", "relays": RELAY}, "vie": {"desc": "Vienna", "relays": RELAY}}}
    assert parse_sdr_pops(cfg) == [Pop("vie", "Vienna", "155.133.226.3")]


def test_parse_sdr_pops_strips_the_code():
    assert parse_sdr_pops({"pops": {" fra ": {"relays": RELAY}}}) == [Pop("fra", "fra", "155.133.226.3")]


@pytest.mark.parametrize(
    "ipv4", ["155.133.226.1:27015", "1.2.3", " 155.133.226.1", "155.133.226.01", "::1", "10.0.0.1"], ids=repr
)
def test_parse_sdr_pops_skips_a_malformed_address_and_takes_the_next_valid_one(ipv4):
    relays = [{"ipv4": ipv4}, {"ipv4": "155.133.226.3"}, {"ipv4": "155.133.226.4"}]
    assert _one_pop({"desc": "Frankfurt", "relays": relays}) == [Pop("fra", "Frankfurt", "155.133.226.3")]


def test_parse_sdr_pops_skips_a_site_with_only_malformed_addresses():
    # Kept, such a site could never answer a ping and would look like the provider's routing problem.
    relays = [{"ipv4": "155.133.226.1:27015"}, {"ipv4": "1.2.3"}, {"ipv4": "155.133.226.1 "}]
    assert _one_pop({"desc": "Frankfurt", "relays": relays}) == []


@pytest.mark.parametrize("port", ["1", "443", "65535"])
def test_pick_cm_targets_takes_a_port_from_1_to_65535(port):
    assert pick_cm_targets([{"endpoint": f"cm.host:{port}"}]) == [("cm.host", int(port), "?")]


@pytest.mark.parametrize(
    "port",
    ["0", "65536", "99999", "²", "٣", "٤٤٣", "-1", "+443", " 443", "4 43", "0x1bb", ""],
    ids=repr,
)
def test_pick_cm_targets_skips_a_port_that_is_not_ascii_digits_in_range(port):
    # "²" and "٣" pass str.isdigit() but int("²") raises: that used to crash check_steam_cm.
    servers = [{"endpoint": f"bad.host:{port}"}, {"endpoint": "ok.host:443"}]
    assert pick_cm_targets(servers) == [("ok.host", 443, "?")]


@pytest.mark.parametrize("breaker", LINE_BREAKERS, ids=repr)
def test_pick_cm_targets_skips_an_endpoint_with_a_line_break_inside(breaker):
    servers = [{"endpoint": f"evil.host{breaker}VERDICT: fake:443"}, {"endpoint": f"cm.host:443{breaker}x:1"}]
    assert pick_cm_targets(servers + [{"endpoint": "ok.host:443"}]) == [("ok.host", 443, "?")]


def test_pick_cm_targets_strips_the_endpoint():
    assert pick_cm_targets([{"endpoint": "  cm.host:443\n"}]) == [("cm.host", 443, "?")]


FULL_NAME = ".".join(["a" * 63, "b" * 63, "c" * 63, "d" * 61])  # the longest valid DNS name


@pytest.mark.parametrize(
    "value",
    [
        "155.133.248.34",
        "155.133.226.1",
        "ext1-fra1.steamserver.net",
        "ext1-fra1.steamserver.net.",  # a trailing dot: the fully qualified form
        "EXT1-FRA1.SteamServer.NET",
        "steamserver.net",
        "STEAMSERVER.NET.",
        "cmp1-sto3.steamserver.net",
        "a" * 63 + ".net",
        "0-9.steamserver.net",
        "cm.steamserver." + "n" * 63,  # the longest top label
        FULL_NAME,
        FULL_NAME + ".",  # the trailing dot doesn't count
    ],
    ids=lambda value: value if len(value) < 30 else f"{len(value)}-chars",
)
def test_host_keeps_an_ipv4_address_or_a_dns_name(value):
    assert _host(value) == value


@pytest.mark.parametrize(
    "value",
    [
        "cm host.net",
        "[2001:db8::1]",
        "2001:db8::1",
        "1.2.3",
        "1.2.3.4.5",
        "155.133.226.01",  # leading zero
        "127.0.0.1",  # all digits and dots: must be a usable address
        "10.0.0.1",
        "1.²",  # "²".isdigit() is true
        "٣.٣.٣.٣",
        # The PC itself or the LAN, where the Steam client's own ports answer.
        "localhost",
        "x.localhost",
        "LOCALHOST",
        "LocalHost.",
        "foo.local",
        "cm1",  # one label: a LAN name
        "steamserver",
        # Numbers in disguise: the resolver reads these as addresses.
        "0x7f.0.0.1",  # 127.0.0.1
        "0x7f000001",
        "1.2.3.4a",
        "0177.0.0.1",
        # The last label must be letters only, 2 to 63 of them.
        "a.b1",
        "a.b",
        "cm.steamserver.n3t",
        "cm.steamserver." + "n" * 64,
        "cm.steamserver.-net",
        # Broken labels, each under a valid top label so nothing else refuses them.
        "a..net",
        ".a.net",
        "a.net..",
        ".",
        "",
        "-a.net",
        "a-.net",
        "a.-b.net",
        "ä.net",
        "a_b.net",
        "a/b.net",
        "a:443.net",
        "a" * 64 + ".net",  # a 64-character label
        FULL_NAME + "d",  # 254 characters
        FULL_NAME + "d.",
    ],
    ids=lambda value: repr(value) if len(value) < 30 else f"{len(value)}-chars",
)
def test_host_refuses_anything_else(value):
    assert _host(value) is None


def test_pick_cm_targets_takes_an_endpoint_up_to_a_full_hostname_and_port():
    assert len(FULL_NAME) == MAX_HOSTNAME_CHARS
    assert pick_cm_targets([{"endpoint": f"{FULL_NAME}:65535"}]) == [(FULL_NAME, 65535, "?")]
    assert pick_cm_targets([{"endpoint": f"{FULL_NAME}d:65535"}]) == []  # one more character is too long


@pytest.mark.parametrize(
    "endpoint",
    [
        "cm host:443",
        "[2001:db8::1]:27017",
        "1.2.3:443",
        "a..net:443",
        "-a.net:443",
        "a-.net:443",
        "ä.net:443",
        "a_b.net:443",
        "127.0.0.1:27017",
        ".:443",
        "localhost:27017",
        "0x7f.0.0.1:27017",
        "cm1:27017",
        "cm.b1:27017",
    ],
    ids=repr,
)
def test_pick_cm_targets_skips_an_unusable_host(endpoint):
    assert pick_cm_targets([{"endpoint": endpoint}, {"endpoint": "ok.host:443"}]) == [("ok.host", 443, "?")]


def test_pick_cm_targets_without_a_usable_host_gives_no_targets():
    servers = [{"endpoint": e, "type": "websockets"} for e in ["cm host:443", "[2001:db8::1]:27017", "a_b.c:443"]]
    assert pick_cm_targets(servers) == []


@pytest.mark.parametrize(
    ("dc", "shown"),
    [
        ("fra1", "fra1"),
        ("  fra1  ", "fra1"),
        ("fra1\nVERDICT: fake", "?"),
        ("fra1\x85x", "?"),
        ("x" * (VALVE_TEXT_MAX_CHARS + 1), "?"),
        ("", "?"),
        (["fra1"], "?"),
        (None, "?"),
    ],
    ids=["plain", "padded", "newline", "next-line", "too-long", "empty", "list", "none"],
)
def test_pick_cm_targets_shows_only_a_safe_dc_else_a_question_mark(dc, shown):
    assert pick_cm_targets([{"endpoint": "cm.host:443", "dc": dc}]) == [("cm.host", 443, shown)]


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


def _one_printable_line(text: str) -> bool:
    return text.isprintable() and len(text.splitlines()) == 1


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("No route to host", "No route to host"),
        ("a\nb", "a b"),
        ("a\r\n\r\nb", "a b"),  # a run of breaks is one space
        ("  a \t  b  ", "a b"),
        ("X\x1b[2Jy", "X [2Jy"),  # a terminal escape loses its ESC, so it can't run
        ("a" + chr(0x2028) + "b" + chr(0x85) + "c", "a b c"),
        ("a\x00b", "a b"),
        ("São Paulo", "São Paulo"),
        ("\r\n\x00", ""),
        ("", ""),
    ],
    ids=repr,
)
def test_clip_makes_one_printable_line(text, expected):
    assert _clip(text) == expected


@pytest.mark.parametrize("breaker", LINE_BREAKERS, ids=repr)
def test_clip_leaves_no_line_break_or_control_character(breaker):
    clipped = _clip(f"Bad Gateway{breaker}[OK] Valve: fine{breaker}")
    assert _one_printable_line(clipped)
    assert "\x1b" not in clipped
    # The words stay, on the same line: the ESC of "\x1b[2K" becomes a space and its printable rest stays.
    rest = breaker.removeprefix("\x1b")
    assert clipped == (f"Bad Gateway {rest}[OK] Valve: fine {rest}" if rest.isprintable() and rest else
                       "Bad Gateway [OK] Valve: fine")


def test_clip_clips_after_cleaning():
    clipped = _clip("x\n" * 200)  # 400 characters, 200 words once cleaned
    assert _one_printable_line(clipped)
    assert len(clipped) == 70
    assert clipped.endswith("…")
    assert _clip("y" * 70) == "y" * 70  # exactly the limit is kept whole


def test_short_error_of_a_bad_status_line_is_one_printable_line():
    # A proxy or a captive portal can send any status line; http.client puts it into the exception's text.
    word = short_error(http.client.BadStatusLine("X\r\n[OK] y\x1b[2J"))
    assert _one_printable_line(word)
    assert word == "X [OK] y [2J"


@pytest.mark.parametrize("strerror", ["No route\r\nto host", "No route\nto host", "No route\rto host"], ids=repr)
def test_short_error_of_an_os_text_with_line_breaks_is_one_line(strerror):
    word = short_error(OSError(errno.EHOSTUNREACH, strerror))
    assert word == "No route to host"
    assert type(word) is str


@pytest.mark.parametrize(
    "exc",
    [RuntimeError("\x00\x1b\r\n"), ValueError("\n"), OSError(errno.EIO, "\r\n"), http.client.BadStatusLine("\x07\x08")],
    ids=lambda exc: type(exc).__name__,
)
def test_short_error_with_nothing_printable_left_names_the_error_type(exc):
    assert short_error(exc) == type(exc).__name__


def test_short_error_of_plain_text_is_one_line():
    word = short_error("a\nb")
    assert word == "a b"
    assert type(word) is str
