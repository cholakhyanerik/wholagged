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
    # The verdict (`verdict.decide()`): one headline and one explanation per rule. {loss} is a raw percentage,
    # keep its ":.0f" (no decimals); {ms} and {jitter} are already formatted like "187 ms".
    "verdict.no_internet.headline": "Խնդիրը քո internet-ն է",
    "verdict.no_internet.explanation": "Համակարգիչը չի կարողանում միանալ ոչ մի արտաքին սերվերի, ոչ միայն Valve-ին։",
    "verdict.dns.headline": "Խնդիրը DNS-ն է",
    "verdict.dns.explanation": (
        "Internet-ն աշխատում է, բայց Steam-ի հասցեները չեն լուծվում։ Dota-ն չի գտնում Valve-ի սերվերները։"
    ),
    "verdict.cert.headline": "Խնդիրը HTTPS սերտիֆիկատների ստուգումն է",
    "verdict.cert.explanation": (
        "Internet-ն աշխատում է, բայց Steam-ի հետ անվտանգ (HTTPS) կապը չի հաստատվում, "
        "որովհետև սերտիֆիկատի ստուգումը ձախողվում է։ Սովորաբար սա provider-ի խնդիր չէ. "
        "պատճառը համակարգչում է կամ ցանցի մուտքի էջում։"
    ),
    "verdict.valve.headline": "Խնդիրը, ամենայն հավանականությամբ, Valve-ի կողմից է",
    "verdict.valve.explanation": (
        "Քո կապը մինչև Valve-ի սերվերները հասնում է, բայց Valve-ը սխալ է վերադարձնում "
        "կամ Dota GC-ն չի պատասխանում։ Քո կողմից ուղղելու բան չկա։"
    ),
    "verdict.unreachable.headline": "Valve-ի սերվերներին չես հասնում",
    "verdict.unreachable.explanation": (
        "Internet-ն աշխատում է, բայց Steam-ի ոչ մի սերվերի չհաջողվեց միանալ։ "
        "Կամ Steam-ն է ամբողջությամբ ընկած, կամ provider-ը, VPN-ը կամ firewall-ը փակում է ճանապարհը դեպի Valve։"
    ),
    "verdict.partial.headline": "Valve-ի սերվերների մի մասը քեզ համար փակ է",
    "verdict.partial.explanation": (
        "Steam-ի որոշ սերվերներ պատասխանում են, որոշները՝ ոչ։ Սա սովորաբար firewall-ի, VPN-ի "
        "կամ provider-ի routing-ի խնդիր է։"
    ),
    "verdict.routing.headline": "Ճանապարհը դեպի Valve-ի խաղային ցանց խափանված է",
    "verdict.routing.explanation": (
        "Steam-ը և internet-ը հասանելի են, բայց Valve-ի relay սերվերները ping-ին չեն պատասխանում։ "
        "Սա սովորաբար provider-ի routing-ի խնդիր է։"
    ),
    "verdict.lossy.headline": "Կապը կա, բայց անկայուն է (packet loss)",
    "verdict.lossy.explanation": (
        "Մինչև Valve-ի relay սերվերները կորչում է փաթեթների մոտ {loss:.0f}%-ը։ "
        "Հենց սա է բերում lag-ի, disconnect-ի և GC-ի հետ կապի կորստի։"
    ),
    "verdict.high_ping.headline": "Կապը կա, բայց ping-ը բարձր է",
    "verdict.high_ping.explanation": (
        "Մինչև Valve-ի ամենամոտ relay-ը ping-ը {ms} է։ Խաղալ հնարավոր է, բայց կզգաս lag։"
    ),
    "verdict.jittery.headline": "Կապը կա, բայց ping-ը տատանվում է",
    "verdict.jittery.explanation": (
        "Jitter-ը {jitter} է. ping-ը ցատկում է, և խաղում դա զգացվում է որպես rubber-banding։"
    ),
    "verdict.pc.headline": "Ցանցը կարգին է, Valve-ն էլ պատասխանում է",
    "verdict.pc.explanation": (
        "Internet-ը, DNS-ը, Steam-ը և Valve-ի խաղային ցանցը պատասխանում են։ Եթե Dota-ն դեռ գրում է "
        "«Searching for Game Coordinator», խնդիրը հավանաբար համակարգչում կամ Steam client-ում է։"
    ),
    # Advice: things the user can do now. One key per piece of advice, shared by the verdicts that give it.
    # Phrases used inside other advice: {steamstat}, {hotspot} and {report_to_isp} are the advice of the same
    # name (advice.steamstat, …), each already translated.
    "advice.hotspot": (
        "Hotspot թեստ. միացիր հեռախոսի mobile internet-ին և նորից ստուգիր։ "
        "Եթե hotspot-ով աշխատում է, խնդիրը տան provider-ի մոտ է"
    ),
    "advice.steamstat": "Բաց արա steamstat.us և նայիր Dota 2 Game Coordinator տողը",
    "advice.report_to_isp": (
        "Սեղմիր «Պատճենել report-ը» և ուղարկիր provider-ի support-ին. դա փաստ է, ոչ թե գանգատ"
    ),
    "advice.router_power_cycle": "Ստուգիր router-ը. անջատիր 30 վայրկյանով և նորից միացրու",
    "advice.wifi_try_cable": "Եթե Wi-Fi ես, փորձիր cable-ով կամ ավելի մոտ router-ին",
    "advice.call_isp": "Եթե router-ը վերագործարկելուց հետո էլ չկա, զանգիր provider-ին",
    "advice.dns_change": "Փոխիր DNS-ը 1.1.1.1 և 8.8.8.8 (Windows → Network adapter → IPv4 → DNS)",
    "advice.dns_flush": "Cmd-ում գործարկիր՝ ipconfig /flushdns",
    "advice.dns_vpn_adblock": "Անջատիր VPN-ը կամ ad-blocker DNS-ը (օր.՝ AdGuard, Pi-hole), եթե ունես",
    "advice.cert_clock": (
        "Ստուգիր համակարգչի ժամը, ամսաթիվը և ժամային գոտին. սխալ ժամի դեպքում սերտիֆիկատները չեն ընդունվում"
    ),
    "advice.cert_antivirus": "Ժամանակավորապես անջատիր antivirus-ի HTTPS / SSL ստուգումը (web shield) և նորից ստուգիր",
    "advice.cert_captive_portal": "Եթե հյուրանոցի կամ սրճարանի Wi-Fi ես, բաց արա browser-ը և մուտք գործիր ցանցի էջով",
    "advice.cert_macos_python": "Եթե Python-ը python.org-ից է, գործարկիր «Install Certificates.command»-ը",
    "advice.steamstat_wait": "{steamstat}. եթե այնտեղ էլ կարմիր է, ուղղակի սպասիր",
    "advice.valve_recovers": "Սովորաբար Valve-ը վերականգնում է րոպեներից մինչև մեկ ժամվա ընթացքում",
    "advice.after_patch": "Patch-ից հետո առաջին ժամին այսպիսի բան հաճախ է լինում",
    "advice.steamstat_all_red": "{steamstat}. եթե ամեն ինչ կարմիր է, խնդիրը Valve-ինն է",
    "advice.if_green_hotspot": "Եթե այնտեղ կանաչ է → {hotspot}",
    "advice.vpn_firewall_off": "Անջատիր VPN-ը և ժամանակավորապես antivirus-ի firewall-ը",
    "advice.firewall_allow": "Windows Firewall-ում թույլատրիր steam.exe-ն և dota2.exe-ն",
    "advice.vpn_proxy_off": "Անջատիր VPN-ը / proxy-ն",
    "advice.gaming_vpn": "Gaming VPN-ը (route optimizer) երբեմն շրջանցում է վատ route-ը",
    "advice.use_cable": "Wi-Fi-ի փոխարեն միացիր cable-ով",
    "advice.close_downloads_torrents": "Փակիր download-ները, torrent-ները, stream-ները",
    "advice.close_downloads": "Փակիր download-ները և stream-ները",
    "advice.restart_router": "Վերագործարկիր router-ը",
    "advice.report_if_loss_on_cable": "Եթե cable-ով էլ է կորուստ, {report_to_isp}",
    "advice.nearest_region": "Dota-ի matchmaking-ում ընտրիր ամենամոտ region-ը (relay-ների ցուցակը տես վերևում)",
    "advice.network_hog": "Ստուգիր՝ արդյոք մեկ ուրիշը ցանցը չի ծանրաբեռնում",
    "advice.steam_restart": "Steam-ից ամբողջությամբ դուրս արի (Steam → Exit) և նորից մտիր",
    "advice.verify_files": "Dota 2 → Properties → Installed Files → Verify integrity of game files",
    "advice.clear_launch_options": "Dota 2 → Properties → ջնջիր Launch options-ը",
    "advice.vpn_off": "Անջատիր VPN-ը, եթե միացված է",
    "advice.gc_unchecked": "GC-ն ուղղակիորեն ստուգել չհաջողվեց. {steamstat}",
    "advice.relays_icmp_blocked": "Relay-ների ping-ը չստուգվեց (ICMP-ն փակ է), packet loss-ը հայտնի չէ",
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
