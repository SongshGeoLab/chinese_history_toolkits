# 朝代数据 (data/dynasties/)

## 数据来源

上海图书馆开放数据平台 <https://data.library.sh.cn/dynasty/>，共 **879 条**原始记录。

## 文件清单

| 文件 | 角色 | 由谁生成 |
|---|---|---|
| `dynasties.json` | 原始 RDF/JSON, 每个 URI 一条 | `scripts/dynasties/scrape_dynasty.py` |
| `dynasty_temporal.csv` | 原始扁平化表 (879 行) | `scripts/dynasties/scrape_dynasty.py` |
| `dynasty_issues.csv` | 6 类质量标签 (189 行可疑) | `scripts/dynasties/validate_dynasties.py` |
| **`dynasty_clean.csv`** | **下游唯一权威表 (854 行, 含 `dynasty_id` 列)** | `scripts/dynasties/clean_dynasties.py` |
| `dynasty_drops.md` | 每条改动的逐行审计 (含上图 URI 链接) | `scripts/dynasties/clean_dynasties.py` |

> **下游使用一律读 `dynasty_clean.csv`**，不再读 `dynasty_temporal.csv`。

---

## 流水线

```
data.library.sh.cn  ──scrape──▶  dynasties.json
                                  │
                                  ├─flatten──▶ dynasty_temporal.csv (879)
                                  │            │
                                  │            ├─validate──▶ dynasty_issues.csv (189)
                                  │            │
                                  │            └─clean ─────▶ dynasty_clean.csv  (854)
                                  │                          dynasty_drops.md   (audit)
                                  ▼
                                 (downstream)
```

每个阶段的脚本只依赖 stdlib，无第三方包。

---

## 原始数据质量问题清单 (validate 阶段产出)

`validate_dynasties.py` 把 879 条扫一遍, 标 6 类标签到 `dynasty_issues.csv` 的
`issues` 列。下表是各类的含义和当前分布:

| 标签 | 含义 | 数量 | 性质 |
|---|---|---|---|
| `A:end<begin` | endYear < beginYear (不可能) | 0 | 真错 |
| `B:ancient-name-AD` | 上古朝代名 (夏/商/周/...) 但 begin>0 AD | 5 | 重名歧义 |
| `C:1yr-span` | beginYear == endYear | 141 | 多数为真实短命年号 |
| `D:no-monarch` | 有 reignTitle 但缺 monarchName (post-Qin) | — | 元数据缺失 |
| `E:missing-year` | beginYear 或 endYear 为 null | 5 | 录入不全 |
| `F1:trunc-dup` | 1 年记录与同年号长跨度记录共存 | 7 | **真错 (录入截断)** |
| `F2:split-span` | 同年号被按事件拆为多段 | 43 | 历史拆分, 非错误 |

详细抽样见 `dynasty_issues.csv` 与历史 review 笔记 (本文件 git history)。

---

## 清洗规则 (clean 阶段, 严格执行)

`scripts/dynasties/clean_dynasties.py` 按以下策略把上面 6 类整理成
`dynasty_clean.csv`。**每一处对原始数据的改动都通过
`RawDataModifiedWarning` 抛出**, 并在 `dynasty_drops.md` 留下逐行审计。

| 类别 | 触发标签 | 数量 | 动作 | 理由 |
|---|---|---|---|---|
| F1 截断重复 | `F1:trunc-dup` | 7 | **丢弃** | 同年号长跨度真实条已在数据中, 1-yr 条是上图录入截断 |
| F2 拆分跨度 | `F2:split-span` | 36 → 18 组 | **合并 [min, max]** | 保证年份→单一年号映射, 拆分点 (如 589 隋统一) 在 audit 留痕 |
| E 缺 endYear | `E:missing-year` | 5 (4 补 / 1 留 NaN) | **`KNOWN_ENDS` 表查表补全** | 4 条已知史实可补, 南诏上元未知, 留 NaN 并 warn 用户上图核查 |
| B 重名 | `B:ancient-name-AD` | 4 (F1 已先丢 1) | **新增 `dynasty_id` 列消歧** | 隋末"夏"是真实政权, 不删行; `dynasty_id = 夏(刘虎)` 等 |
| C 1 年年号 | `C:1yr-span` | 141 | **保留, 不动** | 多数为真实短命年号 (东汉殇帝延平 106 等) |
| D 缺 monarchName | `D:no-monarch` | — | **保留, 不动** | 元数据缺失, 不影响年→朝代查询 |

> 注: F2 数量从 validate 阶段的 43 降到 clean 阶段的 36, 是因为其中 7 条 F2-tagged
> 的 1-yr 兄弟已经在 F1 步被丢, F2 组只剩单条时跳过合并 (无需 merge)。

### 重名消歧规则细则

- 默认 `dynasty_id == dynasty`。
- 若 `dynasty ∈ {夏, 商, 周, 西周, 东周, 春秋, 战国}` 且 `beginYear > 0`:
  - `dynasty_id = f"{dynasty}({monarchName or monarch})"`
- 实际触发的 4 条:
  - `夏(刘虎)` (421~428)
  - `夏(窦建德)` (617~618 + 618~621, 同一政权两段年号)
  - `夏(刘黑闼)` (622~623)
- 上古夏 (`-1989~-1559`, 无 monarch) 保留裸 `夏`, 与上述不冲突。

### 已补 endYear 表 (KNOWN_ENDS, 写在脚本顶部)

| URI 尾段 | dynasty / reignTitle / monarchName | begin~原 end | 补到 | 出处 |
|---|---|---|---|---|
| `glvpbcmcui3yfien` | 北齐 / 承光 / 高恒 | 577~? | 577 | 577 年北齐为周所灭 |
| `kuvnpho9wvo4azic` | 渤海 / — / 大諲譔 | 907~? | 926 | 926 年被辽灭 |
| `n3bv41hw1hoihwy8` | 前蜀 / 咸康 / 王衍 | 925~? | 925 | 925 年为后唐所灭 |
| `8uv1kezwk7i1n6kq` | 大理 / 广德 / 段思聪 | 956~? | 968 | 段思聪卒年 (待精确史料核) |
| `4eljzv3hcnl3l1uv` | 南诏 / 上元 / NON | 784~? | **留 NaN** | readme 未提供, 请上图核查 |

---

## `dynasty_clean.csv` 列定义

| 列 | 类型 | 说明 |
|---|---|---|
| `dynasty_id` | str | **消歧后的唯一键**, 默认 = `dynasty`, B 类重名加 `(monarchName)` 后缀 |
| `dynasty` | str | 原始朝代名 (保留, 不改) |
| `reignTitle` | str | 年号 |
| `monarch` | str | 帝号 (如 武帝、太祖) |
| `monarchName` | str | 帝王本名 (如 刘彻、司马炎) |
| `beginYear` | int | 起始公元纪年 (BCE 用负数) |
| `endYear` | int \| empty | 终止年, F2 合并后为 max, E 留 NaN 时为空 |
| `label` | str | 上图原始 label |
| `uri` | str | 上图原始 URI, 用于回溯核查 |

---

## 透明性保证

- **每一处**对原始数据的改动 (drop / merge / fill / disambiguate / still-missing)
  在 `clean_dynasties.py` 运行时通过 `warnings.warn(RawDataModifiedWarning)` 单独抛出,
  消息中带原始 URI, 用户可点击直达上图核对。
- 全量改动列表写入 `dynasty_drops.md`, 每条带 markdown 链接。
- 上游 `scrape_dynasty.py` / `validate_dynasties.py` 不变 — 它们是事实之源,
  清洗只在 clean 这一层叠加。
- 任何想绕过清洗的下游, 仍可直接读 `dynasty_temporal.csv` (原始扁平化数据)。

---

## 用法

### 重跑清洗

```bash
python scripts/dynasties/clean_dynasties.py
```

会:
1. 在 stderr 打出 ~34 条 `RawDataModifiedWarning` (每条改动一行);
2. 重写 `dynasty_clean.csv` 与 `dynasty_drops.md`。

### 在 Python 中消费

```python
import csv
with open("data/dynasties/dynasty_clean.csv", encoding="utf-8") as fh:
    rows = list(csv.DictReader(fh))

# 1900 BCE → 上古夏
[r["dynasty_id"] for r in rows
 if r["beginYear"] and r["endYear"]
    and int(r["beginYear"]) <= -1900 <= int(r["endYear"])]
# → ['夏']

# 619 AD → 隋末窦建德的夏 (与上古夏不冲突)
[r["dynasty_id"] for r in rows
 if r["beginYear"] and r["endYear"]
    and int(r["beginYear"]) <= 619 <= int(r["endYear"])]
# → ['唐', '夏(窦建德)', ...]
```

### 严格模式 (任何改动即报错)

```python
import warnings
from scripts.dynasties.clean_dynasties import RawDataModifiedWarning
warnings.simplefilter("error", RawDataModifiedWarning)
# 之后 import / 调用清洗逻辑会在第一次 warn 时立刻 raise
```

> 命令行 `python -W error::RawDataModifiedWarning ...` 不行 — Python 在 `-W` 解析阶
> 段查不到自定义类。改用 Python 代码内的 `simplefilter('error', ...)`, 或运行后
> grep stderr 检查警告是否符合预期。
