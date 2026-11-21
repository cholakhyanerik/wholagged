[English](README.md) · **Հայերեն**

# Dota 2 Network Check

Windows desktop tool (Python 3.15 + PySide6 + uv), որը 10–20 վայրկյանում պատասխանում է մեկ հարցի.
**Dota-ի «Searching for Game Coordinator»-ը քո internet-ի՞ց է, provider-ի՞ց, թե՞ Valve-ի սերվերներից։**

## Գործարկում

```powershell
uv sync
uv run dota-netcheck          # պատուհանով
uv run dota-netcheck --cli    # terminal-ում, առանց պատուհանի
uv run pytest                 # test-երը (առանց internet-ի, fake ցանցով)
```

## Ինչ է ստուգում

| # | Ստուգում | Ինչպես | Ինչ է ցույց տալիս |
|---|---|---|---|
| 1 | Internet կապ | TCP 443 դեպի 1.1.1.1, 8.8.8.8, 9.9.9.9 (առանց DNS-ի) | Internet ընդհանրապես կա՞ |
| 2 | DNS | Լուծում է `api.steampowered.com`, `steamcommunity.com`, `google.com` | DNS-ի խնդիր կա՞ |
| 3 | Steam Web API | `ISteamDirectory/GetCMListForConnect` | Valve-ին հասնում ես, և Valve-ը նորմալ պատասխանո՞ւմ է |
| 4 | Steam login սերվերներ | TCP դեպի մոտակա 6 CM սերվեր | Steam client-ը կարո՞ղ է login լինել |
| 5 | Dota 2 Game Coordinator | `IGCVersion_570/GetServerVersion` | GC-ն պատասխանո՞ւմ է (անուղղակի) |
| 6 | Valve-ի խաղային ցանց | ICMP ping դեպի Valve-ի SDR relay-ները (`GetSDRConfig`), 10 ping լավագույն 3-ին | Ping, packet loss, jitter, route-ի խնդիր |

Ping-ը Windows-ում արվում է `IcmpSendEcho`-ով (`iphlpapi.dll`, ctypes). Admin իրավունք պետք չէ,
console չի բացվում, և արդյունքը կախված չէ Windows-ի լեզվից։

## Եզրակացության տրամաբանությունը (`verdict.py`)

1. Internet չկա → **քո կողմից**
2. DNS-ը չի լուծում Steam-ը → **քո կողմից (DNS)**
3. Valve-ը պատասխանում է 5xx-ով կամ GC-ն `success=false` է → **Valve-ի կողմից**
4. Internet կա, բայց Steam-ի ոչ մի սերվեր հասանելի չէ → **Valve կամ provider** (steamstat.us + hotspot թեստ)
5. Steam-ի սերվերների մի մասն է հասանելի → **provider / firewall / VPN**
6. Steam-ը հասանելի է, relay-ները ping-ին չեն պատասխանում, բայց 1.1.1.1-ը պատասխանում է → **provider-ի route**
7. Packet loss > 5%, ping > 150 ms կամ jitter > 30 ms → **կապի որակը**
8. Ամեն ինչ կանաչ է → **ցանցը կարգին է, խնդիրը PC-ում / Steam client-ում է**

«Պատճենել report-ը» կոճակը հավաքում է ամբողջ արդյունքը text-ով. կարելի է ուղարկել provider-ի support-ին։

## Սահմանափակումներ

- GC-ի ուղղակի ստուգումը պահանջում է Steam account-ով login, դրա համար GC-ն ստուգվում է անուղղակի՝ Web API-ի միջոցով։
  Եթե endpoint-ը փոխվի, ստուգումը կնշվի որպես «Բաց թողնվեց», և tool-ը մեղքը Valve-ի վրա չի գցի։
- steamstat.us-ի data endpoint-ը public API չէ, և նրանք խնդրում են այն չօգտագործել. դրա համար tool-ը միայն բացում է կայքը browser-ում։
- Եթե ցանցում ICMP-ն փակ է, relay-ների ping-ը չի ստուգվի (կնշվի «Բաց թողնվեց»)։

## Կառուցվածք

```
src/dota_netcheck/
  checks.py    ստուգումները (միայն standard library)
  icmp.py      ping-ը Windows-ում IcmpSendEcho-ով
  verdict.py   եզրակացությունը
  report.py    text report
  gui.py       PySide6 պատուհան
tests/         fake ցանց + 17 սցենար
```
