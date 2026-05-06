# API Reference

Two functions, both in `src.core.dynasties`. Both consume `dynasty_clean.csv` by default; pass your own `time_table` to override.

---

## `get_age_from_cultural_period`

Map a cultural-period name to its `(begin, end)` years.

### Signature

```python
def get_age_from_cultural_period(
    cultural_period: str,
    level: Literal["period", "dynasty", "epoch"] = "period",
    *,
    anno_domini: bool = True,
    time_table: pd.DataFrame | None = None,
    aliases: Mapping[str, Iterable[str]] | None = None,
) -> tuple[float, float]:
```

### Parameters

| Param | Description |
|---|---|
| `cultural_period` | The name to resolve. Whitespace is stripped. Aliases (if provided) are applied first. |
| `level` | `"period"` (year-name match), `"dynasty"` (dynasty literal), or `"epoch"` (curated aggregations + prehistoric brackets). |
| `anno_domini` | `True` (default) returns AD/BCE; `False` returns BP relative to 1950 (radiocarbon convention). |
| `time_table` | Optional `DataFrame` with the same schema as `dynasty_clean.csv`. Year columns can be strings — they're coerced. **`_KNOWN_BAD_URIS` is NOT applied to user-supplied tables.** |
| `aliases` | Optional `{canonical_name: {alias, ...}}` map. See [Aliases](#aliases). |

### Returns

`(begin, end)` floats. AD mode: `begin <= end`. BP mode: `begin >= end` (older first).

### Levels in detail

#### `level="period"` — match by 年号

```python
get_age_from_cultural_period("康熙")              # → (1662.0, 1722.0)
get_age_from_cultural_period("元平")              # → (-74.0, -74.0)   single-year BCE
get_age_from_cultural_period("清康熙")            # → (1662.0, 1722.0) label fallback
```

If `reignTitle` doesn't match, the function falls back to the full `label` column (e.g. `"清康熙"`). If the same `reignTitle` belongs to ≥2 distinct rulers (e.g. `建平` was used by 7 rulers), it raises `AmbiguousCulturalPeriodError`:

```python
get_age_from_cultural_period("建平")
# AmbiguousCulturalPeriodError: reignTitle='建平' matches 7 different rulers
```

#### `level="dynasty"` — match by dynasty literal

```python
get_age_from_cultural_period("唐", level="dynasty")    # → (618.0, 907.0)
get_age_from_cultural_period("商", level="dynasty")    # → (-1559.0, -1123.0)
```

Returns the union span over all rows with that `dynasty`. **Caveat**: the function matches the raw `dynasty` column, not `dynasty_id`. So `"夏"` returns `(-1989, 623)` because both 上古夏 and 隋末夏 share the literal — use `level="epoch"` with `"上古"` for ancient-only.

#### `level="epoch"` — curated aggregations

```python
get_age_from_cultural_period("汉", level="epoch")      # → (-206.0, 220.0)
get_age_from_cultural_period("三国", level="epoch")    # → (220.0, 280.0)
get_age_from_cultural_period("上古", level="epoch")    # → (-1989.0, -221.0)
get_age_from_cultural_period("新石器", level="epoch")  # → (-10000.0, -2070.0)
get_age_from_cultural_period("旧石器", level="epoch")  # → (-inf, -10000.0)
```

Resolution order:

1. Prehistoric brackets in `PREHISTORIC_EPOCHS` (旧石器 / 新石器) — short-circuit, no DataFrame work.
2. Aggregations in `EPOCH_MAP` (汉 / 晋 / 三国 / 宋 / 五代 / 南北朝 / 上古) — filter rows by `dynasty in [...]` then by year bounds.
3. Fallback to `level="dynasty"` match.

See the [Epochs Reference](epochs.md) for the full table.

### `anno_domini=False`: BP mode

```python
get_age_from_cultural_period("商", level="dynasty", anno_domini=False)
# → (3509.0, 3073.0)   # BP = 1950 - AD; older first

get_age_from_cultural_period("旧石器", level="epoch", anno_domini=False)
# → (inf, 11950.0)     # -inf in AD becomes +inf in BP
```

### `aliases`

Pre-rewrites `cultural_period` to a canonical name before any matching. Useful for:

- foreign-language input (`"Tang"` → `"唐"`)
- shorthand (`"Neo"` → `"新石器"`)
- legacy spellings (Wade-Giles → Pinyin → 汉字)

```python
ALIASES = {
    "新石器": {"Neolithic", "Neo"},
    "旧石器": {"Paleolithic"},
    "唐":   {"Tang", "T'ang"},
    "康熙": {"Kangxi", "K'ang-hsi"},
}

get_age_from_cultural_period("Neo", level="epoch", aliases=ALIASES)
# → (-10000.0, -2070.0)
```

Resolution rules:

| Input | Behavior |
|---|---|
| `aliases=None` or `{}` | no-op, identical to omitting the arg |
| `cp` is a canonical key | no rewrite — canonical query path |
| `cp` matches one canonical's alias set | rewrite to the canonical |
| `cp` matches ≥2 canonicals' alias sets | `ValueError` naming all candidates |
| `cp` matches no canonical / alias | passes through → downstream `KeyError` |

The alias values can be any iterable (`set`, `frozenset`, `tuple`, `list`).

### Errors

| Exception | When |
|---|---|
| `KeyError` | name has no match (after alias resolution) |
| `AmbiguousCulturalPeriodError` (subclass of `ValueError`) | `level="period"` and the `reignTitle` matches ≥2 rulers |
| `ValueError` | empty input, unknown level, alias maps to ≥2 canonicals, or matched rows all have NaN years |

---

## `get_cultural_periods_from_year`

Map a year to every dynasty / reign-era / prehistoric epoch covering it.

### Signature

```python
def get_cultural_periods_from_year(
    year: float,
    *,
    anno_domini: bool = True,
    time_table: pd.DataFrame | None = None,
) -> list[CulturalPeriodMatch]:
```

### Parameters

| Param | Description |
|---|---|
| `year` | Query year. AD/BCE by default (BCE negative). With `anno_domini=False`, interpreted as BP-1950 and converted to AD before matching. |
| `anno_domini` | How to read `year`. The output `beginYear` / `endYear` on each match are **always** in AD/BCE form. |
| `time_table` | Optional override DataFrame, same schema as `dynasty_clean.csv`. |

### Returns

`list[CulturalPeriodMatch]`, sorted by `(beginYear, endYear)` ascending. Empty list when no record covers the year.

`CulturalPeriodMatch` is a `NamedTuple`:

```python
class CulturalPeriodMatch(NamedTuple):
    dynasty_id: str
    dynasty: str
    reignTitle: str
    monarch: str
    monarchName: str
    beginYear: float
    endYear: float
    label: str
    uri: str    # empty for prehistoric epochs (旧石器 / 新石器)
```

### Examples

```python
from src.core.dynasties import get_cultural_periods_from_year as q

# Single dynasty, no era reuse
[(m.dynasty_id, m.reignTitle) for m in q(1700)]
# → [('清', ''), ('清', '康熙')]

# Parallel polities during 三国
[m.dynasty_id for m in q(250)]
# → ['三国', '吴', '蜀', '魏']

# 隋末群雄并起 — disambiguated 夏(窦建德), no false 上古夏 match
[m.dynasty_id for m in q(619) if m.dynasty_id == '夏']
# → []
[m.dynasty_id for m in q(619) if m.dynasty_id == '夏(窦建德)']
# → ['夏(窦建德)']

# Prehistoric — beginYear=-inf is honest about the open lower bound
[(m.dynasty_id, m.beginYear, m.endYear) for m in q(-100_000)]
# → [('旧石器', -inf, -10000.0)]

# Boundary year is inclusive on BOTH sides — -10000 matches 旧石器 AND 新石器
[m.dynasty_id for m in q(-10000)]
# → ['旧石器', '新石器']

# Far future returns []
q(10_000)  # → []

# BP input
q(250, anno_domini=False) == q(1700)   # BP 250 ≡ AD 1700
# → True
```

### Behavior pins

- **Inclusive endpoints** on both sides: a year exactly at `beginYear` or `endYear` matches.
- **Multiple matches are normal** — dynasty-level summary rows coexist with per-emperor reign rows; parallel polities (三国, 隋末) coexist by definition.
- **NaN-end rows are silently skipped** — 南诏上元 (`784, NaN`) is the deliberately unfilled E-row; we don't claim a match without knowing the end.
- **Prehistoric matches have `uri=""`** — filter `[m for m in matches if m.uri]` to keep only data-backed rows.
- **`ValueError`** on `NaN` / `None` year input — distinguishes "bad input" from "no matches".

---

## Cookbook

### "What dynasty is year X in, ignoring overlapping summary rows?"

```python
specific = [
    m for m in get_cultural_periods_from_year(year)
    if m.reignTitle  # excludes dynasty-summary rows that have no era
]
```

### "Was era X earlier or later than year Y?"

```python
begin, end = get_age_from_cultural_period("永乐", level="period")
verdict = "before" if end < year else "after" if begin > year else "during"
```

### "Convert an archaeological BP age to a candidate dynasty"

```python
matches = get_cultural_periods_from_year(3500, anno_domini=False)
# BP 3500 ≡ AD -1550, returns 商 dynasty
```
