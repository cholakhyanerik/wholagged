"""Turns check results into one verdict: whose side the problem is on."""

from __future__ import annotations

import sys

from .i18n import Msg
from .models import CheckResult, Side, Status, Verdict

HOTSPOT = (
    "Hotspot թեստ. միացիր հեռախոսի mobile internet-ին և նորից ստուգիր։ "
    "Եթե hotspot-ով աշխատում է, խնդիրը տան provider-ի մոտ է"
)
STEAMSTAT = "Բաց արա steamstat.us և նայիր Dota 2 Game Coordinator տողը"
REPORT_TO_ISP = "Սեղմիր «Պատճենել report-ը» և ուղարկիր provider-ի support-ին. դա փաստ է, ոչ թե գանգատ"


def decide(results: dict[str, CheckResult]) -> Verdict:
    def status(key: str) -> Status:
        res = results.get(key)
        return res.status if res else Status.SKIP

    def flag(key: str, name: str):
        res = results.get(key)
        return res.data.get(name) if res else None

    # 1. No internet at all.
    if status("internet") == Status.FAIL:
        return Verdict(
            Side.YOU,
            "Խնդիրը քո internet-ն է",
            "Համակարգիչը չի կարողանում միանալ ոչ մի արտաքին սերվերի, ոչ միայն Valve-ին։",
            [
                "Ստուգիր router-ը. անջատիր 30 վայրկյանով և նորից միացրու",
                "Եթե Wi-Fi ես, փորձիր cable-ով կամ ավելի մոտ router-ին",
                "Եթե router-ը վերագործարկելուց հետո էլ չկա, զանգիր provider-ին",
            ],
        )

    # 2. DNS.
    if status("dns") == Status.FAIL or flag("dns", "steam_dns_fail"):
        return Verdict(
            Side.YOU,
            "Խնդիրը DNS-ն է",
            "Internet-ն աշխատում է, բայց Steam-ի հասցեները չեն լուծվում։ Dota-ն չի գտնում Valve-ի սերվերները։",
            [
                "Փոխիր DNS-ը 1.1.1.1 և 8.8.8.8 (Windows → Network adapter → IPv4 → DNS)",
                "Cmd-ում գործարկիր՝ ipconfig /flushdns",
                "Անջատիր VPN-ը կամ ad-blocker DNS-ը (օր.՝ AdGuard, Pi-hole), եթե ունես",
            ],
        )

    # 3. HTTPS to Valve fails the certificate check: a PC-side problem, not the route.
    if flag("steam_api", "cert_error"):
        advice = [
            "Ստուգիր համակարգչի ժամը, ամսաթիվը և ժամային գոտին. սխալ ժամի դեպքում սերտիֆիկատները չեն ընդունվում",
            "Ժամանակավորապես անջատիր antivirus-ի HTTPS / SSL ստուգումը (web shield) և նորից ստուգիր",
            "Եթե հյուրանոցի կամ սրճարանի Wi-Fi ես, բաց արա browser-ը և մուտք գործիր ցանցի էջով",
        ]
        if sys.platform == "darwin":
            advice.append("Եթե Python-ը python.org-ից է, գործարկիր «Install Certificates.command»-ը")
        return Verdict(
            Side.YOU,
            "Խնդիրը HTTPS սերտիֆիկատների ստուգումն է",
            "Internet-ն աշխատում է, բայց Steam-ի հետ անվտանգ (HTTPS) կապը չի հաստատվում, "
            "որովհետև սերտիֆիկատի ստուգումը ձախողվում է։ Սովորաբար սա provider-ի խնդիր չէ. "
            "պատճառը համակարգչում է կամ ցանցի մուտքի էջում։",
            advice,
        )

    # 4. Valve answered, but with an error, or the GC is down.
    if (status("steam_api") == Status.WARN and flag("steam_api", "server_error")) or flag("dota_gc", "gc_down"):
        return Verdict(
            Side.VALVE,
            "Խնդիրը, ամենայն հավանականությամբ, Valve-ի կողմից է",
            "Քո կապը մինչև Valve-ի սերվերները հասնում է, բայց Valve-ը սխալ է վերադարձնում "
            "կամ Dota GC-ն չի պատասխանում։ Քո կողմից ուղղելու բան չկա։",
            [
                STEAMSTAT + ". եթե այնտեղ էլ կարմիր է, ուղղակի սպասիր",
                "Սովորաբար Valve-ը վերականգնում է րոպեներից մինչև մեկ ժամվա ընթացքում",
                "Patch-ից հետո առաջին ժամին այսպիսի բան հաճախ է լինում",
            ],
        )

    # 5. Internet works, but no Steam server is reachable at all.
    if status("steam_api") == Status.FAIL and status("steam_cm") == Status.FAIL:
        return Verdict(
            Side.UNCLEAR,
            "Valve-ի սերվերներին չես հասնում",
            "Internet-ն աշխատում է, բայց Steam-ի ոչ մի սերվերի չհաջողվեց միանալ։ "
            "Կամ Steam-ն է ամբողջությամբ ընկած, կամ provider-ը, VPN-ը կամ firewall-ը փակում է ճանապարհը դեպի Valve։",
            [
                STEAMSTAT + ". եթե ամեն ինչ կարմիր է, խնդիրը Valve-ինն է",
                "Եթե այնտեղ կանաչ է → " + HOTSPOT,
                "Անջատիր VPN-ը և ժամանակավորապես antivirus-ի firewall-ը",
            ],
        )

    # 6. Part of Valve is reachable, part is blocked.
    if Status.FAIL in (status("steam_api"), status("steam_cm")) or status("steam_cm") == Status.WARN:
        return Verdict(
            Side.ISP,
            "Valve-ի սերվերների մի մասը քեզ համար փակ է",
            "Steam-ի որոշ սերվերներ պատասխանում են, որոշները՝ ոչ։ Սա սովորաբար firewall-ի, VPN-ի "
            "կամ provider-ի routing-ի խնդիր է։",
            [
                "Windows Firewall-ում թույլատրիր steam.exe-ն և dota2.exe-ն",
                "Անջատիր VPN-ը / proxy-ն",
                HOTSPOT,
                REPORT_TO_ISP,
            ],
        )

    # 7. Steam is fine, but Valve's game relays don't answer.
    if flag("relays", "routing"):
        return Verdict(
            Side.ISP,
            "Ճանապարհը դեպի Valve-ի խաղային ցանց խափանված է",
            "Steam-ը և internet-ը հասանելի են, բայց Valve-ի relay սերվերները ping-ին չեն պատասխանում։ "
            "Սա սովորաբար provider-ի routing-ի խնդիր է։",
            [HOTSPOT, REPORT_TO_ISP, "Gaming VPN-ը (route optimizer) երբեմն շրջանցում է վատ route-ը"],
        )

    # 8. Connected, but the connection quality is bad.
    if flag("relays", "lossy"):
        return Verdict(
            Side.YOU,
            "Կապը կա, բայց անկայուն է (packet loss)",
            f"Մինչև Valve-ի relay սերվերները կորչում է փաթեթների մոտ {flag('relays', 'loss'):.0f}%-ը։ "
            "Հենց սա է բերում lag-ի, disconnect-ի և GC-ի հետ կապի կորստի։",
            [
                "Wi-Fi-ի փոխարեն միացիր cable-ով",
                "Փակիր download-ները, torrent-ները, stream-ները",
                "Վերագործարկիր router-ը",
                "Եթե cable-ով էլ է կորուստ, " + REPORT_TO_ISP,
            ],
        )
    if flag("relays", "high_ping"):
        return Verdict(
            Side.YOU,
            "Կապը կա, բայց ping-ը բարձր է",
            f"Մինչև Valve-ի ամենամոտ relay-ը ping-ը {flag('relays', 'best_ms'):.0f} ms է։ "
            "Խաղալ հնարավոր է, բայց կզգաս lag։",
            [
                "Dota-ի matchmaking-ում ընտրիր ամենամոտ region-ը (relay-ների ցուցակը տես վերևում)",
                "Ստուգիր՝ արդյոք մեկ ուրիշը ցանցը չի ծանրաբեռնում",
                REPORT_TO_ISP,
            ],
        )
    if flag("relays", "jittery"):
        return Verdict(
            Side.YOU,
            "Կապը կա, բայց ping-ը տատանվում է",
            f"Jitter-ը {flag('relays', 'jitter'):.0f} ms է. ping-ը ցատկում է, և խաղում դա զգացվում է որպես rubber-banding։",
            ["Wi-Fi-ի փոխարեն միացիր cable-ով", "Փակիր download-ները և stream-ները", "Վերագործարկիր router-ը"],
        )

    # 9. Everything answers.
    advice = [
        "Steam-ից ամբողջությամբ դուրս արի (Steam → Exit) և նորից մտիր",
        "Dota 2 → Properties → Installed Files → Verify integrity of game files",
        "Dota 2 → Properties → ջնջիր Launch options-ը",
        "Windows Firewall-ում թույլատրիր steam.exe-ն և dota2.exe-ն",
        "Անջատիր VPN-ը, եթե միացված է",
    ]
    if status("dota_gc") == Status.SKIP:
        advice.insert(0, "GC-ն ուղղակիորեն ստուգել չհաջողվեց. " + STEAMSTAT)
    if status("relays") == Status.SKIP:
        # Only a blocked ICMP is the network's doing; a bad relay list or a failed download is not.
        if flag("relays", "icmp_blocked"):
            advice.append("Relay-ների ping-ը չստուգվեց (ICMP-ն փակ է), packet loss-ը հայտնի չէ")
        else:
            advice.append(Msg("advice.relays_unchecked"))
    return Verdict(
        Side.PC,
        "Ցանցը կարգին է, Valve-ն էլ պատասխանում է",
        "Internet-ը, DNS-ը, Steam-ը և Valve-ի խաղային ցանցը պատասխանում են։ Եթե Dota-ն դեռ գրում է "
        "«Searching for Game Coordinator», խնդիրը հավանաբար համակարգչում կամ Steam client-ում է։",
        advice,
    )
