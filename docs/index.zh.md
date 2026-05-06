# 中国历史工具集

把任意年份对应到中国朝代 / 年号 / 历史时期, 反向亦可。基于[上海图书馆开放数据平台](https://data.library.sh.cn/dynasty/), 数据清洗过程透明可审计 —— 每一处改动都能追溯到上图原始 URI。

!!! info "你能用它做什么"
    - 🏛️ **双向查询** —— 名称 → 起止年份; 年份 → 多个并行政权列表
    - 🪨 **完整时间线** —— 旧石器 / 新石器 史前段一直到清
    - ✨ **数据已清洗** —— 丢弃 F1 截断重复、合并 F2 拆分跨度、手工补全缺失年份、消歧重名（`夏(窦建德)` ≠ `夏`）
    - 📜 **可审计** —— `dynasty_drops.md` 里每一条改动都带上图 URI 链接
    - 🌐 **支持别名** —— 传入 `aliases` 表后, `Neolithic` / `Kangxi` / `Tang` 等也能解析

## 两分钟上手

```python
import chhiskit

# 名称 → 年份
chhiskit.get_age_from_cultural_period("康熙", level="period")
# → (1662.0, 1722.0)

chhiskit.get_age_from_cultural_period("唐", level="dynasty")
# → (618.0, 907.0)

chhiskit.get_age_from_cultural_period("新石器", level="epoch")
# → (-10000.0, -2070.0)

# 年份 → 所有匹配的政权（三国 / 隋末等会有多个并行）
[m.dynasty_id for m in chhiskit.get_cultural_periods_from_year(250)]
# → ['三国', '吴', '蜀', '魏']

[m.dynasty_id for m in chhiskit.get_cultural_periods_from_year(619)]
# → ['唐', '夏(窦建德)', '梁', '楚', ...]   # 隋末群雄并起

# BP 纪年（碳十四惯例, 1950 为参考点）
chhiskit.get_age_from_cultural_period("商", level="dynasty", anno_domini=False)
# → (3509.0, 3073.0)   # BP 模式下 begin 较老在前

# 外文别名
chhiskit.get_age_from_cultural_period(
    "Neolithic", level="epoch",
    aliases={"新石器": {"Neolithic", "Neo"}},
)
# → (-10000.0, -2070.0)
```

## 下一步

- 📖 [快速开始](doc/quick-start.md) —— 安装并跑通第一个查询
- 🧹 [数据流水线](doc/data-pipeline.md) —— 上图原始数据如何变成 `dynasty_clean.csv`
- 📚 [API 参考](doc/api-reference.md) —— 两个函数每一个参数 + 实例
- 🗺️ [历史时期参考表](doc/epochs.md) —— `EPOCH_MAP` + `PREHISTORIC_EPOCHS`

## 数据血缘

```
data.library.sh.cn  ─►  dynasty_temporal.csv (879)
                              │
                              ├─► dynasty_issues.csv (189 条标记)
                              │
                              └─► dynasty_clean.csv (854) ◄── 运行时查询的对象
                                  dynasty_drops.md (审计)
```
