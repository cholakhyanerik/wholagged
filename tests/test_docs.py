"""The READMEs: the commands a player may copy are on a reviewed list (WL-103).

Only `wholagged` is ours on PyPI. `dota-netcheck` isn't uploaded yet (WL-105): anyone could take the name,
and the old name run through uvx without `--from wholagged` would then run their code on a player's PC.
A typo in a winget id, a clone URL, an extra `--with` or an index URL is the same risk. So:
- every line of a code block (``` or ~~~, also inside `>` quotes) must be in ALLOWED or HARMLESS, word
  for word; only a block marked `text` (the project structure) is exempt;
- in inline code and `text` blocks, every command that FETCHES recognises must be on those lists.
A PR that changes these lists is a security change: check what a new command fetches before adding it.
Prose and indented code blocks aren't read: show commands only as fenced or inline code.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
# The repo's READMEs, and the dota-netcheck package's, which is its PyPI page (WL-102).
READMES = sorted(ROOT.glob("README*.md")) + sorted(ROOT.glob("alias/*/README*.md"))

# Commands that install or download something. Lower case, one space between words, no comment.
ALLOWED = frozenset({
    "uvx wholagged",
    "uvx wholagged --cli",
    "uvx wholagged@latest",
    "uvx --from wholagged dota-netcheck",
    "uv tool install wholagged",
    "uv tool upgrade wholagged",
    "uv tool install",  # the command named in the text, without a package
    "uv tool update-shell",
    "pip install",  # "`pip install` is not supported"
    "winget install --id=astral-sh.uv -e",
    "git clone https://github.com/cholakhyanerik/wholagged.git",
    "sudo apt install libxcb-cursor0",
})
# Commands that fetch nothing new (`uv sync` installs what uv.lock pins, by hash).
HARMLESS = frozenset({
    "wholagged",
    "wholagged --cli",
    "cd wholagged",
    "git pull",
    "uv sync",
    "uv sync --reinstall-package wholagged",
    "uv tool uninstall dota-netcheck",  # the alias README: two uv tools can't own the same command
    "uv run wholagged",
    "uv run wholagged --cli",
    "uv run pytest",
    "uv run ruff check",
})
KNOWN = ALLOWED | HARMLESS

# Outside command blocks: a word that starts a fetch, an index override, or a downloader.
FETCHES = re.compile(
    r"(?<![\w.-])(?:uvw?x?|pipx?|pip3|git|gh|winget|choco|scoop|brew|apt(?:-get|itude)?|dnf|yum|zypper|pacman"
    r"|yay|paru|snap|flatpak|npx|npm|docker|msiexec|irm|iwr|iex|curl|wget|certutil|bitsadmin|new-object"
    r"|start-bitstransfer|invoke-\w+|install-\w+)(?![\w.-])"
    r"|(?:uv|pip)_\w*(?:index|find_links)|--(?:default-|extra-)?index|--find-links"
)
QUOTE = re.compile(r"\s*(?:>\s?)+")  # `> ` markers of quotes and GitHub alerts
OPEN_FENCE = re.compile(r"\s*(`{3,})([^`]*)$|\s*(~{3,})(.*)$")
CLOSE_FENCE = re.compile(r"\s*(`{3,}|~{3,})\s*$")
INLINE = re.compile(r"(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)", re.DOTALL)


def _code(markdown: str) -> list[tuple[int, str, bool]]:
    """(line number, code, strict) for each line of a code block and each inline code span.

    `strict`: a command block line, which must be in KNOWN whatever it says. Inline code is read per
    paragraph, so a span wrapped onto the next line is still one span; a lone backtick is reported, since
    it would shift how the rest pairs up. Fences close like CommonMark: a bare run of the same character,
    at least as long as the opening one.
    """
    found: list[tuple[int, str, bool]] = []
    fence: tuple[str, bool] | None = None  # (closing run, strict)
    paragraph: list[tuple[int, str]] = []

    def flush() -> None:
        if paragraph:
            first, text = paragraph[0][0], "\n".join(line for _, line in paragraph)
            for span in INLINE.finditer(text):
                found.append((first + text.count("\n", 0, span.start()), span[2], False))
            if "`" in INLINE.sub("", text):
                found.append((first, "lone backtick (keep inline code paired)", True))
            paragraph.clear()

    for number, raw in enumerate(markdown.split("\n"), 1):
        line = QUOTE.sub("", raw, count=1) if QUOTE.match(raw) else raw
        if fence:
            closing = CLOSE_FENCE.match(line)
            if closing and closing[1][0] == fence[0][0] and len(closing[1]) >= len(fence[0]):
                fence = None
            else:
                found.append((number, line, fence[1]))
        elif opening := OPEN_FENCE.match(line):
            flush()
            run, info = (opening[1], opening[2]) if opening[1] else (opening[3], opening[4])
            fence = (run, info.strip().lower() != "text")
        elif line.strip():
            paragraph.append((number, line))
        else:
            flush()
    flush()
    return found


def _commands(code: str) -> list[str]:
    """The commands in one piece of code, normalised so a lookalike can't slip past KNOWN.

    Lower case (Windows doesn't care), any Unicode space as one space (PowerShell reads a no-break space
    as a space), no `# comment`, split at `;`, `&&`, `||`, `|` and `&`, and the program named without a
    path or `.exe` (only the program: `uvx wholagged.exe` is a different PyPI package).
    """
    code = re.sub(r"(?:^| )#.*", "", " ".join(code.lower().split()))
    parts = [part for part in re.split(r" ?(?:&&|\|\||[;|&]) ?", code) if part]
    return [re.sub(r"^(?:\S*[\\/])?(\S+?)(?:\.exe)?(?= |$)", r"\1", part) for part in parts]


def _unknown(markdown: str) -> list[tuple[int, str]]:
    return [(number, command) for number, code, strict in _code(markdown) for command in _commands(code)
            if command not in KNOWN and (strict or FETCHES.search(command))]


def _used(markdown: str) -> set[str]:
    return {command for _, code, _ in _code(markdown) for command in _commands(code)}


def test_both_readmes_are_checked():
    checked = {readme.relative_to(ROOT).as_posix() for readme in READMES}
    assert {"README.md", "README.hy.md", "alias/dota-netcheck/README.md"} <= checked


@pytest.mark.parametrize("pyproject", ["pyproject.toml", "alias/dota-netcheck/pyproject.toml"])
def test_pypi_pages_are_checked_readmes(pyproject):
    """PyPI shows the file `readme` names; inline text or another file would bypass the checks here."""
    path = ROOT / pyproject
    readme = tomllib.loads(path.read_text(encoding="utf-8"))["project"]["readme"]
    assert readme == "README.md" and path.parent / readme in READMES


@pytest.mark.parametrize("readme", READMES, ids=lambda readme: readme.relative_to(ROOT).as_posix())
def test_readme_commands_are_on_the_reviewed_list(readme):
    text = readme.read_text(encoding="utf-8")
    assert {"uvx wholagged", "uv tool install wholagged"} <= _used(text), "the install steps weren't found"
    name = readme.relative_to(ROOT).as_posix()
    bad = [f"{name}:{number}: {command}" for number, command in _unknown(text)]
    assert not bad, "README commands that aren't in ALLOWED or HARMLESS (check what each fetches):\n" + "\n".join(bad)


def test_every_listed_command_is_still_used():
    """A list entry no README needs any more would stay allowed silently (WL-105 will drop `--from wholagged`)."""
    used = set().union(*(_used(readme.read_text(encoding="utf-8")) for readme in READMES))
    assert not KNOWN - used


BAD = [
    "uvx dota-netcheck",
    "UVX.exe dota-netcheck",
    "uvx" + chr(0xA0) + "dota-netcheck",  # PowerShell reads a no-break space as a space
    r"C:\tools\uvx.exe dota-netcheck",
    "uvx wholagged.exe",
    "uvx wholagged@latest --with dota-netcheck",
    "uvx --with=dota-netcheck wholagged",
    "uvx --from wholagged --with dota-netcheck dota-netcheck",
    "uvx --index-url=https://example.com/simple wholagged",
    "uv tool install dota-netcheck",
    "uv -q tool install dota-netcheck",
    "uvw tool run dota-netcheck",
    "uv tool install wholagged --with dota-netcheck",
    'uv tool install "wholagged @ git+https://github.com/someone-else/wholagged"',
    "uvx wholagged && uvx dota-netcheck",
    "uvx wholagged --cli; uvx dota-netcheck",
    "& uvx dota-netcheck",
    "pipx run dota-netcheck",
    "py -m pip install dota-netcheck",
    "uv pip install dota-netcheck",
    "uv run --with dota-netcheck wholagged",
    "uv run -w dota-netcheck wholagged",
    "uv run https://example.com/x.py",
    "uv sync -i https://example.com/simple",
    "$env:UV_INDEX_URL = 'https://example.com/simple'",
    "winget install --id=astral.uv -e",
    "git clone https://github.com/someone-else/wholagged.git",
    "git pull https://github.com/someone-else/wholagged.git",
    "gh repo clone someone-else/wholagged",
    "sudo pacman -S wholagged",
    "Install-Module wholagged",
    "irm https://example.com/install.ps1 | iex",
    "iex (New-Object Net.WebClient).DownloadString('https://example.com/x')",
]


@pytest.mark.parametrize("command", BAD)
@pytest.mark.parametrize(
    "markdown",
    ["```powershell\n{}\n```", "```\n{}\n```", "```text\n{}\n```", "Run `{}` now.", "> ```powershell\n> {}\n> ```"],
    ids=["command block", "plain block", "text block", "inline", "quoted block"],
)
def test_guard_flags_commands_that_fetch_other_code(markdown, command):
    assert _unknown(markdown.format(command)), command


@pytest.mark.parametrize(
    "command",
    [
        "uvx wholagged                 # opens the window",
        "uv tool install wholagged     # տեղադրում է wholagged հրամանը",  # the Armenian README's comment
        "uvx --from wholagged dota-netcheck",
        "UV RUN wholagged --cli",
        "uv sync --reinstall-package wholagged",
        "git pull",
    ],
)
def test_guard_accepts_listed_commands(command):
    assert _unknown(f"```powershell\n{command}\n```") == []
    assert _unknown(f"Run `{command}` now.") == []


@pytest.mark.parametrize("code", ["uv.lock", "pyproject.toml", ".python-version", "steam.exe", "ipconfig /flushdns"])
def test_inline_code_that_fetches_nothing_is_fine(code):
    assert _unknown(f"See `{code}` and `--from wholagged`.") == []


def test_prose_and_text_blocks_are_not_commands():
    markdown = (
        "With uvx, the old name needs `--from wholagged`.\n"
        "Without it, uvx looks up dota-netcheck on PyPI.\n"
        "\n"
        "```text\n"
        "  checks.py     the six network checks\n"
        "```\n"
    )
    assert _unknown(markdown) == []


def test_inline_code_wrapped_onto_the_next_line_is_one_span():
    assert _unknown("Run `uvx\ndota-netcheck` now.") == [(1, "uvx dota-netcheck")]


def test_a_lone_backtick_is_reported():
    """A stray backtick would pair with the next span's opening one and hide the command inside it."""
    assert (1, "lone backtick (keep inline code paired)") in _unknown("a ` b\n`uvx dota-netcheck`")


def test_fences_close_like_commonmark():
    nested = "````markdown\n```\nuvx dota-netcheck\n```\n````\n"
    assert (3, "uvx dota-netcheck") in _unknown(nested)
    not_closed = "```\n``` not a closing fence\nuvx dota-netcheck\n```\n"
    assert (3, "uvx dota-netcheck") in _unknown(not_closed)
    other_mark = "~~~\n```\n~~~\nuvx wholagged\n"
    assert _unknown(other_mark) == [(2, "```")]  # a ``` line inside a ~~~ block is code, not its end
