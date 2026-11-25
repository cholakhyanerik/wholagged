"""The i18n core: lookup, language switching, placeholders, fallback order and the catalogues themselves."""

from __future__ import annotations

import ast
import copy
import importlib
import inspect
import pickle
import pkgutil
import re
import string
from pathlib import Path

import pytest

from wholagged import checks, i18n, locales
from wholagged.i18n import Msg, render, t

from fakes import FakeNet

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


# --- texts moved out of the code -----------------------------------------------------------------


@pytest.mark.parametrize("spec", checks.CHECKS, ids=lambda s: s.key)
def test_check_title_and_hint_are_armenian_catalogue_entries(spec):
    hy = _messages("hy")
    assert (spec.title_key, spec.hint_key) == (f"check.{spec.key}.title", f"check.{spec.key}.hint")
    assert spec.title == hy[spec.title_key]
    assert spec.hint == hy[spec.hint_key]


def test_check_title_and_hint_follow_a_language_switch(monkeypatch):
    spec = checks.CHECKS[0]
    armenian = spec.title, spec.hint
    _use(monkeypatch, "en", {spec.title_key: "Internet", spec.hint_key: "Connects to Cloudflare"})
    assert (spec.title, spec.hint) == ("Internet", "Connects to Cloudflare")  # read when shown, not when built
    i18n.set_language("hy")
    assert (spec.title, spec.hint) == armenian


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


def _literal_key_calls() -> list[tuple[str, str, ast.Call]]:
    """Every `t("...")` / `Msg("...")` call with a literal key in the app's code: (where, key, call).

    The AST, not a regex over the text: a docstring example such as i18n's `t("relay.ping", ms=42)` is no call.
    """
    root = Path(i18n.__file__).parent
    calls = []
    for path in sorted(root.rglob("*.py")):
        if "locales" in path.relative_to(root).parts:
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"), filename=str(path))):
            if not (isinstance(node, ast.Call) and node.args):
                continue
            name = node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, "attr", None)
            first = node.args[0]
            if name in ("t", "Msg") and isinstance(first, ast.Constant) and isinstance(first.value, str):
                calls.append((f"{path.relative_to(root).as_posix()}:{node.lineno}", first.value, node))
    return calls


def test_every_key_used_in_the_code_is_in_the_armenian_catalogue():
    calls = _literal_key_calls()
    assert {"check.dns.ok", "check.steam_api.ok", "error.timeout"} <= {key for _, key, _ in calls}  # the scan works
    hy = _messages("hy")
    assert [f"{where}: {key}" for where, key, _ in calls if key not in hy] == []


def test_every_key_used_in_the_code_gets_exactly_its_placeholders():
    # A misspelt parameter leaves "{ms}" on screen and fills nothing; an extra one is silently ignored.
    hy = _messages("hy")
    wrong = []
    for where, key, call in _literal_key_calls():
        if key not in hy or any(kw.arg is None for kw in call.keywords):  # missing (test above) or **params
            continue
        given, needed = {kw.arg for kw in call.keywords}, _placeholders(hy[key])
        if given != needed:
            wrong.append(f"{where}: {key} gets {sorted(given)}, its text uses {sorted(needed)}")
    assert wrong == []


@pytest.mark.parametrize(
    "code",
    [
        checks.short_error,
        checks.tcp_probe,
        checks.HttpFailure,
        checks.http_get_json,
        checks._resolve,
        checks.check_internet,
        checks.check_dns,
        checks.check_steam_api,
        checks.CheckSpec,
    ],
    ids=lambda code: code.__name__,
)
def test_moved_code_has_no_inline_armenian(code):
    assert [line.strip() for line in inspect.getsource(code).splitlines() if ARMENIAN.search(line)] == []


# --- Msg: a text that can be shown again in another language ------------------------------------


def test_msg_is_the_text_t_gives_and_keeps_its_key_and_params(monkeypatch):
    _use(monkeypatch, "en", {"relay.ping": "{pop}: {ms:.0f} ms"})
    msg = Msg("relay.ping", pop="fra", ms=41.6)
    assert isinstance(msg, str)
    assert msg == t("relay.ping", pop="fra", ms=41.6) == "fra: 42 ms"
    assert msg.key == "relay.ping"
    assert msg.params == {"pop": "fra", "ms": 41.6}
    assert f"[{msg}]" == "[fra: 42 ms]"  # f-strings, joins, the report and Qt labels see the plain text
    details = [msg, "x"]
    assert "\n".join(details) == "fra: 42 ms\nx"  # how the window shows a result's details


def test_msg_param_named_key_does_not_clash_with_its_key(monkeypatch):
    _use(monkeypatch, "en", {"gui.press": "Press {key}"})
    msg = Msg("gui.press", key="Enter")
    assert msg == "Press Enter"
    assert (msg.key, msg.params) == ("gui.press", {"key": "Enter"})


@pytest.mark.parametrize("lang", i18n.LANGUAGES)
def test_msg_with_an_unknown_key_is_the_key_like_t(lang):
    i18n.set_language(lang)
    msg = Msg("no.such.key", ms=1)
    assert msg == t("no.such.key", ms=1) == "no.such.key"
    assert msg.key == "no.such.key"
    assert msg.render() == "no.such.key"


def test_msg_render_follows_a_language_switch_but_the_msg_stays_a_snapshot(monkeypatch):
    monkeypatch.setitem(i18n._catalogues, "en", {"relay.ping": "{pop}: {ms:.0f} ms"})
    _use(monkeypatch, "ru", {"relay.ping": "{pop}: {ms:.0f} мс"})
    msg = Msg("relay.ping", pop="fra", ms=41.6)
    assert msg == "fra: 42 мс"
    i18n.set_language("en")
    assert msg.render() == render(msg) == "fra: 42 ms"  # a number param keeps its format spec
    assert msg == "fra: 42 мс"  # the Msg itself is the text of the moment it was made
    i18n.set_language("ru")
    assert render(msg) == "fra: 42 мс"


PROBE_EN = {"dns": "DNS: {detail}", "probe": "{target} failed ({error})", "error.timeout": "timed out"}
PROBE_RU = {"dns": "DNS: {detail}", "probe": "{target}: ошибка ({error})", "error.timeout": "время вышло"}


def _use_russian_then_english(monkeypatch) -> None:
    monkeypatch.setitem(i18n._catalogues, "en", PROBE_EN)
    _use(monkeypatch, "ru", PROBE_RU)


def test_nested_msg_params_are_rendered_again_in_the_new_language(monkeypatch):
    _use_russian_then_english(monkeypatch)
    word = Msg("error.timeout")
    msg = Msg("dns", detail=Msg("probe", target="Cloudflare", error=word))  # two levels deep
    assert msg == "DNS: Cloudflare: ошибка (время вышло)"
    i18n.set_language("en")
    assert render(msg) == "DNS: Cloudflare failed (timed out)"
    assert msg.params["detail"] == "Cloudflare: ошибка (время вышло)"  # the params stay snapshots too
    assert word == "время вышло"


@pytest.mark.parametrize("value", ["plain text", "", "Բաց թողնվեց", 42, 4.5, None, ["a"]], ids=repr)
def test_render_passes_anything_but_a_msg_through_unchanged(monkeypatch, value):
    _use(monkeypatch, "en", {"plain text": "translated"})  # a plain str is never looked up, even if it is a key
    assert render(value) is value


def test_copied_msg_keeps_its_snapshot_and_can_still_be_rendered(monkeypatch):
    _use_russian_then_english(monkeypatch)
    msg = Msg("probe", target="Cloudflare", error=Msg("error.timeout"))
    i18n.set_language("en")
    copied = copy.deepcopy(msg)  # what dataclasses.asdict() does to a CheckResult's texts
    assert type(copied) is Msg
    assert copied == "Cloudflare: ошибка (время вышло)"  # copying doesn't render it again
    assert (copied.key, copied.params["error"].key) == ("probe", "error.timeout")
    assert copied.render() == "Cloudflare failed (timed out)"


@pytest.mark.parametrize(
    "duplicate",
    [copy.copy, copy.deepcopy, lambda m: pickle.loads(pickle.dumps(m))],  # noqa: S301 - our own bytes
    ids=["copy", "deepcopy", "pickle"],
)
def test_copying_a_msg_never_looks_its_text_up_as_a_key(monkeypatch, duplicate):
    # The text "check.b" is also a key: a copy rebuilt with Msg("check.b") would read "wrong".
    _use(monkeypatch, "en", {"check.a": "check.b", "check.b": "wrong"})
    msg = Msg("check.a", ms=5)
    copied = duplicate(msg)
    assert type(copied) is Msg
    assert copied == "check.b"
    assert (copied.key, copied.params) == ("check.a", {"ms": 5})


# --- a finished run, shown again after a language switch -----------------------------------------

# Test English for every key a run of checks 1-3 uses, and the six titles. Each text differs from the Armenian
# one, so a text that wasn't rendered again can't pass by accident.
RUN_EN = {
    "check.internet.title": "Internet connection",
    "check.dns.title": "Name lookup (DNS)",
    "check.steam_api.title": "Steam Web API reachability",
    "check.steam_cm.title": "Steam login servers",
    "check.dota_gc.title": "Dota 2 Game Coordinator status",
    "check.relays.title": "Valve game network",
    "check.probe_failed": "{target} — failed ({error})",
    "check.internet.fail": "No internet: could not connect to any outside server",
    "check.internet.ok": "Internet works ({ok}/{total}, {ms})",
    "check.dns.name_failed": "{name} — did not resolve ({error})",
    "check.dns.fail": "DNS doesn't work: no name resolved",
    "check.dns.some_failed": "Some names did not resolve: {names}",
    "check.dns.ok": "All names resolved ({ms})",
    "check.steam_api.server_error": "Steam answered with an error ({error})",
    "check.steam_api.cert_error": "No secure (HTTPS) connection to Steam ({error})",
    "check.steam_api.certificate": "Certificate: {reason}",
    "check.steam_api.unreachable": "Could not reach the Steam Web API ({error})",
    "check.steam_api.empty": "Steam answered, but the login server list is empty",
    "check.steam_api.ok": "Steam Web API answered ({ms}, {count} login servers)",
    "check.steam_api.data_centers": "Nearest data centers: {dcs}",
    "error.timeout": "timed out",
    "error.refused": "connection refused",
    "error.reset": "connection reset",
    "error.dns": "name not found",
    "error.ssl": "TLS error",
    "error.too_big": "answer too big",
    "error.not_json": "answer is not JSON",
}

# [title, summary, *details] of a check, as shown after the switch.
INTERNET_OK = [
    "Internet connection",
    "Internet works (3/3, 12 ms)",
    "Cloudflare (1.1.1.1:443) — 12 ms",
    "Google (8.8.8.8:443) — 12 ms",
    "Quad9 (9.9.9.9:443) — 12 ms",
]
DNS_OK = [
    "Name lookup (DNS)",
    "All names resolved (4 ms)",
    "api.steampowered.com → 1.2.3.4 (4 ms)",
    "steamcommunity.com → 1.2.3.4 (4 ms)",
    "google.com → 1.2.3.4 (4 ms)",
]
STEAM_API_OK = [
    "Steam Web API reachability",
    "Steam Web API answered (120 ms, 5 login servers)",
    "Nearest data centers: fra1, sto1, vie1",
]


def _set(name, value):
    return lambda net: setattr(net, name, value)


def _answer(url, value):
    return lambda net: net.http.update({url: value})


RERUN_CASES = {
    "all-ok": (lambda net: None, {"internet": INTERNET_OK, "dns": DNS_OK, "steam_api": STEAM_API_OK}),
    "no-internet": (
        _set("internet", False),
        {
            "internet": [
                "Internet connection",
                "No internet: could not connect to any outside server",
                "Cloudflare (1.1.1.1:443) — failed (timed out)",
                "Google (8.8.8.8:443) — failed (timed out)",
                "Quad9 (9.9.9.9:443) — failed (timed out)",
            ]
        },
    ),
    "dns-broken": (
        _set("dns", False),
        {
            "internet": INTERNET_OK,
            "dns": [
                "Name lookup (DNS)",
                "DNS doesn't work: no name resolved",
                "api.steampowered.com — did not resolve (name not found)",
                "steamcommunity.com — did not resolve (name not found)",
                "google.com — did not resolve (name not found)",
            ],
            "steam_api": [
                "Steam Web API reachability",
                "Could not reach the Steam Web API (timed out)",
                checks.CM_LIST_URL,
            ],
        },
    ),
    "steam-api-name-missing": (
        _set("unresolved", {"api.steampowered.com"}),
        {
            "dns": [
                "Name lookup (DNS)",
                "Some names did not resolve: api.steampowered.com",
                "api.steampowered.com — did not resolve (name not found)",
                "steamcommunity.com → 1.2.3.4 (4 ms)",
                "google.com → 1.2.3.4 (4 ms)",
            ],
            "steam_api": [
                "Steam Web API reachability",
                "Could not reach the Steam Web API (name not found)",
                checks.CM_LIST_URL,
            ],
        },
    ),
    "bad-certificate": (
        _set("cert_ok", False),
        {
            "internet": INTERNET_OK,
            "dns": DNS_OK,
            "steam_api": [
                "Steam Web API reachability",
                "No secure (HTTPS) connection to Steam (TLS error)",
                checks.CM_LIST_URL,
                "Certificate: certificate has expired",
            ],
        },
    ),
    "valve-503": (
        _answer(checks.CM_LIST_URL, 503),
        {"steam_api": ["Steam Web API reachability", "Steam answered with an error (HTTP 503)", checks.CM_LIST_URL]},
    ),
    "empty-server-list": (
        _answer(checks.CM_LIST_URL, {"response": {"serverlist": []}}),
        {"steam_api": ["Steam Web API reachability", "Steam answered, but the login server list is empty"]},
    ),
}


@pytest.fixture
def net(monkeypatch):
    return FakeNet().install(monkeypatch)


def _texts(res) -> list[str]:
    return [res.title, res.summary, *res.details]


def test_test_english_uses_the_armenian_keys_and_placeholders():
    hy = _messages("hy")
    assert RUN_EN.keys() <= hy.keys()
    for key, text in RUN_EN.items():
        assert _placeholders(text) == _placeholders(hy[key]), key
        assert text != hy[key], key


@pytest.mark.parametrize(("breaks", "expected"), RERUN_CASES.values(), ids=RERUN_CASES.keys())
def test_finished_run_is_shown_again_in_the_new_language(net, monkeypatch, breaks, expected):
    breaks(net)
    results = checks.run_checks()  # made in Armenian, like a run that finished before the switch
    made = {key: _texts(results[key]) for key in expected}
    snapshot = {key: [str(text) for text in texts] for key, texts in made.items()}
    for key, (_, summary, *_) in snapshot.items():
        assert ARMENIAN.search(summary), key

    _use(monkeypatch, "en", RUN_EN)
    for key, texts in made.items():
        assert [render(text) for text in texts] == expected[key], key
        assert [str(text) for text in texts] == snapshot[key], key  # the result itself keeps the run's text

    i18n.set_language("hy")
    for key, texts in made.items():
        assert [render(text) for text in texts] == snapshot[key], key  # and back, word for word


def test_every_result_title_is_shown_again_in_the_new_language(net, monkeypatch):
    net.internet = False  # the skipped checks get their titles too
    results = checks.run_checks()
    hy = _messages("hy")
    _use(monkeypatch, "en", RUN_EN)
    for spec in checks.CHECKS:
        title = results[spec.key].title
        assert (title.key, str(title)) == (spec.title_key, hy[spec.title_key])
        assert render(title) == RUN_EN[spec.title_key]


@pytest.mark.parametrize(
    ("breaks", "check", "key"),
    [
        (_set("internet", False), "internet", "error.timeout"),
        (_set("dns", False), "dns", "error.dns"),
        (_set("dns", False), "steam_api", "error.timeout"),
        (_set("unresolved", {"api.steampowered.com"}), "steam_api", "error.dns"),
        (_set("cert_ok", False), "steam_api", "error.ssl"),
    ],
    ids=["probe-timeout", "dns-name", "api-timeout", "api-name", "api-certificate"],
)
def test_fake_network_gives_msg_error_words_like_the_real_helpers(net, breaks, check, key):
    breaks(net)
    res = checks.run_checks()[check]
    failed = next(text for text in [res.summary, *res.details] if isinstance(text, Msg) and "error" in text.params)
    word = failed.params["error"]
    assert isinstance(word, Msg)
    assert word.key == key
