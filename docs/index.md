# Chinese History Toolkits

Map any year to its Chinese dynasty / reign-era / epoch — and back. Built on the [Shanghai Library open data](https://data.library.sh.cn/dynasty/), with a transparent cleaning pipeline so every change traces back to the source.

!!! info "What you get"
    - 🏛️ **Two-way lookup** — name → `(begin, end)` years; year → list of parallel polities.
    - 🪨 **Full timeline** — 旧石器 / 新石器 prehistoric brackets through 清.
    - ✨ **Pre-cleaned data** — F1 truncations dropped, F2 split-spans merged, missing years hand-filled, ancient names disambiguated (`夏(窦建德)` ≠ `夏`).
    - 📜 **Auditable** — every cleaning decision traces back to a 上图 URI in `dynasty_drops.md`.
    - 🌐 **Alias-friendly** — pass an `aliases` map so `Neolithic` / `Kangxi` / `Tang` resolve correctly.

## Two-minute taste

```python
from src.core.dynasties import (
    get_age_from_cultural_period,
    get_cultural_periods_from_year,
)

# Name → years
get_age_from_cultural_period("康熙", level="period")
# → (1662.0, 1722.0)

get_age_from_cultural_period("唐", level="dynasty")
# → (618.0, 907.0)

get_age_from_cultural_period("新石器", level="epoch")
# → (-10000.0, -2070.0)

# Year → all matching polities (parallel during 三国 / 隋末 / etc.)
[m.dynasty_id for m in get_cultural_periods_from_year(250)]
# → ['三国', '吴', '蜀', '魏']

[m.dynasty_id for m in get_cultural_periods_from_year(619)]
# → ['唐', '夏(窦建德)', '梁', '楚', ...]   # 隋末 — many parallel polities

# BP convention (radiocarbon, 1950 reference)
get_age_from_cultural_period("商", level="dynasty", anno_domini=False)
# → (3509.0, 3073.0)   # older first, in BP

# Foreign-language aliases
get_age_from_cultural_period(
    "Neolithic", level="epoch",
    aliases={"新石器": {"Neolithic", "Neo"}},
)
# → (-10000.0, -2070.0)
```

## Where to next

- 📖 [Quick Start](doc/quick-start.md) — install & run your first lookup
- 🧹 [Data Pipeline](doc/data-pipeline.md) — how raw 上图 data becomes `dynasty_clean.csv`
- 📚 [API Reference](doc/api-reference.md) — every parameter, with worked examples
- 🗺️ [Epochs Reference](doc/epochs.md) — `EPOCH_MAP` + `PREHISTORIC_EPOCHS`

## Data lineage

```
data.library.sh.cn  ─►  dynasty_temporal.csv (879)
                              │
                              ├─► dynasty_issues.csv (189 flagged)
                              │
                              └─► dynasty_clean.csv (854) ◄── what you query
                                  dynasty_drops.md (audit)
```
