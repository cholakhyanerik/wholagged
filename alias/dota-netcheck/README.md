# dota-netcheck

English, then Հայերեն and Русский below.

**dota-netcheck is the old name of [wholagged](https://pypi.org/project/wholagged/).**

- This package has no code of its own. It installs wholagged and keeps the old `dota-netcheck` command,
  which starts the same app.
- If Dota 2 lags or is stuck on "Searching for Game Coordinator", wholagged tells you whose side the
  problem is on: your internet, your provider, or Valve's servers.
- Use the new name:

```powershell
uvx wholagged
uv tool install wholagged
```

- If you installed the old name as a uv tool, remove it first: two uv tools can't both own the
  `dota-netcheck` command, so installing wholagged would stop with "Executable already exists".

```powershell
uv tool uninstall dota-netcheck
uv tool install wholagged
```

- Docs, changelog and source: https://github.com/cholakhyanerik/wholagged
- License: PolyForm Noncommercial 1.0.0 (the `LICENSE` file).

## Հայերեն

**dota-netcheck-ը [wholagged](https://pypi.org/project/wholagged/)-ի հին անունն է։**

- Այս package-ը սեփական կոդ չունի։ Այն տեղադրում է wholagged-ը և պահպանում է հին `dota-netcheck` հրամանը,
  որը գործարկում է նույն app-ը։
- Եթե Dota 2-ում lag ես զգում կամ խաղը կախվել է «Searching for Game Coordinator»-ի վրա, wholagged-ն ասում է,
  թե խնդիրը քո internet-ից է, provider-ից, թե Valve-ի սերվերներից։
- Օգտագործիր նոր անունը.

```powershell
uvx wholagged
uv tool install wholagged
```

- Եթե հին անունը տեղադրել ես որպես uv tool, նախ հեռացրու այն. նույն `dota-netcheck` հրամանը չի կարող
  պատկանել երկու uv tool-ի, դրա համար wholagged-ի տեղադրումը կընդհատվի «Executable already exists» սխալով։

```powershell
uv tool uninstall dota-netcheck
uv tool install wholagged
```

- Փաստաթղթավորումը, փոփոխությունների պատմությունը և source code-ը՝ https://github.com/cholakhyanerik/wholagged
- Լիցենզիա՝ PolyForm Noncommercial 1.0.0 (`LICENSE` ֆայլը)։

## Русский

**dota-netcheck — старое название [wholagged](https://pypi.org/project/wholagged/).**

- В этом пакете нет своего кода. Он устанавливает wholagged и сохраняет старую команду `dota-netcheck`,
  которая запускает то же приложение.
- Если Dota 2 лагает или висит на «Searching for Game Coordinator», wholagged скажет, где проблема:
  в твоём интернете, у провайдера или на серверах Valve.
- Пользуйся новым названием:

```powershell
uvx wholagged
uv tool install wholagged
```

- Если ты установил старое название как инструмент uv, сначала удали его: одна и та же команда `dota-netcheck`
  не может принадлежать двум инструментам uv, поэтому установка wholagged прервётся с ошибкой
  «Executable already exists».

```powershell
uv tool uninstall dota-netcheck
uv tool install wholagged
```

- Документация, история изменений и исходный код: https://github.com/cholakhyanerik/wholagged
- Лицензия: PolyForm Noncommercial 1.0.0 (файл `LICENSE`).
