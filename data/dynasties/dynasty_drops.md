# 上图朝代数据清洗审计 (auto-generated)

> 数据源: https://data.library.sh.cn/dynasty/
> 共 879 条 → clean 后 854 条 (丢 7, 合并 36→18, 补全 4, 留 NaN 1, 重名消歧 4)

> 本文件由 `scripts/dynasties/clean_dynasties.py` 自动生成。如对任何清洗判断有异议, 点 URI 链接到上图原始记录核对。

## 1. 丢弃 — F1 截断重复 (7 条)

同一年号同一帝王同时存在两条记录: 一条只有 1 年 (begin=end),
另一条是真实的多年跨度。前者是上图录入截断, 已被后者覆盖, 故丢弃。

| dynasty | reignTitle | monarchName | dropped (1-yr) | kept (real span) | dropped URI |
|---|---|---|---|---|---|
| 晋 | 太康 | 司马炎 | 280~280 | 280~289 | [fo3y5vgrykmpbupv](http://data.library.sh.cn/authority/temporal/fo3y5vgrykmpbupv) |
| 晋 | 永安 | 司马衷 | 305~305 | 304~305 | [348e75qfbzegxsui](http://data.library.sh.cn/authority/temporal/348e75qfbzegxsui) |
| 西凉 | 永建 | 李恂 | 420~420 | 420~421 | [vxfb2rg9phlxs47p](http://data.library.sh.cn/authority/temporal/vxfb2rg9phlxs47p) |
| — | 安乐 | 李轨 | 618~618 | 618~623 | [ekjzfp7wkcv8lfxb](http://data.library.sh.cn/authority/temporal/ekjzfp7wkcv8lfxb) |
| 隋 | 皇泰 | 杨侗 | 618~618 | 618~619 | [jp1o55m8a6jepgiz](http://data.library.sh.cn/authority/temporal/jp1o55m8a6jepgiz) |
| 南平 | 乾祐 | 高保融 | 948~948 | 948~950 | [gu17j6je3677vs2d](http://data.library.sh.cn/authority/temporal/gu17j6je3677vs2d) |
| 夏 | 五凤 | 窦建德 | 618~618 | 618~621 | [sh9ichrt69298cka](http://data.library.sh.cn/authority/temporal/sh9ichrt69298cka) |

> 如对清洗判断有异议, 点 URI 链接到上图核对原始记录。

## 2. 合并 — F2 同年号上图按事件拆分 (36 条 → 18 组)

上图将一些年号按历史事件 (如 589 隋统一、420 北凉迁都) 拆为多段。
我们合并为 `[min(begin), max(end)]` 单段, 以保证'一年→单一年号'查询。
拆分点的事件语义在此留痕 — 若下游需要事件级精度, 请回上图查原始 URI。

| dynasty | reignTitle | monarchName | original spans | merged → | kept URI | dropped URIs |
|---|---|---|---|---|---|---|
| 汉 | 建平 | 刘欣 | -6~-5, -5~-3 | **-6~-3** | [vuoeofj271g96eb2](http://data.library.sh.cn/authority/temporal/vuoeofj271g96eb2) | [amvtgsrbhv3316w8](http://data.library.sh.cn/authority/temporal/amvtgsrbhv3316w8) |
| 后秦 | 白雀 | 姚苌 | 384~386, 384~386 | **384~386** | [rerrvzs5i41ek322](http://data.library.sh.cn/authority/temporal/rerrvzs5i41ek322) | [5xzvownn7cviildh](http://data.library.sh.cn/authority/temporal/5xzvownn7cviildh) |
| 东晋 | 元兴 | 司马德宗 | 402~403, 404~404 | **402~404** | [7qoibz4hyub5xosg](http://data.library.sh.cn/authority/temporal/7qoibz4hyub5xosg) | [mtme6wjkuhvmptxe](http://data.library.sh.cn/authority/temporal/mtme6wjkuhvmptxe) |
| 北凉 | 玄始 | 沮渠蒙逊 | 412~420, 420~428 | **412~428** | [5psm1qtb2nz51g4e](http://data.library.sh.cn/authority/temporal/5psm1qtb2nz51g4e) | [46rll74uqosg839j](http://data.library.sh.cn/authority/temporal/46rll74uqosg839j) |
| 梁 | 承圣 | 萧绎 | 552~555, 553~554 | **552~555** | [n9u3rdpli664wlvt](http://data.library.sh.cn/authority/temporal/n9u3rdpli664wlvt) | [p3djldcondu9rx4b](http://data.library.sh.cn/authority/temporal/p3djldcondu9rx4b) |
| 高昌 | 延昌 | 麴乾固 | 561~589, 589~601 | **561~601** | [dbvlcnjnf2w148ip](http://data.library.sh.cn/authority/temporal/dbvlcnjnf2w148ip) | [i4gzq1997nn8nufc](http://data.library.sh.cn/authority/temporal/i4gzq1997nn8nufc) |
| 隋 | 开皇 | 杨坚 | 582~589, 589~600 | **582~600** | [ylyobpybbk442ev6](http://data.library.sh.cn/authority/temporal/ylyobpybbk442ev6) | [1p4t1rtattpetdfn](http://data.library.sh.cn/authority/temporal/1p4t1rtattpetdfn) |
| 高昌 | 义和 | 麴□ | 614~618, 618~619 | **614~619** | [bf218vii1c6fj4aq](http://data.library.sh.cn/authority/temporal/bf218vii1c6fj4aq) | [kv77na29tocjf8pb](http://data.library.sh.cn/authority/temporal/kv77na29tocjf8pb) |
| — | 昌达 | 朱粲 | 615~618, 618~619 | **615~619** | [5nsz6pu5numz1ls5](http://data.library.sh.cn/authority/temporal/5nsz6pu5numz1ls5) | [qyautsp4racb8ls1](http://data.library.sh.cn/authority/temporal/qyautsp4racb8ls1) |
| 楚 | 太平 | 林士弘 | 616~618, 618~622 | **616~622** | [m9mfgfyvjwjpnshj](http://data.library.sh.cn/authority/temporal/m9mfgfyvjwjpnshj) | [1dwijyeoweiftq8w](http://data.library.sh.cn/authority/temporal/1dwijyeoweiftq8w) |
| — | 天兴 | 刘武周 | 617~618, 618~620 | **617~620** | [fc1bpe6kp4ip63wl](http://data.library.sh.cn/authority/temporal/fc1bpe6kp4ip63wl) | [3rg33wlc5dsm9qa3](http://data.library.sh.cn/authority/temporal/3rg33wlc5dsm9qa3) |
| 梁 | 永隆 | 梁师都 | 617~618, 618~628 | **617~628** | [morqizkjdraq42gk](http://data.library.sh.cn/authority/temporal/morqizkjdraq42gk) | [y1lyqeazxb9or8mj](http://data.library.sh.cn/authority/temporal/y1lyqeazxb9or8mj) |
| 梁 | 鸣凤 | 萧铣 | 617~618, 618~621 | **617~621** | [jl1qvvfjrkb4igqb](http://data.library.sh.cn/authority/temporal/jl1qvvfjrkb4igqb) | [sqakp2qhv4j2ul7g](http://data.library.sh.cn/authority/temporal/sqakp2qhv4j2ul7g) |
| 南诏 | 阁逻凤 | NON | 746~751, 752~768 | **746~768** | [yexkmubqdqmoigrx](http://data.library.sh.cn/authority/temporal/yexkmubqdqmoigrx) | [hptc7bde439lnd44](http://data.library.sh.cn/authority/temporal/hptc7bde439lnd44) |
| 吴 | 天祐 | 杨渥 | 905~907, 907~919 | **905~919** | [9re19pl2w2hiwg7s](http://data.library.sh.cn/authority/temporal/9re19pl2w2hiwg7s) | [3nm1usbwxwlw59h1](http://data.library.sh.cn/authority/temporal/3nm1usbwxwlw59h1) |
| 闽 | 乾化 | 王审知 | 911~912, 914~915 | **911~915** | [9faq4n3lg6q5w2zr](http://data.library.sh.cn/authority/temporal/9faq4n3lg6q5w2zr) | [vpevn7dljt8gkz4r](http://data.library.sh.cn/authority/temporal/vpevn7dljt8gkz4r) |
| 楚 | 天福 | 马希範 | 937~943, 947~947 | **937~947** | [nrs93gczomxy2y62](http://data.library.sh.cn/authority/temporal/nrs93gczomxy2y62) | [e647hppyovtxy3tj](http://data.library.sh.cn/authority/temporal/e647hppyovtxy3tj) |
| 南平 | 天福 | 高从诲 | 937~943, 947~947 | **937~947** | [blx2icc6q27q9xv7](http://data.library.sh.cn/authority/temporal/blx2icc6q27q9xv7) | [xdhtmo9ur88khdz9](http://data.library.sh.cn/authority/temporal/xdhtmo9ur88khdz9) |

> 如对清洗判断有异议, 点 URI 链接到上图核对原始记录。

## 3. 手工补全 endYear (4 条已补 / 1 条待用户核查)

上图原始记录缺 endYear。可从已知史实补全的写入 `KNOWN_ENDS` 表,
无史实出处的保留 `endYear=NaN` 并标注为待用户核查。

| status | dynasty | reignTitle | monarchName | begin~end | source / note | URI |
|---|---|---|---|---|---|---|
| ✅ filled | 北齐 | 承光 | 高恒 | 577~**577** | 北齐承光: 577 年北齐为周所灭 (readme.md) | [glvpbcmcui3yfien](http://data.library.sh.cn/authority/temporal/glvpbcmcui3yfien) |
| ✅ filled | 渤海 | — | 大諲譔 | 907~**926** | 渤海大諲譔: 926 年被辽灭 (readme.md) | [kuvnpho9wvo4azic](http://data.library.sh.cn/authority/temporal/kuvnpho9wvo4azic) |
| ✅ filled | 前蜀 | 咸康 | 王衍 | 925~**925** | 前蜀咸康/王衍: 925 年为后唐所灭 (readme.md) | [n3bv41hw1hoihwy8](http://data.library.sh.cn/authority/temporal/n3bv41hw1hoihwy8) |
| ✅ filled | 大理 | 广德 | 段思聪 | 956~**968** | 大理广德/段思聪: 段思聪卒于 968 (readme.md, 待精确史料核) | [8uv1kezwk7i1n6kq](http://data.library.sh.cn/authority/temporal/8uv1kezwk7i1n6kq) |
| ⚠ **TODO 用户核查** | 南诏 | 上元 | NON | 784~? | readme.md 未给已知 end | [4eljzv3hcnl3l1uv](http://data.library.sh.cn/authority/temporal/4eljzv3hcnl3l1uv) |

> 如对清洗判断有异议, 点 URI 链接到上图核对原始记录。

## 4. 重名消歧 — `dynasty_id` 重写 (4 条)

上古朝代名 (夏/商/周/...) 在 AD 时期被某些割据政权复用 (如隋末
唐初窦建德/刘虎/刘黑闼三家'夏')。原 `dynasty` 字段保留, 新增
`dynasty_id` 列加 `(monarchName)` 后缀以唯一区分。

| dynasty | begin~end | monarchName | dynasty_id (new) | URI |
|---|---|---|---|---|
| 夏 | 421~428 | 刘虎 | **夏(刘虎)** | [izq73mev4g3ajor2](http://data.library.sh.cn/authority/temporal/izq73mev4g3ajor2) |
| 夏 | 617~618 | 窦建德 | **夏(窦建德)** | [hm6tq9vl6nx7pa4l](http://data.library.sh.cn/authority/temporal/hm6tq9vl6nx7pa4l) |
| 夏 | 618~621 | 窦建德 | **夏(窦建德)** | [fk9omvu42cf2rlao](http://data.library.sh.cn/authority/temporal/fk9omvu42cf2rlao) |
| 夏 | 622~623 | 刘黑闼 | **夏(刘黑闼)** | [o21xjey9i9onrsyf](http://data.library.sh.cn/authority/temporal/o21xjey9i9onrsyf) |

> 如对清洗判断有异议, 点 URI 链接到上图核对原始记录。
