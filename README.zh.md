<div align="center">

# 🏛️ 中国历史工具集

**把任意年份对应到中国朝代 / 年号 / 历史时期, 反向亦可。**

[中文](README.zh.md) · [English](README.md) · [在线文档](https://songshgeo.github.io/chinese_history_toolkits/zh/)

[![Python](https://img.shields.io/badge/Python-3.10%E2%80%933.13-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Docs](https://img.shields.io/badge/docs-mkdocs--material-purple)](https://songshgeo.github.io/chinese_history_toolkits/zh/)
[![Tests](https://img.shields.io/badge/tests-103%20passing-brightgreen)]()
[![Doc coverage](https://img.shields.io/badge/docstrings-100%25-brightgreen)]()

</div>

---

基于[上海图书馆开放数据平台](https://data.library.sh.cn/dynasty/)（879 条原始记录）构建, 数据清洗过程透明可审计 —— 每一处改动都能追溯到上图原始 URI。轻量、强类型 Python API。

## ✨ 特性

- 🔁 **双向查询** —— 名称 → 起止年份; 年份 → 多个并行政权列表。
- 🪨 **完整时间线** —— 旧石器 / 新石器 史前段一直到清。
- 🧹 **数据已清洗** —— 丢弃 F1 截断重复、合并 F2 拆分跨度、手工补全缺失年份、消歧上古朝代名（`夏(窦建德)` ≠ `夏`）。
- 📜 **可审计** —— [`dynasty_drops.md`](data/dynasties/dynasty_drops.md) 里每一条改动都附上图 URI 链接; 清洗时每改一行抛一条 `RawDataModifiedWarning`。
- 🌐 **支持别名** —— 传入 `aliases={"新石器": {"Neolithic", "Neo"}}` 即可识别外文输入。
- ⚡ **轻量** —— 运行时仅依赖 `pandas`; 数据已在仓库中, 不需要联网。

## 🚀 快速开始

```bash
git clone https://github.com/SongshGeo/chinese_history_toolkits.git
cd chinese_history_toolkits
uv sync --all-extras   # 或: pip install pandas
```

```python
from src.core.dynasties import (
    get_age_from_cultural_period,
    get_cultural_periods_from_year,
)

# 名称 → 年份
get_age_from_cultural_period("康熙")                              # → (1662.0, 1722.0)
get_age_from_cultural_period("唐", level="dynasty")               # → (618.0, 907.0)
get_age_from_cultural_period("新石器", level="epoch")             # → (-10000.0, -2070.0)

# 年份 → 所有匹配政权（多个匹配是常态 —— 三国、隋末等）
[m.dynasty_id for m in get_cultural_periods_from_year(250)]
# → ['三国', '吴', '蜀', '魏']

# BP 纪年（碳十四惯例, 1950 为参考点）
get_age_from_cultural_period("商", level="dynasty", anno_domini=False)
# → (3509.0, 3073.0)

# 外文别名
get_age_from_cultural_period(
    "Neolithic", level="epoch",
    aliases={"新石器": {"Neolithic", "Neo"}},
)
# → (-10000.0, -2070.0)
```

## 🏗️ 架构一览

```
data.library.sh.cn  ─►  scrape  ─►  validate  ─►  clean  ─►  dynasty_clean.csv (854)
                                                              dynasty_drops.md   (审计)
                                                                       │
                                                                       ▼
                                                       src/core/dynasties.py
                                                       (运行时 API, 两个函数)
```

| 阶段 | 脚本 | 产出 |
|---|---|---|
| scrape | `scripts/dynasties/scrape_dynasty.py` | `dynasty_temporal.csv`（879 行） |
| validate | `scripts/dynasties/validate_dynasties.py` | `dynasty_issues.csv`（189 条标记） |
| clean | `scripts/dynasties/clean_dynasties.py` | `dynasty_clean.csv` + `dynasty_drops.md` |

运行时 API 只读 `dynasty_clean.csv`。要改清洗规则, 改脚本、重跑、把 `dynasty_clean.csv` 和 `dynasty_drops.md` 一起提交, diff 就是改动的可审查记录。

## 📚 文档

| | |
|---|---|
| 📖 **[快速开始](docs/doc/quick-start.zh.md)** | 安装 + 第一次查询, 五分钟 |
| 🧹 **[数据流水线](docs/doc/data-pipeline.zh.md)** | scrape → validate → clean 详解 |
| 📚 **[API 参考](docs/doc/api-reference.zh.md)** | 每一个参数, 配实例 |
| 🗺️ **[历史时期参考表](docs/doc/epochs.zh.md)** | `EPOCH_MAP` + `PREHISTORIC_EPOCHS` |

本地构建文档:

```bash
make docs       # http://127.0.0.1:8000 实时预览
make docs-build # 静态构建
```

## 🧪 开发

```bash
make test                       # pytest
pre-commit run --all-files      # black + ruff + flake8 + mypy + interrogate
make tox                        # Python 3.10–3.13 矩阵
```

`tests/test_dynasties.py` 是行为可执行规约 —— 103 个用例, 一个行为族一个 class, 每个用例有 docstring 说明它 pin 什么。

## 📄 数据来源

来源: [上海图书馆开放数据平台 (data.library.sh.cn)](https://data.library.sh.cn/dynasty/)。所有清洗决定记录在 [`data/dynasties/dynasty_drops.md`](data/dynasties/dynasty_drops.md), 每条改动带可点击的源 URI。

## 🤝 贡献

欢迎 PR。请确保:

1. `pre-commit run --all-files` 与 `make test` 都通过。
2. 如果改了清洗规则, 重新生成 `dynasty_clean.csv` 与 `dynasty_drops.md` 并一同提交 —— diff 就是审计记录。
3. 新行为对应新测试用例, 在 `tests/test_dynasties.py` 中添加, 用 docstring 说明它 pin 什么。

## 📜 License

MIT —— 见 [LICENSE](LICENSE)。

## 👤 作者

**SongshGeo** · [GitHub](https://github.com/SongshGeo) · [个人主页](https://cv.songshgeo.com/)
