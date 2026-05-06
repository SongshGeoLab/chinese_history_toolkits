<!--
Purpose:
- Track current implementation progress, open questions, and next steps during active development.

Audience:
- Any contributor (or coding agent) coordinating ongoing work.

Usage:
- Keep entries brief and actionable; remove outdated notes once resolved.
-->
# Progress

## Done

- **Pipeline**: scrape → validate → clean. `clean_dynasties.py` produces `dynasty_clean.csv` (854 rows) and `dynasty_drops.md` (per-row audit). Every modification emits `RawDataModifiedWarning`.
- **Runtime API** in `src/chhiskit/core/dynasties.py`:
  - `get_age_from_cultural_period(cp, level, anno_domini, time_table, aliases)` — name → `(begin, end)`. Levels: `period` / `dynasty` / `epoch`. BP conversion via `anno_domini=False`. Custom timetable via `time_table`. Foreign-name aliases via `aliases`.
  - `get_cultural_periods_from_year(year, anno_domini, time_table)` — year → `list[CulturalPeriodMatch]` (sorted by `(beginYear, endYear)`).
  - `EPOCH_MAP` (汉/晋/三国/宋/五代/南北朝/上古) and `PREHISTORIC_EPOCHS` (旧石器/新石器).
- **Tests**: 103 passing in `tests/test_dynasties.py` (one `Test*` class per behavior cluster, parametrized cases with explicit `ids`).
- **Docstring coverage**: 100% on `src/chhiskit/core/dynasties.py` (interrogate ≥ 80% gate passing).
- **Docs**: bilingual user docs under `docs/{en,zh}/`; root `README.md` + `README.zh.md` rewritten as project intro.

## Open questions / next steps

- **Dynasty-level disambiguation by `dynasty_id`**: currently `level="dynasty"` for `"夏"` returns the union span `(-1989, 623)`. The escape hatch is `level="epoch"` with `"上古"`, but a more direct API would be welcome. *(Pinned by a test; change deliberately.)*
- **5th E-row**: 南诏上元 (`784~?`) is intentionally left as NaN; should be filled if a documented end is found, otherwise stays as the function's NaN-end test fixture.

## Packaging

- **PyPI distribution name**: `chinese_history_toolkits` (also matches the GitHub repo name).
- **Python import name**: `chhiskit` (short acronym; cleanest user UX).
- **Bundled data**: `dynasty_clean.csv` is shipped inside the wheel at `chhiskit/data/dynasties/`. Other data artifacts (`raw`, `issues`, `drops.md`) stay in repo-level `data/dynasties/` for dev only.
- **Trusted publishing**: configured on PyPI for `chinese_history_toolkits` ← `SongshGeoLab/chinese_history_toolkits` workflow `release-please.yml`, no environment.

## Recent files touched

- `scripts/dynasties/clean_dynasties.py` (new)
- `data/dynasties/{dynasty_clean.csv, dynasty_drops.md, readme.md}` (new / rewritten)
- `src/chhiskit/core/dynasties.py` (substantial)
- `tests/test_dynasties.py` (new, 103 cases)
- `docs/index{,.zh}.md`, `docs/doc/*{,.zh}.md` (rewritten + reorganized for `mkdocs-static-i18n`)
- `mkdocs.yml` (single config; `mkdocs.en.yml` / `mkdocs.zh.yml` deleted in favor of i18n plugin)
- Root `README.md`, `README.zh.md` (rewritten)
