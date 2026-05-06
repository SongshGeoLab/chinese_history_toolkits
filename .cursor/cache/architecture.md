<!--
Purpose:
- Record the project's high-level architecture (modules, boundaries, and key flows) as a quick reference.

Audience:
- Contributors and reviewers who need context before making changes.

Usage:
- Update this file when architectural decisions or major module interactions change.
-->

# Architecture

## Three-stage pipeline

```
data.library.sh.cn  (上海图书馆开放数据平台)
        │
        ▼  scripts/dynasties/scrape_dynasty.py
        │
   data/dynasties/dynasties.json          (raw RDF/JSON, 879 URIs)
   data/dynasties/dynasty_temporal.csv    (flattened, 879 rows)
        │
        ▼  scripts/dynasties/validate_dynasties.py
        │
   data/dynasties/dynasty_issues.csv      (189 flagged rows, 6 categories)
        │
        ▼  scripts/dynasties/clean_dynasties.py
        │   - drops 7 F1 truncated dups
        │   - merges 36→18 F2 split-spans
        │   - hand-fills 4 of 5 E missing-end rows
        │   - adds dynasty_id (disambiguates 夏 vs 夏(窦建德) ...)
        │   - emits one warnings.warn(RawDataModifiedWarning) per change
        │
   data/dynasties/dynasty_clean.csv       (854 rows; downstream-authoritative)
   data/dynasties/dynasty_drops.md        (per-row audit with 上图 URI links)
        │
        ▼  src/chhiskit/core/dynasties.py  (runtime, reads only dynasty_clean.csv)
        │
   get_age_from_cultural_period(cp, level, anno_domini, time_table, aliases)
   get_cultural_periods_from_year(year, anno_domini, time_table)
```

## Module boundaries

| Module | Owns | Does NOT own |
|---|---|---|
| `scripts/dynasties/` | Build-time: HTTP, validation, cleaning, audit-doc generation | Runtime queries |
| `src/chhiskit/core/dynasties.py` | Runtime API. Reads `dynasty_clean.csv` only | Cleaning rules, validation logic |
| `data/dynasties/` | Versioned artifacts (raw + clean + audit) | Logic |
| `tests/test_dynasties.py` | API behavior contracts pinned to `dynasty_clean.csv` | Pipeline-stage tests |

Cleaning rules live in `clean_dynasties.py`; the API never re-validates or re-cleans at runtime — it trusts the CSV. To change a rule, change the script and re-run it.

## Key invariants

- `dynasty_clean.csv` is the **only** source the runtime API reads (default loader).
- Every row carries a stable `uri` traceable back to `data.library.sh.cn`.
- `dynasty_id` is the disambiguated key (e.g. `夏(窦建德)` for the 隋末 polity vs bare `夏` for 上古夏); raw `dynasty` is preserved alongside.
- Prehistoric epochs (`旧石器`, `新石器`) are NOT rows in the CSV — they live in `PREHISTORIC_EPOCHS` and short-circuit before any DataFrame work.
- `EPOCH_MAP` aggregates dynasty-level rows into meta-epochs (`汉`, `三国`, `南北朝`, `上古`, …) with optional year bounds for disambiguation.
- All cleaning side-effects are observable: every modified row → one `RawDataModifiedWarning` to stderr **and** one row in `dynasty_drops.md`.
