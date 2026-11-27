"""The i18n core: lookup, language switching, placeholders, fallback order and the catalogues themselves."""

from __future__ import annotations

import ast
import copy
import importlib
import pickle
import pkgutil
import re
import string
from pathlib import Path

import pytest

from wholagged import checks, i18n, icmp, locales, models
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


def _fields(text: str) -> set[tuple[str, str, str | None]]:
    """Each field with its format spec and conversion: `{loss:.0f}` is ("loss", ".0f", None)."""
    return {(name, spec, conv) for _, name, spec, conv in string.Formatter().parse(text) if name is not None}


@pytest.mark.parametrize("lang", ["ru", "en"])
def test_translations_use_the_same_placeholders_as_armenian(lang):
    # locales/__init__.py: placeholders must be the same in every language. parse() also rejects broken templates.
    source = _messages("hy")
    for key, text in _messages(lang).items():
        if key in source:
            assert _placeholders(text) == _placeholders(source[key]), key


@pytest.mark.parametrize("lang", ["ru", "en"])
def test_translations_keep_the_armenian_format_specs(lang):
    # A translation that drops `:.0f` from `{loss:.0f}%` would show "26.666666666666668%".
    source = _messages("hy")
    for key, text in _messages(lang).items():
        if key in source:
            assert _fields(text) == _fields(source[key]), key


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


# Modules whose user-facing texts have all moved to the catalogues: not one Armenian letter is left, not even
# in a comment. Add a module when its move card is done (verdict.py: WL-24; report.py and __init__.py: WL-25;
# gui.py: WL-26).
MOVED_MODULES = [checks, icmp, models]


@pytest.mark.parametrize("module", MOVED_MODULES, ids=lambda module: module.__name__)
def test_moved_module_has_no_inline_armenian(module):
    lines = Path(module.__file__).read_text(encoding="utf-8").splitlines()
    assert [f"{n}: {line.strip()}" for n, line in enumerate(lines, 1) if ARMENIAN.search(line)] == []


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

# Test English for every key a run of the six checks and the runner uses. Each text differs from the Armenian
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
    "check.steam_cm.fallback": "No login server list, so Steam's web servers are checked instead",
    "check.steam_cm.fail": "Could not connect to any Steam login server",
    "check.steam_cm.web_fail": "Could not connect to any Steam web server",
    "check.steam_cm.ok": "Steam login servers reachable ({ok}/{total}, median {ms})",
    "check.steam_cm.web_ok": "Steam web servers reachable ({ok}/{total}, median {ms})",
    "check.steam_cm.partial": "Only {ok}/{total} servers reachable",
    "check.dota_gc.note": "Checked indirectly through the Web API; see steamstat.us to be sure",
    "check.dota_gc.down": "Dota GC is not answering ({error})",
    "check.dota_gc.unknown": "Could not check ({error})",
    "check.dota_gc.bad_answer": "Unexpected answer: can't judge",
    "check.dota_gc.ok": "Dota GC answers ({ms})",
    "check.dota_gc.ok_version": "Dota GC answers ({ms}, version {version})",
    "check.relays.list_failed": "Could not get the relay list ({error})",
    "check.relays.empty": "The relay list is empty",
    "check.relays.routing": "Valve's relays don't answer ping, though the rest of the internet does",
    "check.relays.checked": "Relays checked: {count}",
    "check.relays.icmp_blocked": "ICMP ping looks blocked on this network, so the relays can't be checked",
    "check.relays.responded": "Relays that answered: {ok}/{total}",
    "check.relays.quality": "{pop}: {sent} pings, {loss:.0f}% loss, average {avg}, jitter {jitter}",
    "check.relays.lossy": "{loss:.0f}% packet loss: the connection is unstable",
    "check.relays.high_ping": "High ping: {ms} ({pop})",
    "check.relays.jittery": "Unsteady ping (jitter {ms})",
    "check.relays.ok": "Best: {pop}, {ms}, {loss:.0f}% loss",
    "check.skipped_no_internet": "Skipped: no internet",
    "check.internal_error": "Internal error in the check: {error}",
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
CM_LOGIN = [  # pick_cm_targets() of fakes.CM_LIST: the four websockets servers
    "ext1-fra1.steamserver.net:27019 [fra1]",
    "ext2-fra1.steamserver.net:27019 [fra1]",
    "ext1-sto1.steamserver.net:27019 [sto1]",
    "ext1-vie1.steamserver.net:443 [vie1]",
]
CM_WEB = ["store.steampowered.com:443 [web]", "steamcommunity.com:443 [web]", "api.steampowered.com:443 [web]"]
STEAM_CM_OK = [
    "Steam login servers",
    "Steam login servers reachable (4/4, median 35 ms)",
    *[f"{target} — 35 ms" for target in CM_LOGIN],
]
GC_NOTE = RUN_EN["check.dota_gc.note"]
DOTA_GC_OK = ["Dota 2 Game Coordinator status", "Dota GC answers (120 ms, version 7001)", GC_NOTE]
RELAY_SITES = [  # fakes.RELAY_MS, fastest first
    "Vienna (vie) — 47 ms",
    "Frankfurt (fra) — 52 ms",
    "Stockholm (sto) — 58 ms",
    "Dubai (dxb) — 71 ms",
    "Singapore (sgp) — 160 ms",
]
RELAYS_OK = [
    "Valve game network",
    "Best: Vienna, 47 ms, 0% loss",
    *RELAY_SITES,
    "Relays that answered: 5/5",
    "Vienna: 10 pings, 0% loss, average 47 ms, jitter <1 ms",
    "Frankfurt: 10 pings, 0% loss, average 52 ms, jitter <1 ms",
    "Stockholm: 10 pings, 0% loss, average 58 ms, jitter <1 ms",
]


def _skipped(title):
    return [title, "Skipped: no internet"]


def _set(name, value):
    return lambda net: setattr(net, name, value)


def _answer(url, value):
    return lambda net: net.http.update({url: value})


def _all(*breaks):
    def apply(net):
        for one in breaks:
            one(net)

    return apply


RERUN_CASES = {
    "all-ok": (
        lambda net: None,
        {
            "internet": INTERNET_OK,
            "dns": DNS_OK,
            "steam_api": STEAM_API_OK,
            "steam_cm": STEAM_CM_OK,
            "dota_gc": DOTA_GC_OK,
            "relays": RELAYS_OK,
        },
    ),
    "no-internet": (
        _set("internet", False),
        {
            "internet": [
                "Internet connection",
                "No internet: could not connect to any outside server",
                "Cloudflare (1.1.1.1:443) — failed (timed out)",
                "Google (8.8.8.8:443) — failed (timed out)",
                "Quad9 (9.9.9.9:443) — failed (timed out)",
            ],
            "dns": _skipped("Name lookup (DNS)"),
            "steam_api": _skipped("Steam Web API reachability"),
            "steam_cm": _skipped("Steam login servers"),
            "dota_gc": _skipped("Dota 2 Game Coordinator status"),
            "relays": _skipped("Valve game network"),
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
    # 4. Steam login servers
    "valve-unreachable": (
        _set("tcp_ok", False),
        {
            "steam_cm": [
                "Steam login servers",
                "Could not connect to any Steam web server",
                "No login server list, so Steam's web servers are checked instead",
                *[f"{target} — failed (timed out)" for target in CM_WEB],
            ],
            "dota_gc": ["Dota 2 Game Coordinator status", "Could not check (timed out)", GC_NOTE],
            "relays": ["Valve game network", "Could not get the relay list (timed out)"],
        },
    ),
    "login-list-unusable": (
        _answer(checks.CM_LIST_URL, {"response": {"serverlist": [{"endpoint": "no-port", "dc": "fra1"}]}}),
        {
            "steam_cm": [
                "Steam login servers",
                "Steam web servers reachable (3/3, median 35 ms)",
                "No login server list, so Steam's web servers are checked instead",
                *[f"{target} — 35 ms" for target in CM_WEB],
            ]
        },
    ),
    "login-servers-partly-refused": (
        _set("refused_hosts", {"ext1-fra1.steamserver.net", "ext2-fra1.steamserver.net", "ext1-sto1.steamserver.net"}),
        {
            "steam_cm": [
                "Steam login servers",
                "Only 1/4 servers reachable",
                *[f"{target} — failed (connection refused)" for target in CM_LOGIN[:3]],
                f"{CM_LOGIN[3]} — 35 ms",
            ]
        },
    ),
    "login-servers-all-refused": (
        _set("refused_hosts", {target.split(":")[0] for target in CM_LOGIN}),
        {
            "steam_cm": [
                "Steam login servers",
                "Could not connect to any Steam login server",
                *[f"{target} — failed (connection refused)" for target in CM_LOGIN],
            ]
        },
    ),
    # 5. Dota 2 Game Coordinator
    "gc-without-version": (
        _answer(checks.GC_VERSION_URL, {"result": {"success": True}}),
        {"dota_gc": ["Dota 2 Game Coordinator status", "Dota GC answers (120 ms)", GC_NOTE]},
    ),
    "gc-503": (
        _answer(checks.GC_VERSION_URL, 503),
        {"dota_gc": ["Dota 2 Game Coordinator status", "Dota GC is not answering (HTTP 503)", GC_NOTE]},
    ),
    "gc-success-false": (
        _answer(checks.GC_VERSION_URL, {"result": {"success": False}}),
        {"dota_gc": ["Dota 2 Game Coordinator status", "Dota GC is not answering (success = false)", GC_NOTE]},
    ),
    "gc-404": (
        _answer(checks.GC_VERSION_URL, 404),
        {"dota_gc": ["Dota 2 Game Coordinator status", "Could not check (HTTP 404)", GC_NOTE]},
    ),
    "gc-bad-answer": (
        _answer(checks.GC_VERSION_URL, {"result": ["success"]}),
        {"dota_gc": ["Dota 2 Game Coordinator status", "Unexpected answer: can't judge", GC_NOTE]},
    ),
    # 6. Valve's game network
    "relays-lossy": (
        _set("loss_every", 4),  # the 4th and 8th of each relay's 10 quality pings
        {
            "relays": [
                "Valve game network",
                "20% packet loss: the connection is unstable",
                *RELAY_SITES,
                "Relays that answered: 5/5",
                "Vienna: 10 pings, 20% loss, average 47 ms, jitter <1 ms",
                "Frankfurt: 10 pings, 20% loss, average 52 ms, jitter <1 ms",
                "Stockholm: 10 pings, 20% loss, average 58 ms, jitter <1 ms",
            ]
        },
    ),
    "relays-high-ping": (
        _set("relay_extra_ms", 140.0),
        {
            "relays": [
                "Valve game network",
                "High ping: 187 ms (Vienna)",
                "Vienna (vie) — 187 ms",
                "Frankfurt (fra) — 192 ms",
                "Stockholm (sto) — 198 ms",
                "Dubai (dxb) — 211 ms",
                "Singapore (sgp) — 300 ms",
                "Relays that answered: 5/5",
                "Vienna: 10 pings, 0% loss, average 187 ms, jitter <1 ms",
                "Frankfurt: 10 pings, 0% loss, average 192 ms, jitter <1 ms",
                "Stockholm: 10 pings, 0% loss, average 198 ms, jitter <1 ms",
            ]
        },
    ),
    "relays-jittery": (
        _set("relay_jitter_ms", 40.0),  # the first ping to each relay is the plain one
        {
            "relays": [
                "Valve game network",
                "Unsteady ping (jitter 40 ms)",
                *RELAY_SITES,
                "Relays that answered: 5/5",
                "Vienna: 10 pings, 0% loss, average 67 ms, jitter 40 ms",
                "Frankfurt: 10 pings, 0% loss, average 72 ms, jitter 40 ms",
                "Stockholm: 10 pings, 0% loss, average 78 ms, jitter 40 ms",
            ]
        },
    ),
    "relays-silent": (
        _set("relays_ok", False),
        {
            "relays": [
                "Valve game network",
                "Valve's relays don't answer ping, though the rest of the internet does",
                "Relays checked: 5",
            ]
        },
    ),
    "icmp-blocked": (
        _all(_set("relays_ok", False), _set("control_ok", False)),
        {"relays": ["Valve game network", "ICMP ping looks blocked on this network, so the relays can't be checked"]},
    ),
    "relay-list-empty": (
        _answer(checks.SDR_CONFIG_URL, {"revision": 2, "pops": {}}),
        {"relays": ["Valve game network", "The relay list is empty"]},
    ),
    # The runner: a check that crashes. The error word is a Msg too, so it is rendered again.
    "check-crashes": (
        _answer(checks.GC_VERSION_URL, ConnectionResetError()),
        {
            "dota_gc": ["Dota 2 Game Coordinator status", "Internal error in the check: connection reset"],
            "relays": RELAYS_OK,  # the run goes on
        },
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
        assert _fields(text) == _fields(hy[key]), key  # `{loss:.0f}` keeps its spec
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
        (_set("refused_hosts", {"api.steampowered.com"}), "steam_api", "error.refused"),
        (_set("tcp_ok", False), "steam_cm", "error.timeout"),
        (_set("refused_hosts", {"ext1-fra1.steamserver.net"}), "steam_cm", "error.refused"),
        (_set("unresolved", {"ext1-sto1.steamserver.net"}), "steam_cm", "error.dns"),
        (_set("tcp_ok", False), "dota_gc", "error.timeout"),
        (_set("tcp_ok", False), "relays", "error.timeout"),
    ],
    ids=[
        "probe-timeout",
        "dns-name",
        "api-timeout",
        "api-name",
        "api-certificate",
        "api-refused",
        "cm-fallback-timeout",
        "cm-refused",
        "cm-name",
        "gc-timeout",
        "relay-list-timeout",
    ],
)
def test_fake_network_gives_msg_error_words_like_the_real_helpers(net, breaks, check, key):
    breaks(net)
    res = checks.run_checks()[check]
    failed = next(text for text in [res.summary, *res.details] if isinstance(text, Msg) and "error" in text.params)
    word = failed.params["error"]
    assert isinstance(word, Msg)
    assert word.key == key


@pytest.mark.parametrize(
    ("breaks", "check", "summary", "error"),
    [
        (_set("tcp_ok", False), "dota_gc", "check.dota_gc.unknown", "error.timeout"),
        (_set("tcp_ok", False), "relays", "check.relays.list_failed", "error.timeout"),
        (_set("refused_hosts", {"api.steampowered.com"}), "dota_gc", "check.dota_gc.unknown", "error.refused"),
        (_set("refused_hosts", {"api.steampowered.com"}), "relays", "check.relays.list_failed", "error.refused"),
        (_set("cert_ok", False), "dota_gc", "check.dota_gc.unknown", "error.ssl"),
        (_set("cert_ok", False), "relays", "check.relays.list_failed", "error.ssl"),
    ],
    ids=["gc-timeout", "relays-timeout", "gc-refused", "relays-refused", "gc-certificate", "relays-certificate"],
)
def test_http_failure_word_reaches_the_summary_as_a_msg_not_flattened_by_str(net, breaks, check, summary, error):
    # `HttpFailure.message`, not `str(exc)`: a str would be the Armenian word forever.
    breaks(net)
    res = checks.run_checks()[check]
    assert res.summary.key == summary
    word = res.summary.params["error"]
    assert type(word) is Msg
    assert (word.key, word.params) == (error, {})


@pytest.mark.parametrize(
    ("answer", "summary", "error"),
    [(503, "check.dota_gc.down", "HTTP 503"), (404, "check.dota_gc.unknown", "HTTP 404")],
    ids=["503", "404"],
)
def test_http_status_in_a_gc_summary_is_plain_text(net, answer, summary, error):
    net.http[checks.GC_VERSION_URL] = answer
    res = checks.run_checks()["dota_gc"]
    assert res.summary.key == summary
    assert res.summary.params["error"] == error
    assert type(res.summary.params["error"]) is str  # no words to translate: no key


@pytest.mark.parametrize(
    ("breaks", "failed", "error"),
    [
        (_set("tcp_ok", False), 3, "error.timeout"),  # the web fallback: no login server list
        (_set("refused_hosts", {"ext1-fra1.steamserver.net", "ext1-vie1.steamserver.net"}), 2, "error.refused"),
        (_set("unresolved", {"ext2-fra1.steamserver.net"}), 1, "error.dns"),
    ],
    ids=["fallback-timeout", "refused", "name"],
)
def test_every_steam_server_probe_failure_is_a_msg_with_a_msg_error_word(net, breaks, failed, error):
    breaks(net)
    res = checks.run_checks()["steam_cm"]
    probes = [d for d in res.details if isinstance(d, Msg) and d.key == "check.probe_failed"]
    assert len(probes) == failed
    for probe in probes:
        assert type(probe.params["error"]) is Msg
        assert probe.params["error"].key == error
    assert all(d.endswith(" ms") for d in res.details if type(d) is str)  # plain text only for "host — 35 ms"


@pytest.mark.parametrize(
    "exc",
    [
        RuntimeError("bug"),
        KeyError("result"),
        ValueError(),
        ConnectionResetError(),
        TimeoutError("timed out"),
        OSError(113, "No route to host"),
    ],
    ids=lambda exc: type(exc).__name__,
)
def test_internal_error_carries_short_error_of_the_exception(net, exc):
    net.http[checks.GC_VERSION_URL] = exc  # an exception the check doesn't expect escapes it
    results = checks.run_checks()
    res = results["dota_gc"]
    assert res.status == models.Status.SKIP
    assert res.summary.key == "check.internal_error"
    word, expected = res.summary.params["error"], checks.short_error(exc)
    assert word == expected
    assert type(word) is type(expected)  # a Msg for the errors we have words for, else the system's own text
    if isinstance(expected, Msg):
        assert (word.key, word.params) == (expected.key, expected.params)
    assert results["relays"].status == models.Status.OK  # the run went on
