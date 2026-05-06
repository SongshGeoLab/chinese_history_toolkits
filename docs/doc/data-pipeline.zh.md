# 数据流水线

上图原始数据如何变成你运行时查询的 `dynasty_clean.csv` —— 整个过程透明可重放。

## 三段式

```
┌─ scrape ──────────────────────────────────────────────────────┐
│ scripts/dynasties/scrape_dynasty.py                            │
│   data.library.sh.cn  →  dynasties.json  →  dynasty_temporal.csv│
└────────────────────────────────────────────────────────────────┘
                            │ 879 行 raw
┌─ validate ────────────────▼───────────────────────────────────┐
│ scripts/dynasties/validate_dynasties.py                        │
│   标记 189 条可疑行  →  dynasty_issues.csv                      │
└────────────────────────────────────────────────────────────────┘
                            │ A / B / C / D / E / F1 / F2
┌─ clean ───────────────────▼───────────────────────────────────┐
│ scripts/dynasties/clean_dynasties.py                           │
│   按 6 类规则处理, 每改一行抛一条 warning                        │
│   →  dynasty_clean.csv  (854 行; 运行时只读它)                  │
│   →  dynasty_drops.md   (逐行审计, URI 可点击直达上图)          │
└────────────────────────────────────────────────────────────────┘
```

## validate 阶段标的 6 类问题

| 标签 | 含义 | 数量 | 性质 |
|---|---|---|---|
| `A:end<begin` | endYear < beginYear（不可能） | 0 | 真错 |
| `B:ancient-name-AD` | dynasty 在 {夏 / 商 / 周 / …} 但 begin > 0 AD | 5 | 重名歧义 |
| `C:1yr-span` | begin == end | 141 | 多数为真实短命年号 |
| `D:no-monarch` | 有 reignTitle 但缺 monarchName | — | 元数据缺失 |
| `E:missing-year` | begin 或 end 为 null | 5 | 录入不全 |
| `F1:trunc-dup` | 1 年记录与同年号长跨度记录共存 | 7 | **录入截断, 真错** |
| `F2:split-span` | 同年号被按事件拆为多段 | 43 | 历史拆分, 非错误 |

## clean 阶段对每类的处理

| 类别 | 动作 | 理由 |
|---|---|---|
| **F1** 截断重复 | **丢弃 7 条** | 长跨度真实条已在数据中, 1 年条是上图录入截断 |
| **F2** 拆分跨度 | **合并为 `[min(begin), max(end)]`**（36 条 → 18 组） | 保证一年 → 单一年号查询。原始拆分语义在审计文档里留痕 |
| **E** 缺 endYear | **`KNOWN_ENDS` 表查表补 4 条**, 1 条（南诏上元）保留 NaN | 4 条已知史实有据可依; 南诏上元无可靠出处 —— 留 NaN 并 warn 用户上图核查 |
| **B** 上古重名 | **`dynasty_id` 加 `(monarchName)` 后缀** | 隋末"夏"是真实政权, 不能丢; 改 dynasty_id 消歧。原 `dynasty` 字段保留 |
| **C** 1 年年号 | **保留** | 多数是真实短命年号（东汉殇帝刘隆延平 106-106） |
| **D** 缺 monarchName | **保留** | 元数据缺失, 不影响年 ↔ 朝代查询 |

## 透明性: 警告 + 审计文档

每一处改动在两个地方可见:

**1. stderr** —— 每行一条 `RawDataModifiedWarning`, 带原始 URI:

```
RawDataModifiedWarning: DROP F1 截断重复: 晋·太康(司马炎) 280~280
  <http://data.library.sh.cn/authority/temporal/fo3y5vgrykmpbupv>
  (已被同年号长跨度条 280~289 覆盖)
```

**2. `data/dynasties/dynasty_drops.md`** —— 每行一条改动, URI 可点击直达上图:

| dynasty | reignTitle | dropped | kept | URI |
|---|---|---|---|---|
| 晋 | 太康 | 280~280 | 280~289 | [fo3y5vgrykmpbupv](http://data.library.sh.cn/authority/temporal/fo3y5vgrykmpbupv) |

如果你对某条清洗决定有异议, 点 URI 链接到上图核对原始记录。

## 重新生成 clean.csv

```bash
python scripts/dynasties/clean_dynasties.py
# stderr 摘要:
# [clean_dynasties] 879 raw → 854 clean | warnings: 34
#   wrote data/dynasties/dynasty_clean.csv
#   wrote data/dynasties/dynasty_drops.md
```

脚本只读 `dynasty_temporal.csv` 与 `dynasty_issues.csv`, **不会**重新抓取。要刷新源数据, 请先跑 `scrape_dynasty.py` 与 `validate_dynasties.py`。

## CI 中的严格模式

如果未来某次清洗"意外"改了比审计文档列出的更多行, CI 应该报错。可以用 Python `warnings` 过滤器包一层:

```python
import warnings
from scripts.dynasties.clean_dynasties import RawDataModifiedWarning, main

with warnings.catch_warnings(record=True) as wlist:
    warnings.simplefilter("always", RawDataModifiedWarning)
    main()
assert len(wlist) == 34, f"unexpected modifications: {len(wlist)}"
```

## 运行时信任的边界

`src/chhiskit/core/dynasties.py` 里的运行时 API **只**读 `dynasty_clean.csv`, 不在运行时重新校验、重新清洗。这是设计决定 —— 要改规则, 改脚本、重跑、把 `dynasty_clean.csv` 与 `dynasty_drops.md` 一起提交, diff 就成了改动的可审查记录。
