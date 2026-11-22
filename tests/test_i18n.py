"""The i18n core: lookup, language switching, placeholders, fallback order and the catalogues themselves."""

from __future__ import annotations

import importlib
import pkgutil
import re
import string

import pytest

from wholagged import i18n, locales
from wholagged.i18n import t

ARMENIAN = re.compile(r"[Ա-և]")
CYRILLIC = re.compile(r"[Ѐ-ӿ]")


@pytest.fixture(autouse=True)
def _isolated_i18n_state(monkeypatch):
    """The language and the catalogue cache are module globals: each test gets its own, restored afterwards."""
    monkeypatch.setattr(i18n, "_language", i18n.get_language())
    monkeypatch.setattr(i18n, "_catalogues", {})


def _messages(lang: str) -> dict[str, str]:
    return importlib.import_module(f"wholagged.locales.{lang}").MESSAGES


def _use(monkeypatch, lang: str, messages: dict[str, str]) -> None:
    """Replace `lang`'s catalogue with test texts (the real locale files stay untouched) and switch to it."""
    monkeypatch.setitem(i18n._catalogues, lang, messages)
    i18n.set_language(lang)


# --- lookup and language switching ---------------------------------------------------------------


def test_default_language_is_armenian():
    assert i18n.DEFAULT_LANGUAGE == "hy"
    assert i18n.get_language() == "hy"
    text = t("app.subtitle")
    assert text == _messages("hy")["app.subtitle"]
    assert ARMENIAN.search(text)


@pytest.mark.parametrize(
    ("lang", "armenian", "cyrillic"),
    [("ru", False, True), ("en", False, False), ("hy", True, False)],
)
def test_set_language_switches_the_text(lang, armenian, cyrillic):
    i18n.set_language("en" if lang != "en" else "ru")  # start elsewhere, so the switch has to do something
    i18n.set_language(lang)
    assert i18n.get_language() == lang
    text = t("app.subtitle")
    assert text == _messages(lang)["app.subtitle"]
    assert bool(ARMENIAN.search(text)) is armenian
    assert bool(CYRILLIC.search(text)) is cyrillic


@pytest.mark.parametrize(("given", "expected"), [("RU", "ru"), (" en ", "en"), ("Hy", "hy"), ("\tRU\n", "ru")])
def test_set_language_ignores_case_and_surrounding_spaces(given, expected):
    i18n.set_language(given)
    assert i18n.get_language() == expected
    assert t("app.subtitle") == _messages(expected)["app.subtitle"]


@pytest.mark.parametrize("bad", ["de", "", "   ", "hy-AM", "ru_RU", "english", None, 7])
def test_unknown_language_is_refused_and_keeps_the_current_one(bad):
    i18n.set_language("ru")
    with pytest.raises(ValueError, match="unknown language") as info:
        i18n.set_language(bad)
    # Every allowed code is named, and not only because it is part of the rejected value ("hy" in "hy-AM").
    rest = str(info.value).replace(repr(bad), "")
    for code in i18n.LANGUAGES:
        assert re.search(rf"\b{code}\b", rest), f"{code!r} missing from {info.value}"
    assert i18n.get_language() == "ru"
    assert t("app.subtitle") == _messages("ru")["app.subtitle"]


def test_only_the_needed_catalogues_are_loaded():
    i18n.set_language("ru")
    t("app.subtitle")
    assert set(i18n._catalogues) == {"ru"}  # found in Russian: English is not even imported
    t("no.such.key")
    assert set(i18n._catalogues) == {"ru", "en"}  # the fallback is loaded on the first miss
    assert i18n._catalogues["ru"] is _messages("ru")  # cached as is, no copy


# --- placeholders --------------------------------------------------------------------------------


def test_placeholder_is_filled(monkeypatch):
    _use(monkeypatch, "en", {"relay.ping": "{pop}: {ms} ms"})
    assert t("relay.ping", pop="fra", ms=42) == "fra: 42 ms"


def test_format_spec_is_applied_to_a_given_value(monkeypatch):
    _use(monkeypatch, "en", {"relay.ping": "{ms:.0f} ms"})
    assert t("relay.ping", ms=41.6) == "42 ms"


def test_missing_placeholder_stays_visible(monkeypatch):
    _use(monkeypatch, "en", {"relay.ping": "{pop}: {ms} ms"})
    assert t("relay.ping", pop="fra") == "fra: {ms} ms"
    assert t("relay.ping") == "{pop}: {ms} ms"


def test_extra_params_are_ignored(monkeypatch):
    _use(monkeypatch, "en", {"relay.ping": "{ms} ms", "app.title": "wholagged"})
    assert t("relay.ping", ms=7, pop="fra", loss=0.5) == "7 ms"
    assert t("app.title", ms=7) == "wholagged"


def test_double_braces_give_literal_braces(monkeypatch):
    _use(monkeypatch, "en", {"hint.braces": "{{ms}} is {ms}", "hint.literal": "set {{x}}"})
    assert t("hint.braces", ms=5) == "{ms} is 5"
    assert t("hint.literal") == "set {x}"  # unescaped even with no params at all


def test_placeholder_named_key_does_not_clash_with_the_lookup_key(monkeypatch):
    _use(monkeypatch, "en", {"gui.press": "Press {key}"})
    assert t("gui.press", key="Enter") == "Press Enter"


@pytest.mark.parametrize(
    ("template", "expected"),
    [
        ("{pop}: {pops[0]}", "fra: {pops[0]}"),  # indexed
        ("{pop}: {pops[0].code}", "fra: {pops[0].code}"),  # indexed, then attribute
        ("{pop}: {relay.name}", "fra: {relay.name}"),  # attribute
        ("{pop}: {ms!r}", "fra: {ms!r}"),  # conversion
        ("{pop}: {ms!s:>6}", "fra: {ms!s:>6}"),  # conversion and format spec
        ("{pop}: {ms:.0f} ms", "fra: {ms:.0f} ms"),  # format spec
        ("{pop}: {0}", "fra: {0}"),  # positional
        ("{pop}: {}", "fra: {}"),  # auto-numbered
    ],
)
def test_field_without_a_value_stays_exactly_as_written(monkeypatch, template, expected):
    # `pop` is given and filled, so showing the whole raw template would fail: each field is rendered on its own.
    _use(monkeypatch, "en", {"relay.ping": template})
    assert t("relay.ping", pop="fra") == expected


@pytest.mark.parametrize("template", ["{pops[0]}", "{ms!r}", "{pop.name}", "{0} ms", "ping {ms:.0f} ms"])
def test_text_with_no_values_given_is_shown_as_written(monkeypatch, template):
    _use(monkeypatch, "en", {"relay.ping": template})
    assert t("relay.ping") == template


@pytest.mark.parametrize(
    ("template", "params"),
    [
        ("{ms:.0f} ms", {"ms": "fast"}),  # format spec that doesn't fit the value
        ("{pop}: {ms:.0f} ms", {"pop": "fra", "ms": "x"}),  # the fitting `pop` is not filled in either
        ("{pop}: {pops[5]}", {"pop": "fra", "pops": ["sto"]}),  # index past the end
        ("{pop}: {pops[x]}", {"pop": "fra", "pops": {}}),  # key the mapping doesn't have
        ("{pop}: {relay.name}", {"pop": "fra", "relay": "sto"}),  # attribute the value doesn't have
        ("{pop}: {ms:.0f} ms", {"pop": "fra", "ms": 10**400}),  # OverflowError: int too large for a float
        ("{ms:c}", {"ms": 2**40}),  # OverflowError: not a code point
    ],
)
def test_value_that_does_not_fit_its_field_returns_the_raw_template(monkeypatch, template, params):
    _use(monkeypatch, "en", {"relay.ping": template})
    assert t("relay.ping", **params) == template


@pytest.mark.parametrize(
    ("template", "params"),
    [
        ("ping {ms", {}),  # unbalanced brace
        ("ping ms}", {}),  # lone closing brace
        ("ping {ms", {"ms": 5}),  # unbalanced brace, value given
        ("{pop}: {ms!z}", {"pop": "fra", "ms": 1}),  # unknown conversion
    ],
)
def test_broken_template_returns_the_raw_text_instead_of_raising(monkeypatch, template, params):
    _use(monkeypatch, "en", {"relay.ping": template})
    assert t("relay.ping", **params) == template


# --- fallback order: current language -> en -> the key ------------------------------------------


@pytest.mark.parametrize("lang", ["ru", "hy"])
def test_key_only_in_english_shows_the_english_text(monkeypatch, lang):
    monkeypatch.setitem(i18n._catalogues, "en", {"check.new": "New check: {ms} ms"})
    _use(monkeypatch, lang, {"app.subtitle": "local"})
    assert t("check.new", ms=3) == "New check: 3 ms"  # placeholders are filled in the fallback text too
    assert t("app.subtitle") == "local"


@pytest.mark.parametrize("lang", ["ru", "hy"])
def test_current_language_wins_over_english(monkeypatch, lang):
    monkeypatch.setitem(i18n._catalogues, "en", {"check.dns": "English"})
    _use(monkeypatch, lang, {"check.dns": "local {ms}"})
    assert t("check.dns", ms=1) == "local 1"


@pytest.mark.parametrize("lang", ["ru", "hy"])
def test_empty_translation_falls_back_to_english(monkeypatch, lang):
    monkeypatch.setitem(i18n._catalogues, "en", {"check.new": "New check: {ms} ms"})
    _use(monkeypatch, lang, {"check.new": ""})
    assert t("check.new", ms=3) == "New check: 3 ms"


@pytest.mark.parametrize("lang", ["en", "ru"])
def test_empty_english_text_falls_back_to_the_key(monkeypatch, lang):
    monkeypatch.setitem(i18n._catalogues, "en", {"check.new": ""})
    _use(monkeypatch, lang, {"check.new": ""})  # for "en" this is the same empty English text
    assert t("check.new", ms=3) == "check.new"


@pytest.mark.parametrize("lang", i18n.LANGUAGES)
def test_unknown_key_returns_the_key(lang):
    i18n.set_language(lang)
    assert t("no.such.key") == "no.such.key"
    assert t("no.such.key", ms=1) == "no.such.key"


def test_key_missing_everywhere_returns_the_key_even_if_it_looks_like_a_template(monkeypatch):
    monkeypatch.setitem(i18n._catalogues, "en", {})
    _use(monkeypatch, "ru", {})
    assert t("{ms} ms", ms=5) == "{ms} ms"  # the key is never formatted


# --- the catalogues ------------------------------------------------------------------------------


def test_every_catalogue_module_is_a_known_language():
    modules = {m.name for m in pkgutil.iter_modules(locales.__path__)}
    assert modules == set(i18n.LANGUAGES)
    assert i18n.FALLBACK_LANGUAGE in i18n.LANGUAGES
    assert i18n.DEFAULT_LANGUAGE in i18n.LANGUAGES


@pytest.mark.parametrize("lang", i18n.LANGUAGES)
def test_catalogue_imports_and_maps_strings_to_strings(lang):
    messages = _messages(lang)
    assert type(messages) is dict
    assert messages
    for key, text in messages.items():
        assert type(key) is str and key, key
        assert type(text) is str and text, key


def _placeholders(text: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(text) if name is not None}


@pytest.mark.parametrize("lang", ["ru", "en"])
def test_translations_use_the_same_placeholders_as_armenian(lang):
    # locales/__init__.py: placeholders must be the same in every language. parse() also rejects broken templates.
    source = _messages("hy")
    for key, text in _messages(lang).items():
        if key in source:
            assert _placeholders(text) == _placeholders(source[key]), key


@pytest.mark.parametrize(
    ("template", "params", "expected"),
    [
        ("{ms:{width}}", {"ms": 5, "width": 4}, "   5"),  # a nested spec works like str.format
        ("{ms:>{width}.1f}", {"ms": 2.25, "width": 6}, "   2.2"),
        ("{ms:{width}}", {"ms": 5}, "{ms:{width}}"),  # the spec's value is missing: the raw template
    ],
)
def test_nested_format_spec(monkeypatch, template, params, expected):
    _use(monkeypatch, "hy", {"k": template})
    assert t("k", **params) == expected


def test_nested_spec_without_its_value_keeps_the_field_even_for_strftime_values(monkeypatch):
    # A date's __format__ accepts any spec, so a half-filled "{w}" spec must never reach it.
    import datetime

    _use(monkeypatch, "hy", {"k": "{day:{w}} / {pop}"})
    assert t("k", day=datetime.date(2026, 11, 22), pop="fra") == "{day:{w}} / fra"
