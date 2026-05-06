<!--
Purpose:
- Describe the project's domain/data model design (core entities, relationships, and invariants).

Audience:
- Developers implementing features that touch data shapes, validation, or persistence.

Usage:
- Keep this aligned with code changes; prefer concise diagrams/examples and links to source-of-truth.
-->
# Project design

这个项目是一个处理中国历史数据的工具仓库。包括以下实用工具：

- 断代史判别数据：利用[上海图书馆开放数据平台](https://data.library.sh.cn/dynasty/)的朝代列表数据，将具体公元纪年与中国朝代/皇帝年号对应。

## Domain entity (post-clean)

`dynasty_clean.csv` is the canonical table; the runtime API reads it through `src/chhiskit/core/dynasties.py`.

| Column | Type | Meaning |
|---|---|---|
| `dynasty_id` | str | **Disambiguated polity key**, defaults to `dynasty`. Ancient names reused in AD periods get a `(monarchName)` suffix, e.g. `夏(窦建德)`. |
| `dynasty` | str | Raw 上图 dynasty literal (preserved). |
| `reignTitle` | str | 年号 (`康熙`, `开皇`, …). |
| `monarch` / `monarchName` | str | 帝号 / 帝王本名. |
| `beginYear` / `endYear` | int | AD/BCE year (BCE negative). One deliberate NaN end (南诏上元). |
| `label` | str | 上图 label (`清康熙`, …). |
| `uri` | str | 上图 URI, audit traceability. |

## Lookup levels (input semantics)

- **period**: match by `reignTitle`, fallback to `label`. Single 年号 query.
- **dynasty**: match by `dynasty` literal (NOT `dynasty_id`). Returns the union span. *Known limitation*: `夏` returns `(-1989, 623)` because both 上古夏 and 隋末夏 share the literal — use `epoch=上古` for ancient-only.
- **epoch**: first check `PREHISTORIC_EPOCHS` (旧石器 / 新石器), then `EPOCH_MAP` (汉 / 晋 / 三国 / 宋 / 五代 / 南北朝 / 上古) with optional year bounds, else fall back to dynasty match.

## Cleaning rules

| Category | Tag | Count | Action | Reason |
|---|---|---|---|---|
| F1 truncated dup | `F1:trunc-dup` | 7 | **drop** | longer-span sibling already in data |
| F2 split-span | `F2:split-span` | 36→18 groups | **merge `[min,max]`** | year → single 年号 |
| E missing-end | `E:missing-year` | 5 (4 filled / 1 NaN) | **`KNOWN_ENDS` table** | 4 from documented history; 南诏上元 deliberately NaN |
| B ancient reuse | `B:ancient-name-AD` | 4 (F1 dropped 1) | **add `(monarchName)` to `dynasty_id`** | 隋末 "夏" is a real polity; don't drop |
| C 1-year era | `C:1yr-span` | 141 | **keep** | mostly real 短命年号 |
| D missing monarchName | `D:no-monarch` | — | **keep** | metadata gap, doesn't affect lookup |

## Errors

- `AmbiguousCulturalPeriodError` (subclass of `ValueError`) — same `reignTitle` matches ≥2 `(dynasty, monarchName)` keys.
- `ValueError` — empty input, unknown level, alias maps to ≥2 canonicals, or matched rows all NaN.
- `KeyError` — name has no match in the data.

## Prehistoric brackets (hand-coded)

- `旧石器`: `(-inf, -10000)` — open-ended start.
- `新石器`: `(-10000, -2070)` — 上界为传统 "夏朝建立" 年份 (夏商周断代工程).

`新石器` end `-2070` and the data's `夏` begin `-1989` differ by 81 years — different sources, not a bug.

## API contracts (high-leverage)

- Both functions accept `time_table: pd.DataFrame` for tests / custom datasets.
- `_KNOWN_BAD_URIS` is filtered **only** in the default loader, not user-supplied tables (pinned by a test).
- `get_age_from_cultural_period(..., aliases=...)`: `{canonical: {alias, ...}}`. Canonical passes through; one-canonical alias rewrites; multi-canonical alias raises `ValueError`; unknown name passes through to `KeyError`.
- `get_cultural_periods_from_year(...)`: returns `list[CulturalPeriodMatch]`, sorted by `(beginYear, endYear)`. NaN-end rows silently skipped. Prehistoric matches have `uri=""`.
