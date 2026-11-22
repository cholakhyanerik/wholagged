"""Translations: `t(key, **params)` looks a text up in the current language's catalogue.

The catalogues are plain Python modules, one per language, in `wholagged/locales/` (`MESSAGES` dicts). Only
the catalogues that are needed get imported, once. Lookup order: the current language, then English, then
the key itself, so a missing text shows up as its key instead of crashing the UI.

Texts use `str.format` syntax: `t("relay.ping", ms=42)` fills `{ms}`. Write a literal brace as `{{` / `}}`.
A field without a value stays visible as written (`{name}`, `{pops[0]}`, `{ms:.0f}`; an empty spec such as
`{ms:}` comes back as `{ms}`). A template that can't be filled is shown raw, with its `{{` escapes.
"""

from __future__ import annotations

import re
import string
from collections.abc import Mapping

LANGUAGES = ("hy", "ru", "en")  # the app's languages (CLAUDE.md rule 14)
DEFAULT_LANGUAGE = "hy"  # the UI has been Armenian so far; WL-30 picks the language from the OS
FALLBACK_LANGUAGE = "en"

_language = DEFAULT_LANGUAGE
_catalogues: dict[str, Mapping[str, str]] = {}
_FORMATTER = string.Formatter()
_FIELD_ROOT = re.compile(r"[.\[]")  # `pops[0]` and `pop.name` both belong to the parameter before it
# Errors a template or an ordinary value (str, int, float, None) can raise while being formatted.
_FORMAT_ERRORS = (ValueError, LookupError, AttributeError, TypeError, ArithmeticError)


def get_language() -> str:
    return _language


def set_language(lang: str) -> None:
    """Switch the language. Raises ValueError for anything but one of LANGUAGES (case doesn't matter)."""
    global _language
    code = lang.strip().lower() if isinstance(lang, str) else ""
    if code not in LANGUAGES:
        raise ValueError(f"unknown language {lang!r}; use one of: {', '.join(LANGUAGES)}")
    _language = code


def _load(lang: str) -> Mapping[str, str]:
    # Plain imports, not importlib with a computed name, so freezers (PyInstaller, Nuitka: WL-80/81) see and
    # bundle every catalogue. Still lazy: only the branch that runs imports its module.
    match lang:
        case "hy":
            from .locales import hy as module
        case "ru":
            from .locales import ru as module
        case _:
            from .locales import en as module
    return module.MESSAGES


def _catalogue(lang: str) -> Mapping[str, str]:
    cat = _catalogues.get(lang)
    if cat is None:
        cat = _catalogues[lang] = _load(lang)
    return cat


def _has_value(field: str, params: Mapping[str, object]) -> bool:
    return _FIELD_ROOT.split(field, maxsplit=1)[0] in params


def _render(text: str, params: Mapping[str, object]) -> str:
    """Fill the fields whose parameters are given; leave any other field as written."""
    out: list[str] = []
    for literal, field, spec, conversion in _FORMATTER.parse(text):
        out.append(literal)
        if field is None:
            continue
        nested = [f for _, f, _, _ in _FORMATTER.parse(spec)] if spec and "{" in spec else []
        if not _has_value(field, params) or not all(f is None or _has_value(f, params) for f in nested):
            out.append("{" + field + (f"!{conversion}" if conversion else "") + (f":{spec}" if spec else "") + "}")
            continue
        value, _ = _FORMATTER.get_field(field, (), params)
        spec = _render(spec, params) if nested else spec or ""  # a nested `{ms:{width}}` spec
        out.append(_FORMATTER.format_field(_FORMATTER.convert_field(value, conversion), spec))
    return "".join(out)


def t(key: str, /, **params: object) -> str:
    """The text for `key` in the current language, with `{placeholders}` filled from `params`."""
    lang = _language  # read once: another thread may switch the language meanwhile
    text = _catalogue(lang).get(key)
    if not text and lang != FALLBACK_LANGUAGE:  # missing or left empty: use English
        text = _catalogue(FALLBACK_LANGUAGE).get(key)
    if not text:
        return key
    try:
        return _render(text, params)
    except _FORMAT_ERRORS:
        return text  # a malformed template, or a value that doesn't fit its field: show the raw text
