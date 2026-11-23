---
paths:
  - "src/wholagged/checks.py"
  - "src/wholagged/icmp.py"
  - "src/wholagged/verdict.py"
  - "src/wholagged/models.py"
  - "src/wholagged/report.py"
---

# Checks, verdict and report

The step-by-step recipe for a new check or verdict rule is the `add-check` skill.

## Checks (`checks.py`, `icmp.py`)
- Standard library only, so `--cli` runs without Qt.
- Every socket, HTTP and ping call has a timeout (`TCP_TIMEOUT_S`, `HTTP_TIMEOUT_S`, `icmp.DEFAULT_TIMEOUT_MS`).
- Fan out with `checks.parallel()`; its worker count is the bound.
- A check is `check_x(ctx: Context) -> CheckResult(key, status, summary, details, latency_ms, data)`.
  Checks share data through `Context`.
- **`SKIP` means "can't tell" and never blames anyone.**
- Facts for the verdict go in `data` flags.
- `run_checks()` skips everything after a failed internet check and turns a crashing check into `SKIP`.
  Still handle expected failures inside the check.
- The whole run stays within about 10–20 s.

## Blame carefully
- Only evidence that points one way may decide the side.
- Example: `cert_error` is set only for a rejected certificate (`ssl.SSLCertVerificationError`), not for
  any TLS error: a handshake cut off by a middlebox can be the provider.

## Stable identifiers (rule 4)
- Check keys (`internet`, `dns`, `steam_api`, `steam_cm`, `dota_gc`, `relays`) and `data` flags are an API
  for the verdict, the tests and users' reports. Never rename them.
- Keep the report layout (`report.py`): people send it to their provider.

## Verdict (`verdict.py`)
- `decide()` rules run top to bottom; the first match wins.
- Keep the numbered rule comments in order and the README "How the verdict is decided" list in sync.
- Each verdict has a side, a headline, an explanation and 3–5 advice items the user can do now.

## Security of the network code (rule 9)
- Never disable TLS verification.
- Valve's responses are untrusted input: check types before use and cap their size (`MAX_BODY_BYTES`).
- No `shell=True`; `subprocess` gets a fixed argv.
- Ping accepts only a strict IPv4 address (`ipaddress`).
- The User-Agent uses `APP_NAME`. The one literal app name is the fixed 32-byte ICMP payload in `icmp.py`.
