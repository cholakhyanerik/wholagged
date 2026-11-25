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
    # Results of the checks. {ms} is already formatted ("42 ms", "<1 ms"); {error} is one of the error.* texts
    # or the system's own words for the error.
    "check.probe_failed": "{target} — չհաջողվեց ({error})",
    "check.internet.fail": "Internet չկա. ոչ մի արտաքին սերվերի չհաջողվեց միանալ",
    "check.internet.ok": "Internet-ն աշխատում է ({ok}/{total}, {ms})",
    "check.dns.name_failed": "{name} — չլուծվեց ({error})",
    "check.dns.fail": "DNS-ը չի աշխատում. ոչ մի հասցե չլուծվեց",
    "check.dns.some_failed": "Որոշ հասցեներ չլուծվեցին՝ {names}",
    "check.dns.ok": "Բոլոր հասցեները լուծվեցին ({ms})",
    "check.steam_api.server_error": "Steam-ը պատասխանեց սխալով ({error})",
    "check.steam_api.cert_error": "Steam-ի հետ անվտանգ (HTTPS) կապը չհաստատվեց ({error})",
    "check.steam_api.certificate": "Սերտիֆիկատ՝ {reason}",
    "check.steam_api.unreachable": "Steam Web API-ին չհաջողվեց հասնել ({error})",
    "check.steam_api.empty": "Steam-ը պատասխանեց, բայց login սերվերների ցուցակը դատարկ է",
    "check.steam_api.ok": "Steam Web API-ն պատասխանեց ({ms}, {count} login սերվեր)",
    "check.steam_api.data_centers": "Ամենամոտ data center-ները՝ {dcs}",
    # Short error words, shown in brackets after what failed.
    "error.timeout": "timeout",
    "error.refused": "կապը մերժվեց",
    "error.reset": "կապը խզվեց",
    "error.dns": "DNS-ը չգտավ հասցեն",
    "error.ssl": "SSL սխալ",
    "error.too_big": "պատասխանը չափազանց մեծ է",
    "error.not_json": "պատասխանը JSON չէ",
}
