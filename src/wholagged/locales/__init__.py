"""Translation catalogues, one module per language (`hy`, `ru`, `en`), each with a `MESSAGES` dict.

Keys are dotted, grouped by where the text is used (`app.`, `check.`, `verdict.`, `report.`, `gui.`).
Armenian (`hy`) is the source: add a key there first, then in `ru` and `en` (the `translator` subagent).
Placeholders use `str.format` syntax (`{ms}`) and must be the same in every language.
"""
