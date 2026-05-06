# Epochs Reference

The two epoch-level lookups: `EPOCH_MAP` (curated dynasty aggregations) and `PREHISTORIC_EPOCHS` (hand-coded brackets for 旧石器 / 新石器).

## `EPOCH_MAP`

Each entry maps a meta-name to `(dynasty_names, year_min, year_max)`. Year bounds disambiguate name reuse (e.g. 三国吴 vs 五代杨吴).

| Epoch | Dynasty literals included | Year window | Notes |
|---|---|---|---|
| `汉` | 西汉 / 汉 / 东汉 | -206 .. 220 | 后汉 (五代, 947-950) is excluded by the year cap |
| `晋` | 西晋 / 晋 / 东晋 | 265 .. 420 | 后晋 (五代) excluded |
| `三国` | 三国 / 魏 / 蜀 / 吴 | 184 .. 280 | 三国吴 not 五代杨吴 |
| `宋` | 北宋 / 宋 / 南宋 | 960 .. 1279 | 南朝宋 excluded |
| `五代` | 后梁 / 后唐 / 后晋 / 后汉 / 后周 | 907 .. 960 | |
| `南北朝` | 南北朝 / 南齐 / 南朝宋 / 梁 / 陈 / 北魏 / 东魏 / 西魏 / 北齐 / 北周 | 420 .. 589 | 10 polities aggregated |
| `上古` | 夏 / 商 / 周 / 西周 / 东周 / 春秋 / 战国 | None .. -221 | Year cap excludes 隋末 reuse of "夏" |

If you call `level="epoch"` with a name that's NOT in this table and NOT in `PREHISTORIC_EPOCHS`, the function falls back to a plain `dynasty` match.

```python
get_age_from_cultural_period("唐", level="epoch")
# → (618.0, 907.0)   # not in EPOCH_MAP, falls back to dynasty match
```

## `PREHISTORIC_EPOCHS`

Hand-coded brackets, NOT in the dynasty CSV. The function short-circuits before any DataFrame work when the name matches.

| Epoch | `(begin, end)` AD years |
|---|---|
| `旧石器` (Paleolithic) | `(-inf, -10000.0)` — open-ended start |
| `新石器` (Neolithic) | `(-10000.0, -2070.0)` — upper bound is the conventional 夏朝建立 (per 夏商周断代工程) |

The 81-year gap between `新石器` end (`-2070`) and the data's `夏` start (`-1989`) is intentional — it reflects the difference between the 夏商周断代工程 conventional date and the 上图 raw record. Not a bug.

### Open-ended begin in BP mode

```python
get_age_from_cultural_period("旧石器", level="epoch", anno_domini=False)
# → (inf, 11950.0)
```

`-inf` AD becomes `+inf` BP (older first), preserving the BP orientation invariant.

## Resolution order at `level="epoch"`

```
cp = strip(input)
  ↓
[1] aliases.get(cp, cp)     ← optional alias rewrite
  ↓
[2] PREHISTORIC_EPOCHS[cp]? → return early (no DataFrame load)
  ↓
[3] EPOCH_MAP[cp]?          → filter rows by dynasty + year bounds
  ↓
[4] fallback: dynasty == cp → union span over matching rows
  ↓
[5] still empty? → KeyError
```

## Adding your own epoch

If you need a custom aggregation that's not in `EPOCH_MAP`, the cleanest way is a one-line subclass via `time_table`:

```python
import pandas as pd
from chhiskit.core.dynasties import _load_default_dynasty_table, get_age_from_cultural_period

df = _load_default_dynasty_table()
my_slice = df[df["dynasty"].isin(["北魏", "东魏", "西魏"])]

get_age_from_cultural_period("魏", level="dynasty", time_table=my_slice)
# → (begin, end) over just the three 魏 polities you scoped
```

For prehistoric brackets you want to support permanently, edit `PREHISTORIC_EPOCHS` in `src/chhiskit/core/dynasties.py` and add a test pinning the expected span in `tests/test_dynasties.py::TestPrehistoricEpochs`.
