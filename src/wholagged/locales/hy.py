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
    # Steam login (CM) servers; the "web" texts are used when the CM list could not be fetched.
    "check.steam_cm.fallback": "Login սերվերների ցուցակը չստացվեց, ստուգվում են Steam-ի web սերվերները",
    "check.steam_cm.fail": "Steam-ի login սերվերներից ոչ մեկին չհաջողվեց միանալ",
    "check.steam_cm.web_fail": "Steam-ի web սերվերներից ոչ մեկին չհաջողվեց միանալ",
    "check.steam_cm.ok": "Steam-ի login սերվերները հասանելի են ({ok}/{total}, մեդիան {ms})",
    "check.steam_cm.web_ok": "Steam-ի web սերվերները հասանելի են ({ok}/{total}, մեդիան {ms})",
    "check.steam_cm.partial": "Հասանելի է միայն {ok}/{total} սերվեր",
    # Dota 2 Game Coordinator. {version} is Valve's version number.
    "check.dota_gc.note": "Անուղղակի ստուգում է Web API-ի միջոցով. լրիվ վստահության համար նայիր steamstat.us",
    "check.dota_gc.down": "Dota GC-ն չի պատասխանում ({error})",
    "check.dota_gc.unknown": "Չհաջողվեց ստուգել ({error})",
    "check.dota_gc.bad_answer": "Պատասխանը սպասված ձևով չէ. չենք կարող գնահատել",
    "check.dota_gc.ok": "Dota GC-ն պատասխանում է ({ms})",
    "check.dota_gc.ok_version": "Dota GC-ն պատասխանում է ({ms}, version {version})",
    # Valve's game network (relays). {pop} is a relay site's name from Valve ("Frankfurt"); {loss} is a
    # percentage, keep its ":.0f" (no decimals); {avg} and {jitter} are formatted like {ms}, or "—".
    "check.relays.list_failed": "Չհաջողվեց ստանալ relay-ների ցուցակը ({error})",
    "check.relays.empty": "Relay-ների ցուցակը դատարկ է",
    "check.relays.routing": "Valve-ի relay-ները ping-ին չեն պատասխանում, թեև մնացած internet-ը պատասխանում է",
    "check.relays.checked": "Ստուգված relay-ներ՝ {count}",
    "check.relays.icmp_blocked": "Այս ցանցում ICMP ping-ը կարծես փակ է. relay-ները չենք կարող ստուգել",
    "check.relays.responded": "Պատասխանեց {ok}/{total} relay",
    "check.relays.quality": "{pop}: {sent} ping, կորուստ {loss:.0f}%, միջինը {avg}, jitter {jitter}",
    "check.relays.lossy": "Packet loss {loss:.0f}%. կապն անկայուն է",
    "check.relays.high_ping": "Ping-ը բարձր է՝ {ms} ({pop})",
    "check.relays.jittery": "Ping-ը տատանվում է (jitter {ms})",
    "check.relays.ok": "Լավագույնը՝ {pop}, {ms}, կորուստ {loss:.0f}%",
    # The runner: a check after a failed internet check, and a check that crashed (a bug in the app).
    "check.skipped_no_internet": "Բաց թողնվեց, քանի որ internet չկա",
    "check.internal_error": "Ստուգման ներքին սխալ՝ {error}",
    # Advice in the verdict (the rest moves here in WL-24).
    "advice.relays_unchecked": "Relay-ների ping-ը չստուգվեց, packet loss-ը հայտնի չէ",
    # Short error words, shown in brackets after what failed.
    "error.timeout": "timeout",
    "error.refused": "կապը մերժվեց",
    "error.reset": "կապը խզվեց",
    "error.dns": "DNS-ը չգտավ հասցեն",
    "error.ssl": "SSL սխալ",
    "error.too_big": "պատասխանը չափազանց մեծ է",
    "error.not_json": "պատասխանը JSON չէ",
}
