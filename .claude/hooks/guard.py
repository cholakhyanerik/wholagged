"""PreToolUse guard (CLAUDE.md rules 4, 9 and uv only: never break or lose work).

Shell commands (Bash, PowerShell), including commands nested in `uv run`, `bash -c`,
`powershell -Command` and `cmd /c`. Blocked (exit code 2, the reason goes to Claude on stderr):
- pip / venv / poetry / conda and bare `python`: this project uses uv only;
- force / mirror / delete pushes, skipped git hooks, and commands that throw work away
  (`reset --hard`, `clean`, `checkout .`, `restore .`, `stash drop|clear`, `branch -D`);
- recursive deletes of a root, the home folder, the repo or `.git`;
- running a download directly (`curl ... | sh`, `iex (irm ...)`, `bash <(curl ...)`);
- deleting the repo or changing its visibility (gh repo / gh api);
- secrets and the owner's private details in the command, in what `git commit` would record and in
  what `git push` would publish.

File writes (Edit, Write, MultiEdit, NotebookEdit) inside the repo: secrets and private details are blocked.
External tools (web, artifacts, MCP connectors): secrets are blocked; private details make Claude Code ask
the user first (permissionDecision "ask"), since only the user may approve sending them.

Private details are never stored in this public repo. They are read from ~/.claude/private-patterns.txt
(one literal per line, `#` starts a comment) or from the file named by WHOLAGGED_PRIVATE_PATTERNS.

The guard fails open: if it crashes, it prints a warning and lets the call run, so a bug here can't lock
the session. tests/test_claude_hooks.py covers it.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]
ALLOWED_DOCUMENTS = Path(__file__).with_name("allowed-documents.txt")
MAX_DEPTH = 4

SECRET_PATTERNS = [
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}"), "GitHub token"),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{40,}"), "GitHub fine-grained token"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS access key"),
    (re.compile(r"-----BEGIN (?:[A-Z]+ )*PRIVATE KEY-----"), "private key"),
    (re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"), "Slack token"),
    (re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}"), "Anthropic API key"),
    (re.compile(r"\bsk-[A-Za-z0-9]{32,}\b"), "API secret key"),
    (re.compile(r"\b[sr]k_live_[A-Za-z0-9]{20,}"), "Stripe live key"),
    (re.compile(r"\bpypi-AgE[A-Za-z0-9_-]{50,}"), "PyPI token"),
    (re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"), "Google API key"),
    (
        re.compile(
            r"(?i)\b(?:api[_-]?key|secret[_-]?key|client[_-]?secret|access[_-]?token|auth[_-]?token|password|passwd)"
            r"\b\s*[:=]\s*['\"][^'\"\s]{12,}['\"]"
        ),
        "hard-coded credential",
    ),
]
SECRET_FILE_RE = re.compile(
    r"(?i)(^|/)(\.env(\..+)?|\.dev\.vars|\.pypirc|\.npmrc|\.netrc|id_(rsa|ed25519|ecdsa)(\.pub)?"
    r"|credentials[^/]*\.json|secrets?\.[a-z]+|settings\.local\.json)$"
    r"|\.(pem|key|pfx|p12|keystore|jks)$"
)
DOCUMENT_RE = re.compile(r"(?i)\.(pdf|docx?|xlsx?|xlsm|ods|odt|rtf|csv)$")

PY_TOOLS = re.compile(r"^(pip|pip3|pip3\.\d+|pipx|pipenv|poetry|virtualenv|conda|mamba)$")
PY_INTERPRETERS = re.compile(r"^(python|python3|python3\.\d+|pythonw|py)$")
WRAPPERS = {"sudo", "env", "command", "exec", "nohup", "time", "nice", "xargs", "&", "call", "start"}
POSIX_SHELLS = {"bash", "sh", "zsh", "dash", "ksh"}
POWERSHELLS = {"powershell", "pwsh"}
UV_RUN_VALUE_OPTS = {
    "--with", "-w", "--with-editable", "--with-requirements", "--python", "-p", "--package", "--group",
    "--extra", "--only-group", "--no-group", "--env-file", "--directory", "--project", "--index",
    "--default-index", "--index-url", "--extra-index-url", "--find-links", "-f", "--cache-dir",
    "--config-file", "--exclude-newer", "--color", "--prerelease", "--resolution", "--index-strategy",
    "--keyring-provider", "--link-mode", "--config-setting", "-C", "--python-platform",
}
UV_RUN_PYTHON_OPTS = {"-m", "--module", "-s", "--script", "--gui-script"}
GIT_VALUE_OPTS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--config-env"}
DANGEROUS_TARGETS = {
    "/", "/*", "~", "~/*", "$home", "${home}", "$env:userprofile", "%userprofile%", "*", ".", "..", ":/",
}
DRIVE_ROOT = re.compile(r"^(?:[a-z]:/?|/[a-z]/?)\*?$", re.IGNORECASE)
DOWNLOAD_EXEC = [
    re.compile(
        r"(?i)\b(curl|wget|iwr|irm|invoke-webrequest|invoke-restmethod)\b[^\n]*?\|\s*(?:sudo\s+(?:-\S+\s+)*|env\s+)*"
        r"(sh|bash|zsh|dash|iex|invoke-expression|pwsh|powershell|python3?)\b"
    ),
    re.compile(r"(?i)\b(iex|invoke-expression)\b[\s(]*\(?\s*(irm|iwr|invoke-webrequest|invoke-restmethod|new-object)\b"),
    re.compile(r"<\(\s*(curl|wget)\b"),
]
HEREDOC = re.compile(r"<<-?\s*\\?(['\"]?)([A-Za-z_]\w*)\1[^\n]*\n.*?\n\s*\2[ \t]*(?=\n|$)", re.DOTALL)
HERESTRING = re.compile(r"@(['\"])\r?\n.*?\r?\n\1@", re.DOTALL)
EXTERNAL_TOOLS = re.compile(r"^(WebFetch|WebSearch|Artifact|ArtifactComments|mcp__.+)$")
REPO_API_PATH = re.compile(r"^/?repos/[^/]+/[^/]+/?$")


class Blocked(Exception):
    def __init__(self, message: str, private: bool = False) -> None:
        super().__init__(message)
        self.private = private


# --------------------------------------------------------------------------- #
# Secrets and private details
# --------------------------------------------------------------------------- #
def private_patterns_path() -> Path:
    return Path(os.environ.get("WHOLAGGED_PRIVATE_PATTERNS") or Path.home() / ".claude" / "private-patterns.txt")


def private_patterns() -> list[str]:
    try:
        lines = private_patterns_path().read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    return [s for line in lines if (s := line.strip()) and not s.startswith("#")]


def _squash(text: str) -> str:
    """Case-fold and drop spaces and punctuation, so "+374 (41) 17-68" matches "3744117 68"."""
    return re.sub(r"[\W_]+", "", text.casefold())


def contains_private(text: str) -> bool:
    lowered = text.casefold()
    squashed_lines: list[str] | None = None
    for literal in private_patterns():
        if literal.casefold() in lowered:
            return True
        squashed = _squash(literal)
        if len(squashed) >= 6:
            # Line by line, so digits from neighbouring lines are never glued into a false match.
            if squashed_lines is None:
                squashed_lines = [_squash(line) for line in text.splitlines()]
            if any(squashed in line for line in squashed_lines):
                return True
    return False


def scan_text(text: str, where: str) -> None:
    """Raise Blocked if `text` holds a secret or one of the owner's private details."""
    for pattern, name in SECRET_PATTERNS:
        if pattern.search(text):
            raise Blocked(f"{where} contains what looks like a {name}. Never commit or send secrets.")
    if contains_private(text):
        raise Blocked(
            f"{where} contains one of the owner's private details (listed in ~/.claude/private-patterns.txt). "
            "Business and personal data must never reach the public repo or an external service.",
            private=True,
        )


def git(*args: str) -> tuple[int, str]:
    proc = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False
    )
    return proc.returncode, proc.stdout


def allowed_documents() -> set[str]:
    try:
        lines = ALLOWED_DOCUMENTS.read_text(encoding="utf-8").splitlines()
    except OSError:
        return set()
    return {s.replace("\\", "/") for line in lines if (s := line.strip()) and not s.startswith("#")}


def check_file_names(names: list[str], where: str) -> None:
    allowed = allowed_documents()
    for name in names:
        name = name.strip().replace("\\", "/")
        if not name:
            continue
        if SECRET_FILE_RE.search(name):
            raise Blocked(f"{where}: `{name}` looks like a secrets file and must not be committed. Add it to .gitignore.")
        if DOCUMENT_RE.search(name) and name not in allowed:
            raise Blocked(
                f"{where}: `{name}` is a document or spreadsheet. These often hold private data, so they are not "
                "committed by default. If it is public by design, add its path to .claude/hooks/allowed-documents.txt."
            )


def scan_pending_commit() -> None:
    """Scan everything a commit from this tree could record: staged, unstaged and untracked files."""
    names = set(git("diff", "--cached", "--name-only", "--diff-filter=AR")[1].splitlines())
    untracked = git("ls-files", "--others", "--exclude-standard")[1].splitlines()
    names |= set(untracked)
    secret_names = set(git("diff", "--cached", "--name-only")[1].splitlines()) | set(
        git("diff", "--name-only")[1].splitlines()
    )
    check_file_names(sorted(names), "The pending commit")
    for name in sorted(secret_names):
        if SECRET_FILE_RE.search(name.replace("\\", "/")):
            raise Blocked(f"`{name}` looks like a secrets file and must not be committed.")
    added = [
        line[1:]
        for diff in (git("diff", "--cached", "-U0")[1], git("diff", "-U0")[1])
        for line in diff.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    ]
    scan_text("\n".join(added), "The pending commit")
    for name in untracked:
        path = ROOT / name
        try:
            if path.stat().st_size > 2_000_000:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        scan_text(text, f"Untracked file `{name}`")


def scan_push() -> None:
    """Scan the commits a push would publish, however they were made (IDE, terminal, a failed-open hook)."""
    for rng in ("@{u}..HEAD", "origin/main..HEAD"):
        code, _ = git("rev-list", "--count", rng)
        if code == 0:
            break
    else:
        return  # nothing to compare against (no upstream yet)
    _, added = git("log", "--diff-filter=AR", "--name-only", "--format=", rng)
    check_file_names(added.splitlines(), "The commits being pushed")
    _, log = git("log", "-p", "-U0", "--format=%an <%ae>%n%B", rng)
    # Removed lines ("-") were published before; only new content and the messages matter here.
    scan_text("\n".join(line for line in log.splitlines() if not line.startswith("-")), "The commits being pushed")


# --------------------------------------------------------------------------- #
# Parsing shell commands
# --------------------------------------------------------------------------- #
def quote_mask(command: str, powershell: bool) -> list[bool]:
    """True for every character that is quoted or escaped (the quote marks included)."""
    escape = "`" if powershell else "\\"
    mask = [False] * len(command)
    quote: str | None = None
    i = 0
    while i < len(command):
        c = command[i]
        if quote:
            mask[i] = True
            if c == escape and quote == '"' and i + 1 < len(command):
                mask[i + 1] = True
                i += 2
                continue
            if c == quote:
                quote = None
        elif c in "'\"":
            quote = c
            mask[i] = True
        elif c == escape and i + 1 < len(command):
            mask[i] = mask[i + 1] = True
            i += 2
            continue
        i += 1
    return mask


def split_commands(command: str, powershell: bool = False) -> list[str]:
    """Split a command line into simple commands at unquoted operators."""
    operators = ("&&", "||", "|&", "$(", ";", "|", "&", "\n", "(", ")") + (() if powershell else ("`",))
    mask = quote_mask(command, powershell)
    parts: list[str] = []
    start = i = 0
    while i < len(command):
        op = None if mask[i] else next((o for o in operators if command.startswith(o, i)), None)
        if op:
            parts.append(command[start:i])
            i += len(op)
            start = i
        else:
            i += 1
    parts.append(command[start:])
    return [p.strip() for p in parts if p.strip()]


def blank_quotes(command: str, powershell: bool) -> str:
    mask = quote_mask(command, powershell)
    return "".join(" " if m and c not in "'\"" else c for c, m in zip(command, mask))


def tokens_of(segment: str, powershell: bool = False) -> list[str]:
    posix = not powershell and "\\" not in segment  # Windows paths would lose their backslashes
    try:
        return [t if posix else t.strip("'\"") for t in shlex.split(segment, posix=posix)]
    except ValueError:
        return segment.split()


def strip_wrappers(tokens: list[str]) -> list[str]:
    while tokens:
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", tokens[0]):
            tokens = tokens[1:]
        elif program(tokens[0]) in WRAPPERS:
            tokens = tokens[1:]
            while tokens and tokens[0].startswith("-"):
                tokens = tokens[1:]
        else:
            break
    return tokens


def program(token: str) -> str:
    return re.split(r"[\\/]", token)[-1].lower().removesuffix(".exe")


def short_flags(tokens: list[str]) -> set[str]:
    return {ch for t in tokens if re.match(r"^-[A-Za-z]+$", t) for ch in t[1:]}


def after_uv_run(args: list[str]) -> list[str]:
    """The command `uv run [options] <command>` runs; [] when it runs Python itself."""
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            return args[i + 1 :]
        if not a.startswith("-"):
            return args[i:]
        if a in UV_RUN_PYTHON_OPTS:
            return []
        i += 2 if a in UV_RUN_VALUE_OPTS else 1
    return []


def nested_command(name: str, args: list[str]) -> tuple[str, bool] | None:
    """The command string a shell runs: `bash -c "..."`, `pwsh -Command ...`, `cmd /c ...`."""
    lowered = [a.lower() for a in args]
    if name in POSIX_SHELLS and "-c" in lowered:
        i = lowered.index("-c")
        return (args[i + 1] if i + 1 < len(args) else ""), False
    if name in POWERSHELLS:
        for flag in ("-command", "-c"):
            if flag in lowered:
                return " ".join(args[lowered.index(flag) + 1 :]), True
    if name == "cmd":
        for flag in ("/c", "/k"):
            if flag in lowered:
                return " ".join(args[lowered.index(flag) + 1 :]), False
    return None


def dangerous_target(target: str) -> bool:
    raw = target.strip("'\"")
    norm = raw.replace("\\", "/").casefold()
    while norm.startswith("./") and len(norm) > 2:
        norm = norm[2:]
    if len(norm) > 1:
        norm = norm.rstrip("/") or "/"
    if norm in DANGEROUS_TARGETS or DRIVE_ROOT.match(norm) or PurePosixPath(norm).name == ".git":
        return True
    try:
        path = Path(os.path.expandvars(raw)).expanduser().resolve()
    except (OSError, RuntimeError, ValueError):
        return False
    return path in (ROOT, ROOT / ".git", Path.home().resolve(), Path(path.anchor))


# --------------------------------------------------------------------------- #
# Rules
# --------------------------------------------------------------------------- #
def check_git(args: list[str]) -> None:
    i = 0
    while i < len(args) and args[i].startswith("-"):
        opt = args[i]
        value = args[i + 1] if opt in GIT_VALUE_OPTS and i + 1 < len(args) else ""
        if (opt == "-c" and value.lower().startswith("core.hookspath")) or opt.lower().startswith("-ccore.hookspath"):
            raise Blocked("Overriding core.hooksPath skips git hooks. That is not allowed.")
        i += 2 if opt in GIT_VALUE_OPTS else 1
    if i >= len(args):
        return
    sub, rest = args[i], args[i + 1 :]
    flags = short_flags(rest)
    targets = [a for a in rest if not a.startswith("-")]
    wildcard = any(t.replace("\\", "/").rstrip("/") in ("", ".", ":", ":/", "*", ":/*") for t in targets)
    if sub == "push":
        if (
            any(a in ("--force", "--mirror", "--delete", "--prune") or a.startswith("--force-with-lease") for a in rest)
            or flags & {"f", "d"}
            or any(a.startswith(("+", ":")) for a in rest)
        ):
            raise Blocked("Force, mirror and delete pushes are not allowed. Push normally; if rejected, rebase first.")
        if "--no-verify" in rest:
            raise Blocked("Skipping git hooks (--no-verify) is not allowed.")
        scan_push()
    elif sub == "commit":
        if "--no-verify" in rest or "--no-gpg-sign" in rest or "n" in flags:
            raise Blocked("Skipping git hooks or signing (--no-verify / -n / --no-gpg-sign) is not allowed.")
        scan_pending_commit()
    elif sub == "add" and ("--force" in rest or "f" in flags):
        check_file_names(targets, "git add --force")
    elif sub == "reset" and "--hard" in rest:
        raise Blocked("`git reset --hard` destroys work. Use `git stash`, `git restore <file>` or `git revert`.")
    elif sub == "clean" and not ("n" in flags or "--dry-run" in rest):
        raise Blocked("`git clean` deletes untracked work for good. Use the cleanup skill (or `git clean -n` to look).")
    elif sub == "checkout" and wildcard:
        raise Blocked("`git checkout .` throws away all local changes. Restore single files by name.")
    elif sub == "restore" and wildcard and ("--staged" not in rest or "--worktree" in rest or "W" in flags):
        raise Blocked("`git restore .` throws away all local changes. Restore single files by name.")
    elif sub == "stash" and targets[:1] in (["drop"], ["clear"]):
        raise Blocked("Dropping stashes loses work. Leave the stash; it costs nothing.")
    elif sub == "branch" and ("D" in flags or ("--delete" in rest and "--force" in rest)):
        raise Blocked("Force-deleting a branch can lose unmerged work. Use `git branch -d` (merged only).")
    elif sub in ("filter-branch", "filter-repo"):
        raise Blocked("Rewriting history is not allowed.")


def check_gh(args: list[str]) -> None:
    if args[:2] in (["repo", "delete"], ["repo", "archive"]):
        raise Blocked("Deleting or archiving the repository is not allowed.")
    if args[:2] == ["repo", "edit"] and any(a.startswith("--visibility") for a in args):
        raise Blocked("Changing the repository visibility is not allowed.")
    if args[:1] == ["api"]:
        method = "GET"
        for i, a in enumerate(args):
            if a in ("-X", "--method") and i + 1 < len(args):
                method = args[i + 1].upper()
            elif a.startswith("--method="):
                method = a.split("=", 1)[1].upper()
        if any(REPO_API_PATH.match(a) for a in args):
            if method == "DELETE":
                raise Blocked("Deleting the repository is not allowed.")
            if method in ("PATCH", "PUT", "POST") and any(
                re.match(r"(?i)^(private|visibility|archived)=", a) for a in args
            ):
                raise Blocked("Changing the repository visibility or archiving it is not allowed.")


def check_delete(name: str, args: list[str]) -> None:
    if name in ("rd", "rmdir", "del", "erase"):
        switches = {a.lower() for a in args if re.match(r"^/[a-z]$", a, re.IGNORECASE)}
        recursive = "/s" in switches or "r" in short_flags(args) or any(a.lower().startswith("-recurse") for a in args)
        targets = [a for a in args if a.lower() not in switches and not a.startswith("-")]
    else:  # rm (POSIX), Remove-Item / ri / rm alias (PowerShell)
        flags = short_flags(args)
        recursive = bool(flags & {"r", "R"}) or any(a.lower() in ("--recursive",) or a.lower().startswith("-recurse")
                                                     for a in args)
        targets = [a for a in args if not a.startswith("-")]
    if recursive and any(dangerous_target(t) for t in targets):
        raise Blocked("Recursive delete of a root, the home folder, the repo or `.git` is not allowed. "
                      "Name the exact paths to delete.")


def check_tokens(tokens: list[str], powershell: bool, depth: int) -> None:
    tokens = strip_wrappers(tokens)
    if not tokens:
        return
    name, args = program(tokens[0]), tokens[1:]
    if PY_TOOLS.match(name):
        raise Blocked(f"`{name}` is not used here: uv is mandatory (uv add / uv remove / uv sync / uvx).")
    if PY_INTERPRETERS.match(name):
        raise Blocked(
            "Bare `python` is not used here: run `uv run python ...` (project code) "
            "or `uv run --no-project python ...` (stand-alone scripts)."
        )
    if name == "uv":
        if args[:1] == ["pip"] and args[1:2] and args[1] in ("install", "uninstall", "sync"):
            raise Blocked("`uv pip install` bypasses uv.lock. Use `uv add` / `uv remove` / `uv sync`.")
        if args[:1] == ["run"]:
            inner = after_uv_run(args[1:])
            if inner and not PY_INTERPRETERS.match(program(inner[0])):
                check_tokens(inner, powershell, depth + 1)
        return
    nested = nested_command(name, args)
    if nested is not None:
        check_command(nested[0], powershell=nested[1], depth=depth + 1)
    elif name == "git":
        check_git(args)
    elif name == "gh":
        check_gh(args)
    elif name in ("rm", "remove-item", "ri", "del", "rd", "rmdir", "erase"):
        check_delete(name, args)


def check_command(command: str, powershell: bool = False, depth: int = 0) -> None:
    if depth > MAX_DEPTH:
        return
    scan_text(command, "The command")
    body = HERESTRING.sub("''", HEREDOC.sub("", command))
    plain = blank_quotes(body, powershell)
    for pattern in DOWNLOAD_EXEC:
        if pattern.search(plain):
            raise Blocked("Never run a download directly. Download it, read it, then decide.")
    for segment in split_commands(body, powershell):
        check_tokens(tokens_of(segment, powershell), powershell, depth)


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def inside_repo(path: str) -> bool:
    try:
        Path(path).resolve().relative_to(ROOT)
    except ValueError:
        return False
    return True


def check_write(tool_input: dict) -> None:
    path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    if not path or not inside_repo(path):
        return  # e.g. the private memory directory, the scratchpad
    pieces = [tool_input.get("content"), tool_input.get("new_string"), tool_input.get("new_source")]
    pieces += [e.get("new_string") for e in tool_input.get("edits") or [] if isinstance(e, dict)]
    scan_text("\n".join(p for p in pieces if isinstance(p, str)), f"The text for `{Path(path).name}`")


def decide(event: dict) -> None:
    tool = event.get("tool_name", "")
    tool_input = event.get("tool_input") or {}
    if tool in ("Bash", "PowerShell"):
        check_command(tool_input.get("command") or "", powershell=tool == "PowerShell")
    elif tool in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        check_write(tool_input)
    elif EXTERNAL_TOOLS.match(tool):
        scan_text(json.dumps(tool_input, ensure_ascii=False), f"The input for {tool}")
        path = tool_input.get("file_path")
        if tool == "Artifact" and isinstance(path, str):  # the page being published is a local file
            try:
                scan_text(Path(path).read_text(encoding="utf-8", errors="replace")[:5_000_000], f"`{Path(path).name}`")
            except OSError:
                pass


def main() -> int:
    try:
        event = json.loads(sys.stdin.buffer.read().decode("utf-8") or "{}")
        decide(event)
    except Blocked as exc:
        if exc.private and EXTERNAL_TOOLS.match(str(event.get("tool_name", ""))):
            # Only the user may approve sending their details to an outside service.
            decision = {"hookEventName": "PreToolUse", "permissionDecision": "ask",
                        "permissionDecisionReason": f"guard.py: {exc}"}
            print(json.dumps({"hookSpecificOutput": decision}))
            return 0
        print(f"Blocked by .claude/hooks/guard.py: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 - fail open, see the module docstring
        print(f"guard.py warning (call allowed): {type(exc).__name__}: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
