"""End-to-end scenarios: break one part of the fake network, expect one verdict."""

from __future__ import annotations

import pytest

from dota_netcheck import checks
from dota_netcheck.checks import run_checks
from dota_netcheck.models import Side, Status
from dota_netcheck.report import build_report
from dota_netcheck.verdict import decide

from fakes import FakeNet


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
    net.loss_every = 4  # 25% loss
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


def test_report_contains_everything(net):
    results, verdict = run(net)
    text = build_report(results, verdict)
    for spec in checks.CHECKS:
        assert spec.title in text
    assert verdict.headline in text


def test_garbage_cm_list_is_not_a_crash(net):
    net.http[checks.CM_LIST_URL] = {"response": {"serverlist": ["x", 5, {"endpoint": 7, "dc": ["fra"]}]}}
    results, _ = run(net)
    assert results["steam_api"].status == Status.OK  # one dict entry survives the type checks
    assert results["steam_cm"].data["fallback"] is True  # but it has no usable endpoint


def test_a_crashing_check_does_not_kill_the_run(net, monkeypatch):
    def boom(ctx):
        raise RuntimeError("bug")

    patched = list(checks.CHECKS)
    spec = patched[4]
    patched[4] = checks.CheckSpec(spec.key, spec.title, spec.hint, boom)
    monkeypatch.setattr(checks, "CHECKS", patched)
    results = run_checks()
    assert results["dota_gc"].status == Status.SKIP
    assert results["relays"].status == Status.OK
