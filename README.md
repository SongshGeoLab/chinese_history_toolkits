<div align="center">

# 🏛️ Chinese History Toolkits

**Map any year to its Chinese dynasty / reign-era / epoch — and back.**

[English](README.md) · [中文](README.zh.md) · [Online Docs](https://songshgeolab.github.io/chinese_history_toolkits/)

[![Python](https://img.shields.io/badge/Python-3.10%E2%80%933.13-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Docs](https://img.shields.io/badge/docs-mkdocs--material-purple)](https://songshgeolab.github.io/chinese_history_toolkits/)
[![Tests](https://img.shields.io/badge/tests-103%20passing-brightgreen)]()
[![Doc coverage](https://img.shields.io/badge/docstrings-100%25-brightgreen)]()

</div>

---

Built on the [Shanghai Library open data platform](https://data.library.sh.cn/dynasty/) (879 raw records), with a transparent cleaning pipeline so every change traces back to the source — and a typed, dependency-light Python API on top.

## ✨ Features

- 🔁 **Two-way lookup** — name → `(begin, end)` years; year → list of all parallel polities.
- 🪨 **Full timeline** — 旧石器 / 新石器 prehistoric brackets through 清.
- 🧹 **Pre-cleaned data** — F1 truncations dropped, F2 split-spans merged, missing endYears hand-filled, ancient-name reuses disambiguated (`夏(窦建德)` ≠ `夏`).
- 📜 **Auditable** — every cleaning decision is one row in [`dynasty_drops.md`](data/dynasties/dynasty_drops.md) with a clickable upstream URI; every modification at clean time emits one `RawDataModifiedWarning`.
- 🌐 **Alias-friendly** — pass `aliases={"新石器": {"Neolithic", "Neo"}}` to accept foreign-language input.
- ⚡ **Lightweight** — only `pandas` at runtime; data ships in the repo, no network needed.

## 🚀 Quickstart

```bash
# From PyPI — distribution name is `chinese_history_toolkits`
pip install chinese_history_toolkits

# Or from source
git clone https://github.com/SongshGeoLab/chinese_history_toolkits.git
cd chinese_history_toolkits
uv sync --all-extras
```

> **Note** — the PyPI distribution name is `chinese_history_toolkits` (verbose), but the **import name is the short acronym `chhiskit`** for daily use.

```python
import chhiskit

# Name → years
chhiskit.get_age_from_cultural_period("康熙")                              # → (1662.0, 1722.0)
chhiskit.get_age_from_cultural_period("唐", level="dynasty")               # → (618.0, 907.0)
chhiskit.get_age_from_cultural_period("新石器", level="epoch")             # → (-10000.0, -2070.0)

# Year → matching polities (multiple are normal — 三国, 隋末, etc.)
[m.dynasty_id for m in chhiskit.get_cultural_periods_from_year(250)]
# → ['三国', '吴', '蜀', '魏']

# BP convention (radiocarbon, 1950 reference)
chhiskit.get_age_from_cultural_period("商", level="dynasty", anno_domini=False)
# → (3509.0, 3073.0)

# Foreign aliases
chhiskit.get_age_from_cultural_period(
    "Neolithic", level="epoch",
    aliases={"新石器": {"Neolithic", "Neo"}},
)
# → (-10000.0, -2070.0)
```

## 🏗️ Architecture at a glance

```
data.library.sh.cn  ─►  scrape  ─►  validate  ─►  clean  ─►  dynasty_clean.csv (854)
                                                              dynasty_drops.md   (audit)
                                                                       │
                                                                       ▼
                                                       src/chhiskit/core/dynasties.py
                                                       (runtime API, two functions)
```

| Stage | Script | Output |
|---|---|---|
| scrape | `scripts/dynasties/scrape_dynasty.py` | `dynasty_temporal.csv` (879 rows) |
| validate | `scripts/dynasties/validate_dynasties.py` | `dynasty_issues.csv` (189 flagged) |
| clean | `scripts/dynasties/clean_dynasties.py` | `dynasty_clean.csv` + `dynasty_drops.md` |

The runtime API only reads `dynasty_clean.csv`. To change a cleaning rule, edit the script and re-run — the diff in `dynasty_clean.csv` and `dynasty_drops.md` makes the change reviewable.

## 📚 Documentation

| | |
|---|---|
| 📖 **[Quick Start](docs/doc/quick-start.md)** | Install + first lookup, 5 minutes |
| 🧹 **[Data Pipeline](docs/doc/data-pipeline.md)** | Scrape → validate → clean explained |
| 📚 **[API Reference](docs/doc/api-reference.md)** | Every parameter, with worked examples |
| 🗺️ **[Epochs Reference](docs/doc/epochs.md)** | `EPOCH_MAP` + `PREHISTORIC_EPOCHS` |

Build the site locally:

```bash
make docs       # serve at http://127.0.0.1:8000
make docs-build # static build
```

## 🧪 Development

```bash
make test                       # pytest
pre-commit run --all-files      # black + ruff + flake8 + mypy + interrogate
make tox                        # Python 3.10–3.13 matrix
```

The test file `tests/test_dynasties.py` is the executable spec — 103 cases organized into one class per behavior cluster, each with a docstring explaining what it pins.

## 📄 Data attribution

Source: [上海图书馆开放数据平台 (data.library.sh.cn)](https://data.library.sh.cn/dynasty/). All cleaning decisions are documented in [`data/dynasties/dynasty_drops.md`](data/dynasties/dynasty_drops.md) with a clickable URI back to the source for each modified row.

## 🤝 Contributing

PRs welcome. Please:

1. Run `pre-commit run --all-files` and `make test` (must pass).
2. If you change cleaning rules, regenerate `dynasty_clean.csv` and `dynasty_drops.md` and commit both — the diff is your change's audit trail.
3. New behavior → new test in `tests/test_dynasties.py` with a docstring describing what it pins.

## 📜 License

MIT — see [LICENSE](LICENSE).

## 👤 Author

**SongshGeo** · [GitHub](https://github.com/SongshGeo) · [Website](https://cv.songshgeo.com/)
