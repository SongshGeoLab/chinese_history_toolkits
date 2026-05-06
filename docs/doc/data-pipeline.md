# Data Pipeline

How raw 上海图书馆 data becomes the `dynasty_clean.csv` you query at runtime — and how to regenerate it transparently.

## The three stages

```
┌─ scrape ──────────────────────────────────────────────────────┐
│ scripts/dynasties/scrape_dynasty.py                            │
│   data.library.sh.cn  →  dynasties.json  →  dynasty_temporal.csv│
└────────────────────────────────────────────────────────────────┘
                            │ 879 rows, raw
┌─ validate ────────────────▼───────────────────────────────────┐
│ scripts/dynasties/validate_dynasties.py                        │
│   tags 189 suspicious rows  →  dynasty_issues.csv              │
└────────────────────────────────────────────────────────────────┘
                            │ A / B / C / D / E / F1 / F2
┌─ clean ───────────────────▼───────────────────────────────────┐
│ scripts/dynasties/clean_dynasties.py                           │
│   applies six rules, emits one warning per modification        │
│   →  dynasty_clean.csv  (854 rows; what runtime reads)         │
│   →  dynasty_drops.md   (per-row audit with clickable URIs)    │
└────────────────────────────────────────────────────────────────┘
```

## Issue categories from the validator

| Tag | Meaning | Count | Severity |
|---|---|---|---|
| `A:end<begin` | endYear < beginYear (impossible) | 0 | true error |
| `B:ancient-name-AD` | dynasty in {夏 / 商 / 周 / …} but begin > 0 AD | 5 | name collision |
| `C:1yr-span` | begin == end | 141 | mostly real 短命年号 |
| `D:no-monarch` | reignTitle without monarchName | — | metadata gap |
| `E:missing-year` | begin or end is null | 5 | record incomplete |
| `F1:trunc-dup` | 1-year row + longer-span twin | 7 | **upstream truncation** |
| `F2:split-span` | era split across multiple rows | 43 | upstream event-based split |

## What the cleaner does to each

| Category | Action | Rationale |
|---|---|---|
| **F1** truncated dups | **Drop 7 rows** | The longer-span sibling is already in the data; the 1-year row is an upstream artifact. |
| **F2** split-spans | **Merge to `[min(begin), max(end)]`** (36 rows → 18 groups) | Guarantees `year → single 年号`. Original split semantics preserved in the audit doc. |
| **E** missing-end | **Hand-fill 4 from `KNOWN_ENDS`**, leave 1 (南诏上元) as NaN | 4 have documented historical endpoints; 南诏上元 has no reliable source — left NaN with a loud warning to verify on 上图. |
| **B** ancient-name reuse | **Rewrite `dynasty_id`** to `{dynasty}({monarchName})` | Disambiguates 上古夏 from 隋末 夏(窦建德 / 刘虎 / 刘黑闼). Raw `dynasty` field preserved. |
| **C** 1-year eras | **Keep as-is** | Most are real 短命年号 (东汉殇帝刘隆延平 106-106). |
| **D** missing monarchName | **Keep as-is** | Metadata gap; doesn't affect year ↔ dynasty queries. |

## Transparency: warnings + audit doc

Every modification is observable in two places:

**1. stderr** — one `RawDataModifiedWarning` per row, with the upstream URI:

```
RawDataModifiedWarning: DROP F1 截断重复: 晋·太康(司马炎) 280~280
  <http://data.library.sh.cn/authority/temporal/fo3y5vgrykmpbupv>
  (covered by long-span sibling 280~289)
```

**2. `data/dynasties/dynasty_drops.md`** — one row per modification with a clickable 上图 URI:

| dynasty | reignTitle | dropped | kept | URI |
|---|---|---|---|---|
| 晋 | 太康 | 280~280 | 280~289 | [fo3y5vgrykmpbupv](http://data.library.sh.cn/authority/temporal/fo3y5vgrykmpbupv) |

If you disagree with any cleaning decision, click the URI to inspect the upstream record.

## Regenerating the cleaned CSV

```bash
python scripts/dynasties/clean_dynasties.py
# stderr summary:
# [clean_dynasties] 879 raw → 854 clean | warnings: 34
#   wrote data/dynasties/dynasty_clean.csv
#   wrote data/dynasties/dynasty_drops.md
```

The script only reads `dynasty_temporal.csv` and `dynasty_issues.csv`. It does NOT re-scrape — to refresh the source data, run `scrape_dynasty.py` followed by `validate_dynasties.py` first.

## Strict mode for CI

If a future cleanup unexpectedly modifies *more* rows than the audit doc lists, you'll want CI to fail. Use Python's `warnings` filter inside a small wrapper:

```python
import warnings
from scripts.dynasties.clean_dynasties import RawDataModifiedWarning, main

# Allow only the documented modifications by counting warnings:
with warnings.catch_warnings(record=True) as wlist:
    warnings.simplefilter("always", RawDataModifiedWarning)
    main()
assert len(wlist) == 34, f"unexpected modifications: {len(wlist)}"
```

## What the runtime trusts

The runtime API in `src/chhiskit/core/dynasties.py` reads **only** `dynasty_clean.csv`. It never re-validates or re-cleans. This is intentional — to change a rule, change the script and re-run it, then commit both `dynasty_clean.csv` and `dynasty_drops.md`. The diff makes the change reviewable.
