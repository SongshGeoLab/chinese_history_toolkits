# 历史时期参考表

两套 epoch 级查询: `EPOCH_MAP`（curated 朝代聚合）和 `PREHISTORIC_EPOCHS`（史前段 旧石器 / 新石器 的硬编码区间）。

## `EPOCH_MAP`

每条映射 `meta-name → (dynasty_names, year_min, year_max)`。年份范围用来消歧重名（如 三国吴 vs 五代杨吴）。

| Epoch | 包含的 dynasty 字面量 | 年份范围 | 备注 |
|---|---|---|---|
| `汉` | 西汉 / 汉 / 东汉 | -206 .. 220 | 五代后汉（947-950）被年份上界排除 |
| `晋` | 西晋 / 晋 / 东晋 | 265 .. 420 | 五代后晋 被排除 |
| `三国` | 三国 / 魏 / 蜀 / 吴 | 184 .. 280 | 三国吴 而非 五代杨吴 |
| `宋` | 北宋 / 宋 / 南宋 | 960 .. 1279 | 南朝宋 被排除 |
| `五代` | 后梁 / 后唐 / 后晋 / 后汉 / 后周 | 907 .. 960 | |
| `南北朝` | 南北朝 / 南齐 / 南朝宋 / 梁 / 陈 / 北魏 / 东魏 / 西魏 / 北齐 / 北周 | 420 .. 589 | 10 个政权聚合 |
| `上古` | 夏 / 商 / 周 / 西周 / 东周 / 春秋 / 战国 | 无下界 .. -221 | 年份上界排除"夏"在隋末的复用 |

如果 `level="epoch"` 传入的名字既不在此表也不在 `PREHISTORIC_EPOCHS`, 函数会兜底到 `dynasty` 字面量匹配:

```python
get_age_from_cultural_period("唐", level="epoch")
# → (618.0, 907.0)   # 不在 EPOCH_MAP, 退化到 dynasty 匹配
```

## `PREHISTORIC_EPOCHS`

硬编码区间, **不在** dynasty CSV 里。当名字命中时, 函数在读取 DataFrame 之前直接短路返回。

| Epoch | `(begin, end)` AD 年份 |
|---|---|
| `旧石器` (Paleolithic) | `(-inf, -10000.0)` —— 开口下界 |
| `新石器` (Neolithic) | `(-10000.0, -2070.0)` —— 上界为传统"夏朝建立"年份（夏商周断代工程） |

`新石器` 末（`-2070`）与数据中 `夏` 起（`-1989`）之间有 81 年 gap —— 反映夏商周断代工程与上图原始数据的差异, 不是 bug。

### BP 模式下的开口下界

```python
get_age_from_cultural_period("旧石器", level="epoch", anno_domini=False)
# → (inf, 11950.0)
```

AD 的 `-inf` 在 BP 下变成 `+inf`（较老的在前）, 保持 BP 方向不变。

## `level="epoch"` 的解析顺序

```
cp = strip(input)
  ↓
[1] aliases.get(cp, cp)     ← 可选别名重写
  ↓
[2] PREHISTORIC_EPOCHS[cp]? → 直接返回（不读 DataFrame）
  ↓
[3] EPOCH_MAP[cp]?          → 按 dynasty + 年份范围过滤
  ↓
[4] 兜底: dynasty == cp     → 同 dynasty 行的并集
  ↓
[5] 仍为空? → KeyError
```

## 自定义 epoch

如果你需要 `EPOCH_MAP` 没有的聚合, 最干净的做法是用 `time_table` 传一个预过滤的子集:

```python
import pandas as pd
from src.core.dynasties import _load_default_dynasty_table, get_age_from_cultural_period

df = _load_default_dynasty_table()
my_slice = df[df["dynasty"].isin(["北魏", "东魏", "西魏"])]

get_age_from_cultural_period("魏", level="dynasty", time_table=my_slice)
# → 仅这三个魏政权的并集
```

如果你想永久支持新的史前段, 直接编辑 `src/core/dynasties.py` 中的 `PREHISTORIC_EPOCHS`, 并在 `tests/test_dynasties.py::TestPrehistoricEpochs` 里加一个 pin 期望值的测试。
