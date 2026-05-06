# 快速开始

五分钟跑通第一个朝代查询。

## 1. 安装

```bash
git clone https://github.com/SongshGeo/chinese_history_toolkits.git
cd chinese_history_toolkits

# uv（推荐）
uv sync --all-extras

# 或者 pip
pip install pandas
```

运行时唯一依赖是 `pandas`。数据已在仓库里（已清洗）, 运行时不需要联网。

## 2. 检查数据是否就位

```bash
ls data/dynasties/
# dynasties.json  dynasty_clean.csv  dynasty_drops.md
# dynasty_issues.csv  dynasty_temporal.csv  readme.md
```

`dynasty_clean.csv` 是运行时唯一会读的文件。其余是审计材料 —— `dynasty_drops.md` 把每一条清洗决定连同上图 URI 都列出来供核查。

## 3. 第一次查询

```python
from src.core.dynasties import get_age_from_cultural_period

# 按年号查（默认 level）
get_age_from_cultural_period("康熙")
# → (1662.0, 1722.0)
```

返回值是 `(begin_year, end_year)`, 公元纪年（公元前用负数）。

## 4. 选择正确的 level

```python
# 年号查询（单一年号）
get_age_from_cultural_period("贞观", level="period")
# → (627.0, 649.0)

# 朝代查询
get_age_from_cultural_period("唐", level="dynasty")
# → (618.0, 907.0)

# 历史时期查询（汉、三国、五代、上古、新石器…）
get_age_from_cultural_period("三国", level="epoch")
# → (220.0, 280.0)
```

!!! tip "三个 level, 一个函数"
    三种 level 不是严格嵌套关系 —— `period` 按 `reignTitle` 匹配, `dynasty` 按 `dynasty` 字面量, `epoch` 按 [`EPOCH_MAP`](epochs.md) 表查。按你输入的语义选合适的那一个。

## 5. 反向查询: 某年都有哪些政权？

```python
from src.core.dynasties import get_cultural_periods_from_year

matches = get_cultural_periods_from_year(250)
for m in matches:
    print(m.dynasty_id, m.reignTitle, m.beginYear, m.endYear)
# 三国        220.0  280.0
# 吴   赤乌  238.0  251.0
# 蜀   延熙  238.0  257.0
# 魏   嘉平  249.0  254.0
```

返回多条是常态 —— 三国、南北朝、五代、隋末唐初这些时期本来就多政权并行。

## 6. 想用外文名字？

```python
ALIASES = {
    "新石器": {"Neolithic", "Neo"},
    "唐":   {"Tang"},
    "康熙": {"Kangxi"},
}

get_age_from_cultural_period("Tang", level="dynasty", aliases=ALIASES)
# → (618.0, 907.0)
```

完整参数行为、BP 纪年转换、自定义 timetable、错误语义详见 [API 参考](api-reference.md)。
