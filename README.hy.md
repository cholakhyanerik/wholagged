[English](README.md) · **Հայերեն**

# wholagged

[![CI](https://github.com/cholakhyanerik/wholagged/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/cholakhyanerik/wholagged/actions/workflows/ci.yml)
[![Python 3.15+](https://img.shields.io/badge/python-3.15%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows-0078D6?logo=windows&logoColor=white)](#պահանջներ)
[![GUI: PySide6](https://img.shields.io/badge/GUI-PySide6-41CD52?logo=qt&logoColor=white)](https://doc.qt.io/qtforpython-6/)
[![License: PolyForm Noncommercial](https://img.shields.io/badge/license-PolyForm%20Noncommercial-blue)](LICENSE)
[![Sponsor](https://img.shields.io/badge/sponsor-GitHub%20Sponsors-EA4AAA?logo=githubsponsors&logoColor=white)](#աջակցիր-նախագծին)

**Dota 2-ը կախվել է «Searching for Game Coordinator»-ի վրա։ Խնդիրը քո internet-ի՞ց է, provider-ի՞ց, թե՞ Valve-ի սերվերներից։**

wholagged-ը փոքր desktop tool է, որը մոտ 10–20 վայրկյանում պատասխանում է այդ մեկ հարցին.

- կատարում է վեց ցանցային ստուգում՝ internet կապից մինչև Valve-ի խաղային relay-ների ping-ն ու packet loss-ը.
- ասում է, թե ում կողմից է խնդիրը.
- թվարկում է, թե ինչ անել այն ուղղելու համար։

Tool-ն աշխատում է Windows-ում, իսկ macOS-ի և Linux-ի աջակցությունն ընթացքի մեջ է։

## Հնարավորություններ

- **Մեկ սեղմումով ստուգում։** Վեց ստուգումները կատարվում են իրար հետևից, և պատուհանը թարմանում է ամեն մեկի ավարտին։
- **Հստակ եզրակացություն.** ում կողմից է խնդիրը (քո, provider-ի, Valve-ի, թե համակարգչի / Steam client-ի) և ինչ անել հետո։
- **Report, որը կարելի է պատճենել։** «Պատճենել report-ը» կոճակն ամբողջ արդյունքը պատճենում է clipboard-ում որպես text, որը սկսվում է app-ի անունով և տարբերակով։
  Դա ապացույց է provider-ի support-ի համար։
- **Admin իրավունք պետք չէ։** Ping-ն արվում է անմիջապես Windows-ի `IcmpSendEcho` API-ով.
  - UAC-ի հարցում չկա.
  - console-ի պատուհան չի բացվում.
  - արդյունքը կախված չէ Windows-ի լեզվից։
- **Պատուհան կամ terminal։** Լռելյայն բացվում է PySide6 պատուհան, իսկ `--cli`-ով նույն ստուգումները տպվում են terminal-ում։
- **Արագ հղումներ** դեպի [steamstat.us](https://steamstat.us/) և [isdown.app](https://isdown.app/status/dota-2), որ համեմատես, թե ինչ են տեսնում մյուս խաղացողները։

## Պահանջներ

- Windows 10 կամ 11 (macOS-ի և Linux-ի համար տես [Պլատֆորմների աջակցություն](#պլատֆորմների-աջակցություն))
- Astral-ի [uv](https://docs.astral.sh/uv/)-ն։ **uv-ն պարտադիր է.**
  - նախագիծը կառավարվում է միայն uv-ով (`pyproject.toml` + `uv.lock`).
  - `requirements.txt` չկա, և `pip install`-ը չի աջակցվում.
  - եթե Python 3.15 չունես, uv-ն ինքը կներբեռնի այն։

## Գործարկում

```powershell
git clone https://github.com/cholakhyanerik/wholagged.git
cd wholagged
uv sync
uv run wholagged              # բացում է պատուհանը
```

Այլ հրամաններ.

```powershell
uv run wholagged --cli        # terminal-ում, առանց պատուհանի
uv run pytest                 # test-երը (առանց internet-ի, fake ցանցով)
uv run ruff check             # կոդի ստուգում (lint)
```

Եթե repo-ն արդեն clone ես արել, թարմացրու այսպես.

```powershell
git pull
uv sync
```

Խնդիրների լուծում.

- Եթե clone-ն արել ես v0.2.2-ից առաջ, երբ նախագիծը դեռ wholagged չէր կոչվում, և թարմացնելուց հետո հին `dota-netcheck` հրամանը
  գրում է «Failed to spawn», մեկ անգամ գործարկիր `uv sync --reinstall-package wholagged`։ `wholagged` հրամանն աշխատում է ամեն դեպքում։

## Ինչ է ստուգում

| # | Ստուգում | Ինչպես | Ինչ է ցույց տալիս |
|---|---|---|---|
| 1 | Internet կապ | TCP կապ 443 port-ով դեպի 1.1.1.1, 8.8.8.8 և 9.9.9.9 (IP-ներով, առանց DNS-ի) | Internet ընդհանրապես կա՞ |
| 2 | DNS | Լուծում է `api.steampowered.com`, `steamcommunity.com` և `google.com` հասցեները | DNS-ը գտնո՞ւմ է Steam-ը |
| 3 | Steam Web API | `ISteamDirectory/GetCMListForConnect` | Valve-ին հասնո՞ւմ ես, և Valve-ը նորմալ պատասխանո՞ւմ է |
| 4 | Steam login սերվերներ | TCP կապ դեպի մոտակա 6 CM (connection manager) սերվեր | Steam client-ը կարո՞ղ է login լինել |
| 5 | Dota 2 Game Coordinator | `IGCVersion_570/GetServerVersion` | GC-ն պատասխանո՞ւմ է (անուղղակի ստուգում) |
| 6 | Valve-ի խաղային ցանց | ICMP ping դեպի Valve-ի SDR relay-ները (`GetSDRConfig`-ից), հետո 10-ական ping ամենաարագ 3-ին | Ping, packet loss, jitter և route-ի խնդիրներ |

- Եթե internet չկա, մնացած ստուգումները բաց են թողնվում։
- Եթե CM սերվերների ցուցակը չստացվի կամ դրանում պիտանի սերվեր չլինի, 4-րդ ստուգումը փոխարենը ստուգում է
  Steam-ի web սերվերները։
- Valve-ի այն տվյալները, որոնք ճիշտ չեն թվում (սխալ ձևաչափով հասցե, տարօրինակ անուն, հսկայական ցուցակ),
  բաց են թողնվում, և դրանց պատճառով tool-ը մեղքը երբեք չի գցում քո կամ provider-ի վրա։
- Եթե որևէ ստուգում crash լինի, այն նշվում է որպես «Բաց թողնվեց», իսկ մնացածները շարունակում են աշխատել։

## Ինչպես է որոշվում եզրակացությունը

[`verdict.py`](src/wholagged/verdict.py)-ի կանոնները ստուգվում են վերևից ներքև, և առաջին համընկնող կանոնն է որոշում եզրակացությունը.

1. Internet չկա → **քո կողմից**
2. DNS-ը չի լուծում Steam-ը → **քո կողմից (DNS)**
3. Steam-ի հետ HTTPS կապում սերտիֆիկատի ստուգումը ձախողվում է → **քո կողմից** (համակարգչի սխալ ժամ, antivirus-ի HTTPS ստուգում, Wi-Fi-ի մուտքի էջ կամ բացակայող CA սերտիֆիկատներ, ոչ թե provider-ը)
4. Valve-ը պատասխանում է 5xx սխալով կամ դատարկ սերվերների ցուցակով, կամ GC-ն վերադարձնում է `success=false` → **Valve-ի կողմից**
5. Internet կա, բայց Steam-ի ոչ մի սերվեր հասանելի չէ → **Valve կամ provider** (նայիր steamstat.us-ը և փորձիր հեռախոսի hotspot-ով)
6. Steam-ի սերվերների միայն մի մասն է հասանելի → **provider, firewall կամ VPN**
7. Steam-ը հասանելի է, 1.1.1.1-ը պատասխանում է ping-ին, իսկ Valve-ի relay-ները՝ ոչ → **provider-ի route-ը դեպի Valve**
8. Packet loss > 5%, ping > 150 ms կամ jitter > 30 ms → **կապի որակը**
9. Ամեն ինչ կարգին է → **ցանցը կարգին է, խնդիրը համակարգչում կամ Steam client-ում է**

Ամեն եզրակացության հետ կան գործնական խորհուրդներ, օրինակ.

- վերագործարկել router-ը.
- DNS-ը փոխել 1.1.1.1 / 8.8.8.8.
- firewall-ում թույլատրել `steam.exe`-ն և `dota2.exe`-ն.
- ստուգել հեռախոսի hotspot-ով.
- ստուգել խաղի ֆայլերը։

## Սահմանափակումներ

- **Game Coordinator-ը ստուգվում է անուղղակի՝** Web API-ի միջոցով, քանի որ ուղղակի ստուգումը պահանջում է Steam account-ով login։
  Եթե endpoint-ը փոխվի, ստուգումը կնշվի որպես «Բաց թողնվեց», և tool-ը մեղքը Valve-ի վրա չի գցի։
- **steamstat.us-ը միայն բացվում է browser-ում։** Կայքի data endpoint-ը public API չէ, և տերերը խնդրում են այն չօգտագործել։
- **Եթե ցանցում ICMP-ն փակ է,** relay-ների ping-ը հնարավոր չէ չափել, և այդ ստուգումը կնշվի որպես «Բաց թողնվեց»։

## Պլատֆորմների աջակցություն

Նպատակն այն է, որ tool-ն աշխատի Windows-ում, macOS-ում և Linux-ում։ Առայժմ լիարժեք աջակցվում է միայն Windows-ը։

| Պլատֆորմ | Վիճակ |
|---|---|
| Windows 10 / 11 | ✅ Լիարժեք աջակցվում է |
| Linux | ⚠️ Աշխատում է, բայց կան հայտնի խնդիրներ |
| macOS | ⚠️ Աշխատում է, բայց իրական Mac-ի վրա դեռ չի ստուգվել |

### Հայտնի խնդիրներ (կուղղվեն)

- **macOS և Linux. ping-ն արվում է համակարգի `ping` հրամանով։**
  - Timeout-ը փոխանցվում է ճիշտ միավորով (macOS-ում՝ միլիվայրկյան, Linux-ում՝ վայրկյան)։
  - Հրամանը գործարկվում է չեզոք locale-ով, այնպես որ արդյունքը կախված չէ համակարգի լեզվից։
  - Նախատեսված է native implementation առանց `ping` հրամանի, ինչպես Windows-ում։
- **Խորհուրդները Windows-ի համար են։** Windows Firewall-ի, `ipconfig /flushdns`-ի, network adapter-ի կարգավորումների
  և `steam.exe` / `dota2.exe`-ի մասին խորհուրդները macOS-ում և Linux-ում չեն գործում։
- **macOS-ում CI դեռ չկա։** Կոդի փոփոխությունները ստուգվում են Windows-ում և Linux-ում, իսկ macOS-ի համար դա նախատեսված է։
  Test-երը օգտագործում են fake ցանց, դրա համար վերևի խնդիրները չեն ծածկում։

### Համակարգի նվազագույն տարբերակներ

Սրանք վերցված են `uv.lock`-ի PySide6 wheel-երից.

- macOS 14 Sonoma կամ ավելի նոր
- Linux x86_64՝ glibc 2.34+ (օրինակ՝ Ubuntu 22.04+, Debian 12+)
- Linux ARM64՝ glibc 2.39+ (օրինակ՝ Ubuntu 24.04+)
- Linux-ում X11-ով Qt-ին պետք է նաև `libxcb-cursor0` system package-ը (Debian/Ubuntu-ում՝ `sudo apt install libxcb-cursor0`)

## Կառուցվածք

```
src/wholagged/
  __init__.py   մուտքի կետը (լռելյայն՝ պատուհան, --cli՝ terminal)
  checks.py     վեց ստուգումները (միայն standard library)
  icmp.py       ping-ը Windows-ում IcmpSendEcho-ով (ctypes)
  verdict.py    ստուգումների արդյունքից հանում է եզրակացությունը
  report.py     text report
  models.py     data class-ներ՝ CheckResult, Verdict, Status, Side
  gui.py        PySide6 պատուհան
  i18n.py       թարգմանություններ՝ t(key) ընթացիկ լեզվով (hy / ru / en)
  locales/      տեքստերի catalogue-ները՝ hy.py (աղբյուրը), ru.py, en.py
tests/
  fakes.py            fake ցանց՝ ամեն մասը կոտրելու switch-երով
  test_scenarios.py   end-to-end սցենարներ. կոտրիր մի բան, սպասիր մեկ եզրակացություն
  test_parsing.py     Valve-ի API պատասխանների parsing
  test_net_helpers.py HTTP սխալների մշակում, ping հրամանը, version-ի համաժամեցում
  test_i18n.py        թարգմանությունների որոնում, placeholder-ներ և fallback-ներ
  test_claude_hooks.py Claude Code-ի guard hook-ը այս repo-ում
  test_claude_md.py   ստուգում է, որ CLAUDE.md-ն կարճ է, իսկ կանոնների ֆայլերը՝ ճիշտ կազմված
```

Մշակման նշումներ (անգլերեն).

- նախատեսված աշխատանքը՝ [TASKS.md](TASKS.md).
- փոփոխությունների պատմությունը՝ [CHANGELOG.md](CHANGELOG.md).
- մասնակիցների և AI agent-ների կանոնները՝ [CLAUDE.md](CLAUDE.md), մանրամասները՝ [`.claude/rules/`](.claude/rules/)-ում։

## Հետագա պլաններ

Tool-ն անձնական օգտագործման համար անվճար է, և նրա ամբողջ կոդը, ներառյալ ապագա Pro տարբերակը, կմնա public։

Պլանավորված է.

- **Cross-platform.** ուղղել [հայտնի խնդիրները](#հայտնի-խնդիրներ-կուղղվեն) և CI-ում test-երը գործարկել նաև macOS-ում (Windows-ում և Linux-ում արդեն գործարկվում են)։
- **Քո ցանցը, թե provider-ը.** ping անել նաև քո router-ին, որ tool-ը կարողանա տարբերել վատ Wi-Fi-ը
  provider-ի կողմի խնդրից։
- **Valve-ի այլ խաղեր.** CS2-ն և Deadlock-ը օգտագործում են Valve-ի նույն relay ցանցը, այնպես որ նույն ստուգումները կաշխատեն նաև դրանց համար։
  wholagged անունը կապված չէ որևէ խաղի հետ, դրա համար այն կմնա նույնը։
- **Ֆոնային մոնիթորինգ (վճարովի Pro տարբերակ).** ամբողջ օրը գրանցել ping-ն ու packet loss-ը, ցույց տալ գրաֆիկներ
  և պատրաստել PDF report, որը կարող ես ուղարկել provider-ին որպես ապացույց։
- **Microsoft Store**-ում թողարկում։

### Թափանցիկություն

Ապագայում app-ը կարող է առաջարկել երրորդ կողմի ծառայություն, օրինակ՝ gaming route optimizer, և այդ առաջարկներից
մի քանիսը կարող են լինել affiliate հղումներ։ Եթե դա լինի, այդ առաջարկները.

- միշտ հստակ նշված կլինեն որպես առաջարկ և որպես affiliate հղում.
- կհայտնվեն միայն այն ժամանակ, երբ եզրակացությունը ցույց է տալիս provider-ի route-ը կամ անկայուն կապը, որտեղ նման ծառայությունն իսկապես կարող է օգնել.
- երբեք չեն հայտնվի, երբ խնդիրը Valve-ի կողմից է, քո Wi-Fi-ում կամ համակարգչում.
- երբեք չեն փոխի եզրակացությունը։ Եզրակացության տրամաբանությունը public է [`verdict.py`](src/wholagged/verdict.py)-ում, և ցանկացած մարդ կարող է դա ստուգել։

## Աջակցիր նախագծին

Եթե այս tool-ը queue-ում սպասելիս քեզ մի քիչ նյարդեր խնայեց, կարող ես աջակցել նրա զարգացմանը GitHub Sponsors-ով.

[![Sponsor on GitHub](https://img.shields.io/badge/Sponsor-%E2%9D%A4-EA4AAA?style=for-the-badge&logo=githubsponsors&logoColor=white)](https://github.com/sponsors/cholakhyanerik)

## Լիցենզիա

wholagged-ը **source-available** է և տարածվում է [PolyForm Noncommercial License 1.0.0](LICENSE)-ով։
Կոդը public է, բայց OSI-ի իմաստով open source չէ։

- ✅ **Ոչ commercial օգտագործումն անվճար է.** անձնական օգտագործում, խաղ, hobby նախագծեր և ուսում, ինչպես նաև
  բարեգործական կազմակերպությունների, դպրոցների և այլ ոչ commercial կազմակերպությունների կողմից օգտագործում։
  Կարող ես փոխել կոդը և տարածել այն, եթե այն մնում է ոչ commercial և տարածվում է license-ի հետ միասին։
- ❌ **Commercial օգտագործման համար պետք է հեղինակից առանձին license։** Սա ներառում է software-ը կամ դրա
  հիման վրա ստեղծված ցանկացած բան վաճառելը, այն որպես վճարովի ծառայություն առաջարկելը և business-ի ներսում
  օգտագործելը (օրինակ՝ computer club-ում կամ գրասենյակում)։

Commercial license-ի համար [բաց արա issue](https://github.com/cholakhyanerik/wholagged/issues) կամ կապվիր հեղինակի հետ GitHub-ում։

## Իրավական նշում

Dota 2-ը և Steam-ը Valve Corporation-ի trademark-երն են։ Այս նախագիծը կապված չէ Valve-ի հետ և Valve-ի կողմից հաստատված չէ։
