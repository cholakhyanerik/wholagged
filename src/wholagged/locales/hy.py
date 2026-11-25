"""Armenian texts: the source catalogue."""

from __future__ import annotations

MESSAGES: dict[str, str] = {
    "app.subtitle": "Ստուգում է Dota 2-ի կապը՝ խնդիրը քո internet-ի՞ց է, provider-ի՞ց, թե՞ Valve-ի սերվերներից",
    # The six checks (`checks.CHECKS`): the row title, and the hint shown before and while the check runs.
    "check.internet.title": "Internet կապ",
    "check.internet.hint": "Միանում է Cloudflare, Google, Quad9 սերվերներին",
    "check.dns.title": "DNS",
    "check.dns.hint": "Լուծում է Steam-ի և Google-ի հասցեները",
    "check.steam_api.title": "Steam Web API",
    "check.steam_api.hint": "Valve-ից ստանում է login սերվերների ցուցակը",
    "check.steam_cm.title": "Steam login սերվերներ",
    "check.steam_cm.hint": "Միանում է Steam-ի մոտակա CM սերվերներին",
    "check.dota_gc.title": "Dota 2 Game Coordinator",
    "check.dota_gc.hint": "Հարցնում է GC-ի version-ը Web API-ից",
    "check.relays.title": "Valve-ի խաղային ցանց",
    "check.relays.hint": "Ping, packet loss և jitter Valve-ի relay-ներին",
}
