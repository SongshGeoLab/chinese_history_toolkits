# API 参考

两个函数, 都在 `chhiskit.core.dynasties`。默认都消费 `dynasty_clean.csv`; 传 `time_table` 可覆盖。

---

## `get_age_from_cultural_period`

把文化期名称映射到 `(begin, end)` 年份。

### 函数签名

```python
def get_age_from_cultural_period(
    cultural_period: str,
    level: Literal["period", "dynasty", "epoch"] = "period",
    *,
    anno_domini: bool = True,
    time_table: pd.DataFrame | None = None,
    aliases: Mapping[str, Iterable[str]] | None = None,
) -> tuple[float, float]:
```

### 参数

| 参数 | 说明 |
|---|---|
| `cultural_period` | 待解析的名称。空白会被 strip; 如果传了 `aliases`, 先做别名重写 |
| `level` | `"period"`（按年号匹配）/ `"dynasty"`（按 dynasty 字面量）/ `"epoch"`（curated 聚合 + 史前段） |
| `anno_domini` | `True`（默认）返回 AD/BCE; `False` 返回相对 1950 的 BP（碳十四惯例） |
| `time_table` | 可选 `DataFrame`, schema 同 `dynasty_clean.csv`。年份列可以是字符串 —— 函数会强转。**`_KNOWN_BAD_URIS` 不会过滤用户传入的表** |
| `aliases` | 可选 `{canonical: {alias, ...}}` 映射。详见 [Aliases](#aliases) |

### 返回

`(begin, end)` 浮点二元组。AD 模式: `begin <= end`; BP 模式: `begin >= end`（较老的在前）。

### Level 详解

#### `level="period"` —— 按年号匹配

```python
get_age_from_cultural_period("康熙")              # → (1662.0, 1722.0)
get_age_from_cultural_period("元平")              # → (-74.0, -74.0)   单年 BCE
get_age_from_cultural_period("清康熙")            # → (1662.0, 1722.0) label 兜底
```

`reignTitle` 找不到时, 函数会回退到 `label` 列（如 `"清康熙"`）。如果同一 `reignTitle` 被 ≥2 个不同帝王使用（比如"建平"被 7 位帝王用过）, 抛 `AmbiguousCulturalPeriodError`:

```python
get_age_from_cultural_period("建平")
# AmbiguousCulturalPeriodError: reignTitle='建平' matches 7 different rulers
```

#### `level="dynasty"` —— 按朝代字面量匹配

```python
get_age_from_cultural_period("唐", level="dynasty")    # → (618.0, 907.0)
get_age_from_cultural_period("商", level="dynasty")    # → (-1559.0, -1123.0)
```

返回所有同 `dynasty` 行的并集。**注意**: 函数匹配的是原始 `dynasty` 字段, 不是 `dynasty_id`, 因此 `"夏"` 返回 `(-1989, 623)` —— 上古夏与隋末夏共享字面量。要只取上古, 用 `level="epoch"` 配 `"上古"`。

#### `level="epoch"` —— curated 聚合

```python
get_age_from_cultural_period("汉", level="epoch")      # → (-206.0, 220.0)
get_age_from_cultural_period("三国", level="epoch")    # → (220.0, 280.0)
get_age_from_cultural_period("上古", level="epoch")    # → (-1989.0, -221.0)
get_age_from_cultural_period("新石器", level="epoch")  # → (-10000.0, -2070.0)
get_age_from_cultural_period("旧石器", level="epoch")  # → (-inf, -10000.0)
```

解析顺序:

1. `PREHISTORIC_EPOCHS` 中的史前段（旧石器 / 新石器）—— 短路, 不读 DataFrame
2. `EPOCH_MAP` 中的聚合（汉 / 晋 / 三国 / 宋 / 五代 / 南北朝 / 上古）—— 按 `dynasty in [...]` 加年份范围过滤
3. 兜底: 退化为 `level="dynasty"` 匹配

完整表见 [历史时期参考表](epochs.md)。

### `anno_domini=False`: BP 模式

```python
get_age_from_cultural_period("商", level="dynasty", anno_domini=False)
# → (3509.0, 3073.0)   # BP = 1950 - AD; 较老的在前

get_age_from_cultural_period("旧石器", level="epoch", anno_domini=False)
# → (inf, 11950.0)     # AD 的 -inf 在 BP 下变成 +inf
```

### `aliases`

在所有匹配之前, 把 `cultural_period` 改写成 canonical 名。适用于:

- 外文输入（`"Tang"` → `"唐"`）
- 简写（`"Neo"` → `"新石器"`）
- 旧拼音（Wade-Giles → 汉语拼音 → 汉字）

```python
ALIASES = {
    "新石器": {"Neolithic", "Neo"},
    "旧石器": {"Paleolithic"},
    "唐":   {"Tang", "T'ang"},
    "康熙": {"Kangxi", "K'ang-hsi"},
}

get_age_from_cultural_period("Neo", level="epoch", aliases=ALIASES)
# → (-10000.0, -2070.0)
```

解析规则:

| 输入 | 行为 |
|---|---|
| `aliases=None` 或 `{}` | no-op, 等价于不传 |
| `cp` 是 canonical key | 不改写, 走 canonical 查询路径 |
| `cp` 命中某一 canonical 的 alias 集合 | 改写为该 canonical |
| `cp` 同时命中 ≥2 个 canonical 的 alias | `ValueError`, 列出所有候选 |
| `cp` 不在 canonical 也不在任何 alias | 透传, 由下游报 `KeyError` |

alias 的 value 可以是任意 iterable (`set` / `frozenset` / `tuple` / `list`)。

### 错误

| 异常 | 触发 |
|---|---|
| `KeyError` | 名称（别名解析后）找不到匹配 |
| `AmbiguousCulturalPeriodError`（继承 `ValueError`） | `level="period"` 且年号对应 ≥2 个帝王 |
| `ValueError` | 输入为空 / level 非法 / 别名映射到 ≥2 canonical / 匹配行年份全 NaN |

---

## `get_cultural_periods_from_year`

把年份映射到所有覆盖它的朝代 / 年号 / 史前段。

### 函数签名

```python
def get_cultural_periods_from_year(
    year: float,
    *,
    anno_domini: bool = True,
    time_table: pd.DataFrame | None = None,
) -> list[CulturalPeriodMatch]:
```

### 参数

| 参数 | 说明 |
|---|---|
| `year` | 查询年份。默认 AD/BCE（公元前为负）; `anno_domini=False` 时按 BP-1950 解释, 内部先转成 AD 再匹配 |
| `anno_domini` | 怎么解释输入 `year`。返回的 `beginYear` / `endYear` 始终是 AD/BCE 形式 |
| `time_table` | 可选 DataFrame, schema 同 `dynasty_clean.csv` |

### 返回

`list[CulturalPeriodMatch]`, 按 `(beginYear, endYear)` 升序排序。无匹配返回 `[]`。

`CulturalPeriodMatch` 是一个 NamedTuple:

```python
class CulturalPeriodMatch(NamedTuple):
    dynasty_id: str
    dynasty: str
    reignTitle: str
    monarch: str
    monarchName: str
    beginYear: float
    endYear: float
    label: str
    uri: str    # 史前段（旧石器 / 新石器）此字段为空
```

### 实例

```python
from chhiskit.core.dynasties import get_cultural_periods_from_year as q

# 单一朝代, 年号无重用
[(m.dynasty_id, m.reignTitle) for m in q(1700)]
# → [('清', ''), ('清', '康熙')]

# 三国时期的并行政权
[m.dynasty_id for m in q(250)]
# → ['三国', '吴', '蜀', '魚']

# 隋末群雄并起 —— 消歧的 夏(窦建德), 没有错配上古夏
[m.dynasty_id for m in q(619) if m.dynasty_id == '夏']
# → []
[m.dynasty_id for m in q(619) if m.dynasty_id == '夏(窦建德)']
# → ['夏(窦建德)']

# 史前 —— beginYear=-inf 老老实实表达开口下界
[(m.dynasty_id, m.beginYear, m.endYear) for m in q(-100_000)]
# → [('旧石器', -inf, -10000.0)]

# 边界年份两端都包含 —— -10000 同时命中 旧石器 和 新石器
[m.dynasty_id for m in q(-10000)]
# → ['旧石器', '新石器']

# 远未来返回 []
q(10_000)  # → []

# BP 输入
q(250, anno_domini=False) == q(1700)   # BP 250 ≡ AD 1700
# → True
```

### 行为约定

- **闭区间**: 年份恰好等于 `beginYear` 或 `endYear` 也算命中
- **多匹配是常态** —— dynasty 级 summary 行与 emperor 级 reign 行共存; 三国 / 隋末等天然多政权并行
- **NaN-end 行被静默跳过** —— 南诏上元（`784, NaN`）是有意未补的 E 类行; 没有可靠 end 就不声称匹配
- **史前段 `uri=""`** —— 用 `[m for m in matches if m.uri]` 过出仅数据驱动的匹配
- **`NaN` / `None` 输入抛 `ValueError`** —— 把"输入错误"和"无匹配"分开

---

## 食谱

### "year X 是哪个朝代, 不要 dynasty 级 summary 行"

```python
specific = [
    m for m in get_cultural_periods_from_year(year)
    if m.reignTitle  # 排除没有年号的 dynasty-summary 行
]
```

### "X 年号是早于还是晚于 Y 年？"

```python
begin, end = get_age_from_cultural_period("永乐", level="period")
verdict = "早于" if end < year else "晚于" if begin > year else "包含"
```

### "把考古 BP 年龄转换成候选朝代"

```python
matches = get_cultural_periods_from_year(3500, anno_domini=False)
# BP 3500 ≡ AD -1550, 返回 商朝
```
