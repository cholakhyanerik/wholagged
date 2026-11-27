"""End-to-end scenarios: break one part of the fake network, expect one verdict."""

from __future__ import annotations

import pytest

import wholagged
from wholagged import checks
from wholagged.checks import run_checks
from wholagged.i18n import Msg
from wholagged.models import Side, Status
from wholagged.report import build_report
from wholagged.verdict import decide

from fakes import CM_LIST, SDR, FakeNet


@pytest.fixture
def net(monkeypatch):
    return FakeNet().install(monkeypatch)


def run(net):
    results = run_checks()
    return results, decide(results)


def test_everything_ok_points_to_the_pc(net):
    results, verdict = run(net)
    assert {r.status for r in results.values()} == {Status.OK}
    assert verdict.side == Side.PC
    assert "Vienna" in results["relays"].summary  # the fastest relay wins
    assert "version 7001" in results["dota_gc"].summary


def test_no_internet(net):
    net.internet = False
    results, verdict = run(net)
    assert results["internet"].status == Status.FAIL
    assert all(results[k].status == Status.SKIP for k in ("dns", "steam_api", "relays"))
    assert verdict.side == Side.YOU
    assert "internet" in verdict.headline


def test_dns_broken(net):
    net.dns = False
    _, verdict = run(net)
    assert verdict.side == Side.YOU
    assert "DNS" in verdict.headline


def test_one_steam_name_not_resolving_is_blamed_on_dns(net):
    net.unresolved = {"steamcommunity.com"}
    results, verdict = run(net)
    assert results["dns"].status == Status.WARN  # the other names still resolve
    assert results["dns"].data["steam_dns_fail"] is True
    assert "steamcommunity.com" in results["dns"].summary
    assert results["steam_api"].status == Status.OK
    assert verdict.side == Side.YOU
    assert "DNS" in verdict.headline


def test_non_steam_name_not_resolving_is_not_blamed_on_dns(net):
    net.unresolved = {"google.com"}
    results, verdict = run(net)
    assert results["dns"].status == Status.WARN
    assert results["dns"].data["steam_dns_fail"] is False
    assert "google.com" in results["dns"].summary
    assert verdict.side == Side.PC  # Steam's names resolve: nothing for Dota to trip over
    assert "DNS" not in verdict.headline


def test_valve_returns_503(net):
    net.http[checks.CM_LIST_URL] = 503
    results, verdict = run(net)
    assert results["steam_api"].status == Status.WARN
    assert verdict.side == Side.VALVE


def test_gc_down(net):
    net.http[checks.GC_VERSION_URL] = {"result": {"success": False}}
    results, verdict = run(net)
    assert results["dota_gc"].status == Status.FAIL
    assert verdict.side == Side.VALVE


def test_gc_endpoint_gone_is_not_blamed_on_valve(net):
    net.http[checks.GC_VERSION_URL] = 404
    results, verdict = run(net)
    assert results["dota_gc"].status == Status.SKIP
    assert verdict.side == Side.PC
    assert "steamstat.us" in verdict.advice[0]


def test_valve_unreachable_but_internet_ok(net):
    net.tcp_ok = False
    results, verdict = run(net)
    assert results["internet"].status == Status.OK
    assert results["steam_api"].status == Status.FAIL
    assert results["steam_cm"].status == Status.FAIL
    assert results["steam_cm"].data["fallback"] is True
    assert verdict.side == Side.UNCLEAR


def test_certificate_failure_is_blamed_on_the_pc_not_the_provider(net):
    net.cert_ok = False
    results, verdict = run(net)
    assert results["steam_api"].status == Status.FAIL
    assert results["steam_api"].data["cert_error"] is True
    assert any("certificate has expired" in d for d in results["steam_api"].details)
    assert results["steam_cm"].status == Status.OK  # plain TCP to Steam still works
    assert verdict.side == Side.YOU
    assert "HTTPS" in verdict.headline


def test_relays_silent_while_internet_pings(net):
    net.relays_ok = False
    results, verdict = run(net)
    assert results["relays"].data.get("routing") is True
    assert verdict.side == Side.ISP


def test_icmp_blocked_everywhere_is_not_a_verdict(net):
    net.relays_ok = False
    net.control_ok = False
    results, verdict = run(net)
    assert results["relays"].status == Status.SKIP
    assert verdict.side == Side.PC


def test_packet_loss(net):
    net.loss_every = 4  # every 4th ping to each relay: 20% of the quality pings
    results, verdict = run(net)
    assert results["relays"].status == Status.WARN
    assert results["relays"].data["lossy"] is True
    assert verdict.side == Side.YOU
    assert "packet loss" in verdict.headline


def test_high_ping(net):
    net.relay_extra_ms = 140.0
    results, verdict = run(net)
    assert results["relays"].data.get("high_ping") is True
    assert verdict.side == Side.YOU


def test_jittery_relays_point_to_your_connection(net):
    net.relay_jitter_ms = 40.0  # 47, 87, 47, 87 ... ms to Vienna: no loss, the best average stays low
    results, verdict = run(net)
    relays = results["relays"]
    assert relays.status == Status.WARN
    assert relays.data["jittery"] is True
    assert relays.data["jitter"] == 40.0
    # The rules before it don't fire: no loss and a low ping, so this is the jitter branch and no other.
    assert relays.data["loss"] == 0.0
    assert relays.data["best_ms"] == 67.0 <= checks.HIGH_PING_MS
    assert "lossy" not in relays.data and "high_ping" not in relays.data
    assert {r.status for k, r in results.items() if k != "relays"} == {Status.OK}
    assert verdict.side == Side.YOU
    assert "40 ms" in verdict.explanation  # the measured jitter, not the loss or the ping


@pytest.mark.parametrize(
    ("extra", "jittery"),
    [(checks.JITTER_WARN_MS, False), (checks.JITTER_WARN_MS + 1, True)],
    ids=["at-the-limit", "just-over"],
)
def test_jitter_warns_only_above_the_limit(net, extra, jittery):
    net.relay_jitter_ms = extra
    results, verdict = run(net)
    relays = results["relays"]
    assert relays.data["jitter"] == extra
    assert relays.data.get("jittery", False) is jittery
    assert relays.status == (Status.WARN if jittery else Status.OK)
    assert verdict.side == (Side.YOU if jittery else Side.PC)


def test_packet_loss_is_named_before_jitter(net):
    net.relay_jitter_ms = 40.0
    net.loss_every = 4
    results, verdict = run(net)
    assert results["relays"].data["lossy"] is True
    assert "jittery" not in results["relays"].data
    assert verdict.side == Side.YOU
    assert "packet loss" in verdict.headline


def test_high_ping_is_named_before_jitter(net):
    net.relay_jitter_ms = 40.0
    net.relay_extra_ms = 140.0  # 187, 227, 187 ... ms to Vienna: 207 ms on average
    results, verdict = run(net)
    assert results["relays"].data["high_ping"] is True
    assert results["relays"].data["best_ms"] == 207.0
    assert "jittery" not in results["relays"].data
    assert verdict.side == Side.YOU
    assert "207 ms" in verdict.explanation  # the ping is named, not the jitter
    assert "jitter" not in verdict.explanation.lower()


def test_jitter_does_not_touch_the_control_pings(net):
    net.relay_jitter_ms = 40.0
    for _ in range(4):
        assert [checks.icmp.ping(ip) for ip in checks.CONTROL_PING_IPS] == [9.0, 11.0]
    assert [checks.icmp.ping("155.133.226.2") for _ in range(4)] == [47.0, 87.0, 47.0, 87.0]


CM_HOSTS = [host for host, _, _ in checks.pick_cm_targets(CM_LIST["response"]["serverlist"])]


def test_most_steam_login_servers_refusing_points_to_the_provider(net):
    net.refused_hosts = set(CM_HOSTS[:-1])  # 1 of 4 still answers: less than half
    results, verdict = run(net)
    cm = results["steam_cm"]
    assert cm.status == Status.WARN
    assert cm.data == {"fallback": False, "ok": 1, "total": 4}
    assert [d.params["error"].key for d in cm.details if isinstance(d, Msg)] == ["error.refused"] * 3
    assert results["steam_api"].status == Status.OK  # not "nothing at Valve answers" (rule 5)
    assert verdict.side == Side.ISP


def test_half_the_steam_login_servers_answering_is_still_ok(net):
    net.refused_hosts = set(CM_HOSTS[:2])
    results, verdict = run(net)
    assert results["steam_cm"].status == Status.OK
    assert results["steam_cm"].data == {"fallback": False, "ok": 2, "total": 4}
    assert verdict.side == Side.PC


def test_all_steam_login_servers_refusing_while_the_api_answers_points_to_the_provider(net):
    net.refused_hosts = set(CM_HOSTS)
    results, verdict = run(net)
    assert results["steam_cm"].status == Status.FAIL
    assert results["steam_cm"].data == {"fallback": False, "ok": 0, "total": 4}
    assert results["steam_api"].status == Status.OK
    assert verdict.side == Side.ISP


def test_steam_api_refused_while_steams_web_servers_answer_points_to_the_provider(net):
    net.refused_hosts = {"api.steampowered.com"}
    results, verdict = run(net)
    assert results["steam_api"].status == Status.FAIL
    assert results["steam_api"].summary.params["error"].key == "error.refused"
    cm = results["steam_cm"]
    assert cm.status == Status.OK  # the store and the community answer: 2 of 3
    assert cm.data == {"fallback": True, "ok": 2, "total": 3}
    assert cm.summary.key == "check.steam_cm.web_ok"
    assert results["dota_gc"].status == Status.SKIP  # the same refused host
    assert results["relays"].status == Status.SKIP
    assert verdict.side == Side.ISP


def test_report_contains_everything(net):
    results, verdict = run(net)
    text = build_report(results, verdict)
    for spec in checks.CHECKS:
        assert spec.title in text
    assert verdict.headline in text


OLD_NAME = "Dota 2 Network Check"  # the pre-WL-10 product name


def test_report_starts_with_the_product_name_and_version(net):
    results, verdict = run(net)
    text = build_report(results, verdict)
    assert text.splitlines()[0] == f"wholagged {wholagged.__version__} · Dota 2"
    assert OLD_NAME not in text


def test_cli_banner_names_wholagged_and_dota_2(net, capsys):
    assert wholagged.run_cli() == 0
    out = capsys.readouterr().out
    first = out.splitlines()[0]
    assert first.startswith(f"wholagged {wholagged.__version__}")
    assert "Dota 2" in first
    assert OLD_NAME not in out


def test_garbage_cm_list_is_not_a_crash(net):
    net.http[checks.CM_LIST_URL] = {"response": {"serverlist": ["x", 5, {"endpoint": 7, "dc": ["fra"]}]}}
    results, _ = run(net)
    assert results["steam_api"].status == Status.OK  # one dict entry survives the type checks
    assert results["steam_cm"].data["fallback"] is True  # but it has no usable endpoint


GARBAGE_SDR = {
    "pops": {
        "lst": {"desc": ["List"], "relays": [{"ipv4": ["155.133.226.9"]}]},  # was a Pop of lists: unhashable
        "int": {"desc": "Int", "relays": 5},  # was a TypeError: an int is not iterable
        "dct": {"desc": "Dict", "relays": {"ipv4": "155.133.226.2"}},
        "str": "Stockholm",
        "fra": {"desc": ["Frankfurt"], "relays": [{"ipv4": 7}, {"ipv4": ""}, {"ipv4": "155.133.226.3"}]},
    }
}


def test_garbage_relay_list_is_not_a_crash(net):
    net.http[checks.SDR_CONFIG_URL] = GARBAGE_SDR
    results, verdict = run(net)
    relays = results["relays"]
    assert relays.summary.key != "check.internal_error"  # what the old parser crashed into
    assert relays.status == Status.OK
    assert relays.summary.key == "check.relays.ok"
    assert relays.summary.params["pop"] == "fra"  # the one usable site, named by its code
    assert relays.data["best_ms"] == 52.0
    assert verdict.side == Side.PC


@pytest.mark.parametrize(
    ("answer", "shown"),
    [
        ({"success": True, "active_version": True, "deploy_version": 7001}, "7001"),  # was "version True"
        ({"success": True, "active_version": {"v": 1}, "deploy_version": "7002"}, "7002"),
        ({"success": True, "active_version": {"v": 1}}, None),  # was "version {'v': 1}"
        ({"success": True, "active_version": "x" * 500}, None),
        ({"success": True, "active_version": "7001\nForged line"}, None),
        ({"success": True, "active_version": 0}, None),
    ],
    ids=["bool-then-deploy", "dict-then-deploy-str", "dict", "too-long", "two-lines", "zero"],
)
def test_gc_version_is_shown_only_when_it_looks_like_one(net, answer, shown):
    net.http[checks.GC_VERSION_URL] = {"result": answer}
    results, verdict = run(net)
    gc = results["dota_gc"]
    assert gc.status == Status.OK  # a strange version never changes the verdict
    if shown is None:
        assert gc.summary.key == "check.dota_gc.ok"
        assert "version" not in gc.summary
    else:
        assert gc.summary.key == "check.dota_gc.ok_version"
        assert gc.summary.params["version"] == shown
    assert verdict.side == Side.PC


def test_relay_list_with_only_malformed_addresses_is_not_blamed_on_the_provider(net):
    # Unpingable addresses used to be pinged anyway: no relay answered while 1.1.1.1 did, so "routing" -> ISP.
    bad = ["155.133.226.1:27015", "155.133.226.2 ", "1.2.3", "010.0.0.3", "::1"]
    net.http[checks.SDR_CONFIG_URL] = {
        "pops": {f"p{i}": {"desc": f"Site {i}", "relays": [{"ipv4": ip}]} for i, ip in enumerate(bad)}
    }
    results, verdict = run(net)
    relays = results["relays"]
    assert relays.status == Status.SKIP
    assert relays.summary.key == "check.relays.empty"
    assert "routing" not in relays.data
    assert verdict.side != Side.ISP
    assert verdict.side == Side.PC  # the rest of the network is fine


def test_cm_port_in_unicode_digits_is_not_a_crash(net):
    # "²".isdigit() is true but int("²") raises: check_steam_cm used to fall into "internal error".
    net.http[checks.CM_LIST_URL] = {
        "response": {
            "serverlist": [
                {"endpoint": "ext1-fra1.steamserver.net:²", "type": "websockets", "dc": "fra1"},
                {"endpoint": "ext2-fra1.steamserver.net:٢٧٠١٩", "type": "websockets", "dc": "fra1"},
                {"endpoint": "ext1-sto1.steamserver.net:0", "type": "websockets", "dc": "sto1"},
                {"endpoint": "ext1-vie1.steamserver.net:443", "type": "websockets", "dc": "vie1"},
            ]
        }
    }
    results, verdict = run(net)
    cm = results["steam_cm"]
    assert cm.summary.key != "check.internal_error"
    assert cm.status == Status.OK
    assert cm.data == {"fallback": False, "ok": 1, "total": 1}  # only the endpoint with a real port
    assert verdict.side == Side.PC


UNUSABLE_CM_HOSTS = ["cm host", "[2001:db8::1]", "1.2.3", "a_b.steamserver.net", "-ext1.steamserver.net", "127.0.0.1"]


def test_cm_list_without_a_usable_host_falls_back_and_is_not_blamed_on_the_provider(net):
    net.http[checks.CM_LIST_URL] = {
        "response": {
            "serverlist": [{"endpoint": f"{h}:27017", "type": "websockets", "dc": "fra1"} for h in UNUSABLE_CM_HOSTS]
        }
    }
    # What the real network does with them: the names don't resolve and nothing listens on the PC itself.
    # Probed anyway, they all failed while the Steam API answered: "part of Valve is blocked" -> ISP.
    net.unresolved = set(UNUSABLE_CM_HOSTS[:-1])
    net.refused_hosts = {"127.0.0.1"}
    results, verdict = run(net)
    assert results["steam_api"].status == Status.OK
    cm = results["steam_cm"]
    assert cm.data == {"fallback": True, "ok": 3, "total": 3}
    assert cm.details[0].key == "check.steam_cm.fallback"
    assert cm.summary.key == "check.steam_cm.web_ok"
    assert cm.status == Status.OK
    assert verdict.side != Side.ISP
    assert verdict.side == Side.PC


def test_relays_at_loopback_are_not_measured(net):
    # 127.0.0.1 answers in <1 ms from the PC itself: kept, it would show a perfect ping that was never measured.
    net.http[checks.SDR_CONFIG_URL] = {
        "pops": {code: {"desc": code.upper(), "relays": [{"ipv4": "127.0.0.1"}]} for code in ("sto", "vie", "fra")}
    }
    assert checks.icmp.ping("127.0.0.1") is not None  # the fake network answers loopback like a real PC
    results, verdict = run(net)
    relays = results["relays"]
    assert relays.status == Status.SKIP
    assert relays.status != Status.OK
    assert relays.summary.key == "check.relays.empty"
    assert verdict.side == Side.PC


def test_loopback_relays_are_dropped_and_the_real_ones_measured(net):
    net.http[checks.SDR_CONFIG_URL] = {
        "pops": {
            "lo": {"desc": "Loopback", "relays": [{"ipv4": "127.0.0.1"}]},
            "lo2": {"desc": "Also loopback", "relays": [{"ipv4": "127.0.0.2"}, {"ipv4": "155.133.226.2"}]},
            "fra": {"desc": "Frankfurt", "relays": [{"ipv4": "155.133.226.3"}]},
        }
    }
    results, _ = run(net)
    relays = results["relays"]
    assert relays.status == Status.OK
    assert relays.summary.params["pop"] == "Also loopback"  # measured at its next relay, 155.133.226.2 (47 ms)
    assert relays.data["best_ms"] == 47.0
    assert relays.details[2].params == {"ok": 2, "total": 2}  # "lo" is gone


def _sdr_with(count: int) -> dict[str, object]:
    """fakes.SDR's five answering sites, then silent ones up to `count` sites, all at public addresses."""
    assert count <= 5_000, "a fake relay list this long would eat memory, not test anything"
    pops = {code: pop for code, pop in SDR["pops"].items() if "relays" in pop}
    for n in range(count - len(pops)):
        pops[f"x{n}"] = {"desc": f"Extra {n}", "relays": [{"ipv4": f"155.133.{227 + n // 250}.{1 + n % 250}"}]}
    return {"pops": pops}


def test_too_many_relay_sites_are_not_pinged(net):
    net.http[checks.SDR_CONFIG_URL] = _sdr_with(checks.MAX_POPS + 1)
    assert len(checks.parse_sdr_pops(net.http[checks.SDR_CONFIG_URL])) == checks.MAX_POPS + 1  # all valid
    results, verdict = run(net)
    relays = results["relays"]
    assert relays.status == Status.SKIP
    assert relays.summary.key == "check.relays.list_failed"
    error = relays.summary.params["error"]
    assert type(error) is Msg
    assert (error.key, error.params) == ("error.too_big", {})
    assert net.pinged == []  # not one ping, not even the control ones
    assert verdict.side not in (Side.ISP, Side.YOU)
    assert verdict.side == Side.PC


def test_relay_sites_up_to_the_limit_are_measured(net):
    sdr = net.http[checks.SDR_CONFIG_URL] = _sdr_with(checks.MAX_POPS)
    results, verdict = run(net)
    relays = results["relays"]
    assert relays.status == Status.OK
    assert relays.summary.params["pop"] == "Vienna"
    responded = next(d for d in relays.details if isinstance(d, Msg) and d.key == "check.relays.responded")
    assert responded.params == {"ok": 5, "total": checks.MAX_POPS}  # the extra sites don't answer
    addresses = {relay["ipv4"] for pop in sdr["pops"].values() for relay in pop["relays"]}
    assert len(addresses) == checks.MAX_POPS
    assert addresses <= set(net.pinged)  # every site was pinged
    assert verdict.side == Side.PC


GARBAGE_SDR_ONLY = {"pops": {"a": {"relays": 5}, "b": {"relays": [{"ipv4": "155.133.226.1:1"}]}, "c\nX": "y"}}
# Ways the relays check is skipped although ICMP works: the advice must not say "ICMP is blocked".
RELAYS_UNCHECKED = {
    "sdr-503": 503,
    "empty-list": {"pops": {}},
    "garbage-list": GARBAGE_SDR_ONLY,
    "too-many-sites": _sdr_with(checks.MAX_POPS + 1),
    "relays-check-crashes": RuntimeError("bug"),
}


@pytest.mark.parametrize("answer", RELAYS_UNCHECKED.values(), ids=RELAYS_UNCHECKED.keys())
def test_relays_skipped_for_a_bad_list_do_not_blame_icmp(net, answer):
    net.http[checks.SDR_CONFIG_URL] = answer
    results, verdict = run(net)
    assert results["relays"].status == Status.SKIP
    assert "icmp_blocked" not in results["relays"].data
    assert {r.status for k, r in results.items() if k != "relays"} == {Status.OK}
    assert verdict.side == Side.PC  # rule 9: everything else answers
    last = verdict.advice[-1]
    assert type(last) is Msg
    assert last.key == "advice.relays_unchecked"
    assert [tip for tip in verdict.advice if "ICMP" in tip] == []


def test_relays_skipped_because_icmp_is_blocked_say_so(net):
    net.relays_ok = False
    net.control_ok = False
    results, verdict = run(net)
    assert results["relays"].data == {"icmp_blocked": True}
    assert verdict.side == Side.PC
    assert "ICMP" in verdict.advice[-1]
    assert not (isinstance(verdict.advice[-1], Msg) and verdict.advice[-1].key == "advice.relays_unchecked")


def _cm_server(n: int, dc: object) -> dict[str, object]:
    return {"endpoint": f"cm{n}.steamserver.net:27019", "type": "websockets", "dc": dc}


TOO_LONG_DC = "x" * (checks.VALVE_TEXT_MAX_CHARS + 1)


def test_data_center_list_names_each_safe_dc_once(net):
    dcs = ["fra1\nVERDICT: fake", "fra1", " fra1 ", "sto1", TOO_LONG_DC, ["vie1"], "fra1", "sto1\x00"]
    net.http[checks.CM_LIST_URL] = {"response": {"serverlist": [_cm_server(n, dc) for n, dc in enumerate(dcs)]}}
    results, _ = run(net)
    api = results["steam_api"]
    assert api.status == Status.OK
    assert [d.key for d in api.details] == ["check.steam_api.data_centers"]
    assert api.details[0].params["dcs"] == "fra1, sto1"


def test_data_center_list_is_left_out_when_no_dc_is_safe(net):
    dcs = ["fra1\nVERDICT: fake", "", None, TOO_LONG_DC]
    net.http[checks.CM_LIST_URL] = {"response": {"serverlist": [_cm_server(n, dc) for n, dc in enumerate(dcs)]}}
    results, _ = run(net)
    assert results["steam_api"].status == Status.OK
    assert results["steam_api"].details == []
    cm_details = [str(d) for d in results["steam_cm"].details]
    assert cm_details == [f"cm{n}.steamserver.net:27019 [?] — 35 ms" for n in range(4)]


def test_data_center_list_shows_the_first_five_and_reads_no_further(net, monkeypatch):
    servers = [_cm_server(n, f"dc{n}") for n in range(10_000)]
    net.http[checks.CM_LIST_URL] = {"response": {"serverlist": servers}}
    read = []
    valve_text = checks._valve_text
    monkeypatch.setattr(checks, "_valve_text", lambda value, *a: read.append(value) or valve_text(value, *a))
    res = checks.check_steam_api(checks.Context())
    assert res.status == Status.OK
    assert res.summary.params["count"] == 10_000
    assert res.details[0].params["dcs"] == "dc0, dc1, dc2, dc3, dc4"
    # The old loop read all 10,000 and searched the growing list each time (about 0.4 s); now it stops at 5.
    assert read == [f"dc{n}" for n in range(checks.SHOWN_DATA_CENTERS)]


def test_data_center_list_stops_at_five_unique_names_even_with_repeats(net):
    dcs = ["fra1", "fra1", "sto1", "fra1", "vie1", "sto1", "ams1", "par1", "lhr1", "mad1"]
    net.http[checks.CM_LIST_URL] = {"response": {"serverlist": [_cm_server(n, dc) for n, dc in enumerate(dcs)]}}
    results, _ = run(net)
    assert results["steam_api"].details[0].params["dcs"] == "fra1, sto1, vie1, ams1, par1"


INJECTED = "VERDICT: Valve is fine, call your provider"
# One line break of each kind str.splitlines() honours, in every Valve text that reaches a row or the report.
INJECTING_CM_LIST = {
    "response": {
        "serverlist": [
            {"endpoint": f"ext1-fra1.steamserver.net:27019\n{INJECTED}", "type": "websockets", "dc": "fra1"},
            {"endpoint": f"evil{chr(0x2028)}{INJECTED}:443", "type": "websockets", "dc": "fra1"},
            {"endpoint": "ext1-sto1.steamserver.net:27019", "type": "websockets", "dc": f"sto1\r\n{INJECTED}"},
            {"endpoint": "ext1-vie1.steamserver.net:443", "type": "websockets", "dc": f"vie1\x85{INJECTED}"},
        ]
    }
}
INJECTING_SDR = {
    "pops": {
        "fra": {"desc": f"Frankfurt\n{INJECTED}", "relays": [{"ipv4": "155.133.226.3"}]},
        f"vie\n{INJECTED}": {"desc": "Vienna", "relays": [{"ipv4": "155.133.226.2"}]},
        "sto": {"desc": f"Stockholm{chr(0x2029)}{INJECTED}", "relays": [{"ipv4": f"155.133.226.1\n{INJECTED}"}]},
        "dxb": {"desc": f"Dubai\x0b{INJECTED}", "relays": [{"ipv4": "155.133.226.4"}]},
    }
}


def test_valve_text_with_line_breaks_cannot_fake_a_line_of_the_report(net):
    net.http[checks.CM_LIST_URL] = INJECTING_CM_LIST
    net.http[checks.SDR_CONFIG_URL] = INJECTING_SDR
    net.http[checks.GC_VERSION_URL] = {
        "result": {"success": True, "active_version": f"7001\n{INJECTED}", "deploy_version": 7000}
    }
    results, verdict = run(net)
    text = build_report(results, verdict)
    lines = text.splitlines()
    assert [line for line in lines if line.lstrip().startswith("VERDICT")] == []
    assert "VERDICT" not in text  # nor anywhere inside a line
    assert len(lines) == len(text.split("\n"))  # no line break but "\n", which only the report itself writes
    # The good parts are still shown, with the code or "?" in place of a refused name.
    assert "ext1-sto1.steamserver.net:27019 [?] — 35 ms" in text
    assert "ext1-vie1.steamserver.net:443 [?] — 35 ms" in text
    assert results["steam_cm"].data == {"fallback": False, "ok": 2, "total": 2}  # the two endpoints with breaks
    assert "fra (fra) — 52 ms" in text
    assert "dxb (dxb) — 71 ms" in text
    assert "version 7000" in results["dota_gc"].summary
    assert results["steam_api"].details[0].params["dcs"] == "fra1"
    assert {r.status for r in results.values()} == {Status.OK}
    assert verdict.side == Side.PC


def test_valve_text_with_line_breaks_cannot_fake_a_line_of_the_cli_output(net, capsys):
    net.http[checks.CM_LIST_URL] = INJECTING_CM_LIST
    net.http[checks.SDR_CONFIG_URL] = INJECTING_SDR
    assert wholagged.run_cli() == 0
    out = capsys.readouterr().out
    assert "VERDICT" not in out
    assert out.splitlines() == out.removesuffix("\n").split("\n")  # no line break but print's own "\n"
    assert "\x1b" not in out  # no terminal escape either


def test_a_crashing_check_does_not_kill_the_run(net, monkeypatch):
    def boom(ctx):
        raise RuntimeError("bug")

    patched = list(checks.CHECKS)
    spec = patched[4]
    patched[4] = checks.CheckSpec(spec.key, spec.title_key, spec.hint_key, boom)
    monkeypatch.setattr(checks, "CHECKS", patched)
    results = run_checks()
    assert results["dota_gc"].status == Status.SKIP
    assert results["dota_gc"].title.key == "check.dota_gc.title"  # the spec passes keys, not rendered titles
    assert results["relays"].status == Status.OK
