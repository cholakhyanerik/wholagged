"""Turns check results into one verdict: whose side the problem is on.

`decide()` runs in the worker thread, so every text of a verdict is an `i18n.Msg`: the text of that moment,
which `i18n.render()` can show again in another language. Advice given by several verdicts has one
`advice.*` key, and a phrase used inside other advice (steamstat.us, the hotspot test, the report for the
provider) is a nested `Msg` param, never glued on with `+`.
"""

from __future__ import annotations

import sys

from .checks import fmt_ms
from .i18n import Msg
from .models import CheckResult, Side, Status, Verdict


def decide(results: dict[str, CheckResult]) -> Verdict:
    def status(key: str) -> Status:
        res = results.get(key)
        return res.status if res else Status.SKIP

    def flag(key: str, name: str):
        res = results.get(key)
        return res.data.get(name) if res else None

    # Phrases used inside other advice. Made here, not at import, so they are in the language of the run.
    hotspot = Msg("advice.hotspot")
    steamstat = Msg("advice.steamstat")
    report_to_isp = Msg("advice.report_to_isp")

    # 1. No internet at all.
    if status("internet") == Status.FAIL:
        return Verdict(
            Side.YOU,
            Msg("verdict.no_internet.headline"),
            Msg("verdict.no_internet.explanation"),
            [Msg("advice.router_power_cycle"), Msg("advice.wifi_try_cable"), Msg("advice.call_isp")],
        )

    # 2. DNS.
    if status("dns") == Status.FAIL or flag("dns", "steam_dns_fail"):
        return Verdict(
            Side.YOU,
            Msg("verdict.dns.headline"),
            Msg("verdict.dns.explanation"),
            [Msg("advice.dns_change"), Msg("advice.dns_flush"), Msg("advice.dns_vpn_adblock")],
        )

    # 3. HTTPS to Valve fails the certificate check: a PC-side problem, not the route.
    if flag("steam_api", "cert_error"):
        advice = [Msg("advice.cert_clock"), Msg("advice.cert_antivirus"), Msg("advice.cert_captive_portal")]
        if sys.platform == "darwin":
            advice.append(Msg("advice.cert_macos_python"))
        return Verdict(Side.YOU, Msg("verdict.cert.headline"), Msg("verdict.cert.explanation"), advice)

    # 4. Valve answered, but with an error, or the GC is down.
    if (status("steam_api") == Status.WARN and flag("steam_api", "server_error")) or flag("dota_gc", "gc_down"):
        return Verdict(
            Side.VALVE,
            Msg("verdict.valve.headline"),
            Msg("verdict.valve.explanation"),
            [Msg("advice.steamstat_wait", steamstat=steamstat), Msg("advice.valve_recovers"),
             Msg("advice.after_patch")],
        )

    # 5. Internet works, but no Steam server is reachable at all.
    if status("steam_api") == Status.FAIL and status("steam_cm") == Status.FAIL:
        return Verdict(
            Side.UNCLEAR,
            Msg("verdict.unreachable.headline"),
            Msg("verdict.unreachable.explanation"),
            [Msg("advice.steamstat_all_red", steamstat=steamstat), Msg("advice.if_green_hotspot", hotspot=hotspot),
             Msg("advice.vpn_firewall_off")],
        )

    # 6. Part of Valve is reachable, part is blocked.
    if Status.FAIL in (status("steam_api"), status("steam_cm")) or status("steam_cm") == Status.WARN:
        return Verdict(
            Side.ISP,
            Msg("verdict.partial.headline"),
            Msg("verdict.partial.explanation"),
            [Msg("advice.firewall_allow"), Msg("advice.vpn_proxy_off"), hotspot, report_to_isp],
        )

    # 7. Steam is fine, but Valve's game relays don't answer.
    if flag("relays", "routing"):
        return Verdict(
            Side.ISP,
            Msg("verdict.routing.headline"),
            Msg("verdict.routing.explanation"),
            [hotspot, report_to_isp, Msg("advice.gaming_vpn")],
        )

    # 8. Connected, but the connection quality is bad.
    if flag("relays", "lossy"):
        return Verdict(
            Side.YOU,
            Msg("verdict.lossy.headline"),
            Msg("verdict.lossy.explanation", loss=flag("relays", "loss")),
            [Msg("advice.use_cable"), Msg("advice.close_downloads_torrents"), Msg("advice.restart_router"),
             Msg("advice.report_if_loss_on_cable", report_to_isp=report_to_isp)],
        )
    if flag("relays", "high_ping"):
        return Verdict(
            Side.YOU,
            Msg("verdict.high_ping.headline"),
            Msg("verdict.high_ping.explanation", ms=fmt_ms(flag("relays", "best_ms"))),
            [Msg("advice.nearest_region"), Msg("advice.network_hog"), report_to_isp],
        )
    if flag("relays", "jittery"):
        return Verdict(
            Side.YOU,
            Msg("verdict.jittery.headline"),
            Msg("verdict.jittery.explanation", jitter=fmt_ms(flag("relays", "jitter"))),
            [Msg("advice.use_cable"), Msg("advice.close_downloads"), Msg("advice.restart_router")],
        )

    # 9. Everything answers.
    advice = [
        Msg("advice.steam_restart"),
        Msg("advice.verify_files"),
        Msg("advice.clear_launch_options"),
        Msg("advice.firewall_allow"),
        Msg("advice.vpn_off"),
    ]
    if status("dota_gc") == Status.SKIP:
        advice.insert(0, Msg("advice.gc_unchecked", steamstat=steamstat))
    if status("relays") == Status.SKIP:
        # Only a blocked ICMP is the network's doing; a bad relay list or a failed download is not.
        advice.append(Msg("advice.relays_icmp_blocked") if flag("relays", "icmp_blocked")
                      else Msg("advice.relays_unchecked"))
    return Verdict(Side.PC, Msg("verdict.pc.headline"), Msg("verdict.pc.explanation"), advice)
