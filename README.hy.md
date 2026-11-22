[English](README.md) · **Հայերեն**

# wholagged

[![Python 3.15+](https://img.shields.io/badge/python-3.15%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows-0078D6?logo=windows&logoColor=white)](#պահանջներ)
[![GUI: PySide6](https://img.shields.io/badge/GUI-PySide6-41CD52?logo=qt&logoColor=white)](https://doc.qt.io/qtforpython-6/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Sponsor](https://img.shields.io/badge/sponsor-GitHub%20Sponsors-EA4AAA?logo=githubsponsors&logoColor=white)](#աջակցիր-նախագծին)

**Dota 2-ը կախվել է «Searching for Game Coordinator»-ի վրա։ Խնդիրը քո internet-ի՞ց է, provider-ի՞ց, թե՞ Valve-ի սերվերներից։**

wholagged-ը փոքր desktop tool է Windows-ի համար (macOS-ի և Linux-ի աջակցությունն ընթացքի մեջ է), որը մոտ 10–20 վայրկյանում պատասխանում է այդ մեկ հարցին։
Այն կատարում է վեց ստուգում՝ internet կապից մինչև Valve-ի խաղային relay-ների ping-ն ու packet loss-ը,
և ասում է, թե որտեղ է խնդիրը և ինչպես այն ուղղել։

## Հնարավորություններ

- **Մեկ սեղմումով ստուգում։** Վեց ստուգումները կատարվում են իրար հետևից, և պատուհանը թարմանում է ամեն մեկի ավարտին։
- **Հստակ եզրակացություն։** Tool-ն ասում է, թե ում կողմից է խնդիրը (քո, provider-ի, Valve-ի, թե համակարգչի / Steam client-ի), և թվարկում է, թե ինչ անել։
- **Report, որը կարելի է պատճենել։** «Պատճենել report-ը» կոճակը ամբողջ արդյունքը պատճենում է clipboard text-ով, որ ուղարկես provider-ի support-ին որպես ապացույց։
- **Admin իրավունք պետք չէ։** Ping-ն արվում է անմիջապես Windows-ի `IcmpSendEcho` API-ով, դրա համար UAC-ի հարցում չկա, console-ի պատուհան չի բացվում, և արդյունքը կախված չէ Windows-ի լեզվից։
- **Պատուհան կամ terminal։** Լռելյայն բացվում է PySide6 պատուհան, իսկ `--cli`-ով նույն ստուգումները տպվում են terminal-ում։
- **Արագ հղումներ** դեպի [steamstat.us](https://steamstat.us/) և [isdown.app](https://isdown.app/status/dota-2), որ համեմատես, թե ինչ են տեսնում մյուս խաղացողները։

## Պահանջներ

- Windows 10 կամ 11 (macOS-ի և Linux-ի համար տես [Պլատֆորմների աջակցություն](#պլատֆորմների-աջակցություն))
- Astral-ի [uv](https://docs.astral.sh/uv/)-ն։ **uv-ը պարտադիր է.** նախագիծը կառավարվում է միայն uv-ով
  (`pyproject.toml` + `uv.lock`)։ `requirements.txt` չկա, և `pip install`-ը չի աջակցվում։
  Եթե Python 3.15 չունես, uv-ը ինքը կներբեռնի այն։

## Գործարկում

```powershell
git clone https://github.com/cholakhyanerik/wholagged.git
cd wholagged
uv sync
uv run dota-netcheck          # բացում է պատուհանը
```

Այլ հրամաններ.

```powershell
uv run dota-netcheck --cli    # terminal-ում, առանց պատուհանի
uv run pytest                 # test-երը (առանց internet-ի, fake ցանցով)
```

## Ինչ է ստուգում

| # | Ստուգում | Ինչպես | Ինչ է ցույց տալիս |
|---|---|---|---|
| 1 | Internet կապ | TCP կապ 443 port-ով դեպի 1.1.1.1, 8.8.8.8 և 9.9.9.9 (IP-ներով, առանց DNS-ի) | Internet ընդհանրապես կա՞ |
| 2 | DNS | Լուծում է `api.steampowered.com`, `steamcommunity.com` և `google.com` հասցեները | DNS-ը գտնո՞ւմ է Steam-ը |
| 3 | Steam Web API | `ISteamDirectory/GetCMListForConnect` | Valve-ին հասնո՞ւմ ես, և Valve-ը նորմալ պատասխանո՞ւմ է |
| 4 | Steam login սերվերներ | TCP կապ դեպի մոտակա 6 CM (connection manager) սերվեր | Steam client-ը կարո՞ղ է login լինել |
| 5 | Dota 2 Game Coordinator | `IGCVersion_570/GetServerVersion` | GC-ն պատասխանո՞ւմ է (անուղղակի ստուգում) |
| 6 | Valve-ի խաղային ցանց | ICMP ping դեպի Valve-ի SDR relay-ները (`GetSDRConfig`-ից), հետո 10-ական ping ամենաարագ 3-ին | Ping, packet loss, jitter և route-ի խնդիրներ |

Եթե internet չկա, մնացած ստուգումները բաց են թողնվում։ Եթե CM սերվերների ցուցակը չստացվի, 4-րդ ստուգումը
փոխարենը ստուգում է Steam-ի web սերվերները։ Եթե որևէ ստուգում crash լինի, այն նշվում է որպես «Բաց թողնվեց», իսկ մնացածները շարունակում են աշխատել։

## Ինչպես է որոշվում եզրակացությունը

[`verdict.py`](src/dota_netcheck/verdict.py)-ի կանոնները ստուգվում են վերևից ներքև, և առաջին համընկնող կանոնն է որոշում եզրակացությունը.

1. Internet չկա → **քո կողմից**
2. DNS-ը չի լուծում Steam-ը → **քո կողմից (DNS)**
3. Valve-ը պատասխանում է 5xx սխալով կամ դատարկ սերվերների ցուցակով, կամ GC-ն վերադարձնում է `success=false` → **Valve-ի կողմից**
4. Internet կա, բայց Steam-ի ոչ մի սերվեր հասանելի չէ → **Valve կամ provider** (նայիր steamstat.us-ը և փորձիր հեռախոսի hotspot-ով)
5. Steam-ի սերվերների միայն մի մասն է հասանելի → **provider, firewall կամ VPN**
6. Steam-ը հասանելի է, 1.1.1.1-ը պատասխանում է ping-ին, իսկ Valve-ի relay-ները՝ ոչ → **provider-ի route-ը դեպի Valve**
7. Packet loss > 5%, ping > 150 ms կամ jitter > 30 ms → **կապի որակը**
8. Ամեն ինչ կարգին է → **ցանցը կարգին է, խնդիրը համակարգչում կամ Steam client-ում է**

Ամեն եզրակացության հետ կան գործնական խորհուրդներ. օրինակ՝ վերագործարկել router-ը, DNS-ը փոխել 1.1.1.1 / 8.8.8.8,
firewall-ում թույլատրել `steam.exe`-ն և `dota2.exe`-ն, ստուգել հեռախոսի hotspot-ով կամ ստուգել խաղի ֆայլերը։

## Սահմանափակումներ

- GC-ի ուղղակի ստուգումը պահանջում է Steam account-ով login, դրա համար tool-ը GC-ն ստուգում է անուղղակի՝ Web API-ի միջոցով։
  Եթե endpoint-ը փոխվի, ստուգումը կնշվի որպես «Բաց թողնվեց», և tool-ը մեղքը Valve-ի վրա չի գցի։
- steamstat.us-ի data endpoint-ը public API չէ, և կայքի տերերը խնդրում են այն չօգտագործել, դրա համար tool-ը միայն բացում է կայքը browser-ում։
- Եթե ցանցում ICMP-ն փակ է, relay-ների ping-ը հնարավոր չէ չափել, և այդ ստուգումը կնշվի որպես «Բաց թողնվեց»։

## Պլատֆորմների աջակցություն

Նպատակն այն է, որ tool-ն աշխատի Windows-ում, macOS-ում և Linux-ում։ Առայժմ լիարժեք աջակցվում է միայն Windows-ը։

| Պլատֆորմ | Վիճակ |
|---|---|
| Windows 10 / 11 | ✅ Լիարժեք աջակցվում է |
| Linux | ⚠️ Աշխատում է, բայց կան հայտնի խնդիրներ |
| macOS | ⚠️ Աշխատում է, բայց relay-ների ping-ը կոտրված է |

### Հայտնի խնդիրներ (կուղղվեն)

- **macOS. relay-ների ping-ը միշտ ձախողվում է։** Windows-ից դուրս tool-ը կանչում է համակարգի `ping` հրամանը `-W 1`-ով։
  Linux-ում `-W`-ն վայրկյան է, իսկ macOS-ում՝ միլիվայրկյան, այնպես որ ամեն ping 1 ms հետո դադարում է սպասել։
  Արդյունքում tool-ը գրում է, որ ICMP-ն փակ է, և բաց է թողնում ping-ի, packet loss-ի և jitter-ի ստուգումը։
- **Linux. ping-ի արդյունքը կարդացվում է `ping`-ի text-ից։** Սովորական `time=… ms` ձևաչափով աշխատում է, բայց այդ text-ը
  կարող է կախված լինել համակարգի լեզվից։ Պետք է գործարկել չեզոք locale-ով կամ անել native implementation, ինչպես Windows-ում։
- **Խորհուրդները Windows-ի համար են։** Որոշ խորհուրդներում նշված են Windows Firewall, `ipconfig /flushdns`, network adapter-ի կարգավորումներ
  և `steam.exe` / `dota2.exe`։ macOS-ում և Linux-ում դրանք չեն գործում։
- **SSL certificate-ի խնդիրները վերագրվում են provider-ին։** Եթե Python-ը չգտնի համակարգի CA certificate-ները
  (դա լինում է macOS-ի որոշ Python տեղադրումներում), Steam API-ի հարցումները ձախողվում են SSL սխալով։ Tool-ը եզրակացնում է,
  որ provider-ը փակում է Valve-ի սերվերների մի մասը, մինչդեռ իրական խնդիրը համակարգչում է։
- **macOS-ում և Linux-ում CI դեռ չկա։** Test-երը օգտագործում են fake ցանց և պետք է ամենուր անցնեն, բայց վերևի խնդիրները չեն ծածկում։

### Համակարգի նվազագույն տարբերակներ

Սրանք վերցված են `uv.lock`-ի PySide6 wheel-երից.

- macOS 14 Sonoma կամ ավելի նոր
- Linux x86_64՝ glibc 2.34+ (օրինակ՝ Ubuntu 22.04+, Debian 12+)
- Linux ARM64՝ glibc 2.39+ (օրինակ՝ Ubuntu 24.04+)
- Linux-ում X11-ով Qt-ին պետք է նաև `libxcb-cursor0` system package-ը (Debian/Ubuntu-ում՝ `sudo apt install libxcb-cursor0`)

## Կառուցվածք

```
src/dota_netcheck/
  __init__.py   մուտքի կետը (լռելյայն՝ պատուհան, --cli՝ terminal)
  checks.py     վեց ստուգումները (միայն standard library)
  icmp.py       ping-ը Windows-ում IcmpSendEcho-ով (ctypes)
  verdict.py    ստուգումների արդյունքից հանում է եզրակացությունը
  report.py     text report
  models.py     data class-ներ՝ CheckResult, Verdict, Status, Side
  gui.py        PySide6 պատուհան
tests/
  fakes.py            fake ցանց՝ ամեն մասը կոտրելու switch-երով
  test_scenarios.py   end-to-end սցենարներ. կոտրիր մի բան, սպասիր մեկ եզրակացություն
  test_parsing.py     Valve-ի API պատասխանների parsing
```

## Հետագա պլաններ

Հիմնական tool-ը անվճար է և open source, և այդպես էլ կմնա։

Պլանավորված է.

- **Cross-platform.** ուղղել [հայտնի խնդիրները](#հայտնի-խնդիրներ-կուղղվեն) և CI-ում test-երը գործարկել Windows-ում, macOS-ում և Linux-ում։
- **Քո ցանցը, թե provider-ը.** ping անել նաև քո router-ին, որ tool-ը կարողանա տարբերել վատ Wi-Fi-ը
  provider-ի կողմի խնդրից։
- **Valve-ի այլ խաղեր.** CS2-ն և Deadlock-ը օգտագործում են Valve-ի նույն relay ցանցը, այնպես որ նույն ստուգումները կաշխատեն նաև դրանց համար։
  wholagged անունը կապված չէ որևէ խաղի հետ, դրա համար այն կմնա նույնը։
- **Մեկ անուն ամենուր.** պատուհանի վերնագիրը, package-ը և հրամանը դեռ կոչվում են
  *Dota 2 Network Check* / `dota-netcheck`։ Դրանք կվերանվանվեն wholagged։
- **Ֆոնային մոնիթորինգ (վճարովի Pro տարբերակ).** ամբողջ օրը գրանցել ping-ն ու packet loss-ը, ցույց տալ գրաֆիկներ
  և պատրաստել PDF report, որը կարող ես ուղարկել provider-ին որպես ապացույց։
- **Microsoft Store**-ում թողարկում։

### Թափանցիկություն

Ապագայում app-ը կարող է առաջարկել երրորդ կողմի ծառայություն, օրինակ՝ gaming route optimizer, և այդ առաջարկներից
մի քանիսը կարող են լինել affiliate հղումներ։ Եթե դա լինի, այդ առաջարկները.

- միշտ հստակ նշված կլինեն որպես առաջարկ և որպես affiliate հղում.
- կհայտնվեն միայն այն ժամանակ, երբ եզրակացությունը ցույց է տալիս provider-ի route-ը կամ անկայուն կապը, որտեղ նման ծառայությունն իսկապես կարող է օգնել.
- երբեք չեն հայտնվի, երբ խնդիրը Valve-ի կողմից է, քո Wi-Fi-ում կամ համակարգչում.
- երբեք չեն փոխի եզրակացությունը։ Եզրակացության տրամաբանությունը open source է [`verdict.py`](src/dota_netcheck/verdict.py)-ում, և ցանկացած մարդ կարող է դա ստուգել։

## Աջակցիր նախագծին

Եթե այս tool-ը queue-ում սպասելիս քեզ մի քիչ նյարդեր խնայեց, կարող ես աջակցել նրա զարգացմանը GitHub Sponsors-ով.

[![Sponsor on GitHub](https://img.shields.io/badge/Sponsor-%E2%9D%A4-EA4AAA?style=for-the-badge&logo=githubsponsors&logoColor=white)](https://github.com/sponsors/cholakhyanerik)

## Լիցենզիա

Նախագիծը տարածվում է [MIT License](LICENSE)-ով։

## Իրավական նշում

Dota 2-ը և Steam-ը Valve Corporation-ի trademark-երն են։ Այս նախագիծը կապված չէ Valve-ի հետ և Valve-ի կողմից հաստատված չէ։
