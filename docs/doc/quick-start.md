# Quick Start

Your first dynasty lookup in five minutes.

## 1. Install

```bash
git clone https://github.com/SongshGeo/chinese_history_toolkits.git
cd chinese_history_toolkits

# uv (recommended)
uv sync --all-extras

# or pip
pip install pandas
```

`pandas` is the only runtime dependency. The data lives in the repo (already cleaned), so no network call is needed at runtime.

## 2. Verify the data is there

```bash
ls data/dynasties/
# dynasties.json  dynasty_clean.csv  dynasty_drops.md
# dynasty_issues.csv  dynasty_temporal.csv  readme.md
```

`dynasty_clean.csv` is the only file the runtime API reads. The rest is audit material — `dynasty_drops.md` documents every cleaning decision with a clickable 上图 URI.

## 3. Your first lookup

```python
from src.core.dynasties import get_age_from_cultural_period

# By 年号 (reign era) — the default level
get_age_from_cultural_period("康熙")
# → (1662.0, 1722.0)
```

The result is `(begin_year, end_year)` in AD/BCE form (BCE is negative).

## 4. Choose the right level

```python
# Reign-era query (single 年号)
get_age_from_cultural_period("贞观", level="period")
# → (627.0, 649.0)

# Dynasty-level query
get_age_from_cultural_period("唐", level="dynasty")
# → (618.0, 907.0)

# Meta-epoch query (汉, 三国, 五代, 上古, 新石器, ...)
get_age_from_cultural_period("三国", level="epoch")
# → (220.0, 280.0)
```

!!! tip "Three levels, one function"
    Levels are not strictly nested — `period` matches by `reignTitle`, `dynasty` by the literal `dynasty` column, `epoch` by the curated [`EPOCH_MAP`](epochs.md). Pick the one whose semantics match your input.

## 5. Reverse lookup: what was happening in year X?

```python
from src.core.dynasties import get_cultural_periods_from_year

matches = get_cultural_periods_from_year(250)
for m in matches:
    print(m.dynasty_id, m.reignTitle, m.beginYear, m.endYear)
# 三国        220.0  280.0
# 吴   赤乌  238.0  251.0
# 蜀   延熙  238.0  257.0
# 魏   嘉平  249.0  254.0
```

Multiple parallel polities are normal — 三国, 南北朝, 五代, 隋末唐初 all routinely overlap.

## 6. Need foreign names?

```python
ALIASES = {
    "新石器": {"Neolithic", "Neo"},
    "唐":   {"Tang"},
    "康熙": {"Kangxi"},
}

get_age_from_cultural_period("Tang", level="dynasty", aliases=ALIASES)
# → (618.0, 907.0)
```

See the [API Reference](api-reference.md) for full parameter behavior, BP-mode conversion, custom timetables, and error semantics.
