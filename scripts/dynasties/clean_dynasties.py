"""Clean dynasty_temporal.csv into a downstream-authoritative dynasty_clean.csv.

Pipeline stage: scrape -> validate -> **clean** (this script) -> downstream usage.

Strategies (each row that gets modified emits a `RawDataModifiedWarning`,
and is also recorded line-by-line in dynasty_drops.md):

  1. F1 truncated duplicates (7 rows): drop. The longer-span sibling already
     exists in the data; the 1-year row is an upstream truncation artifact.
  2. F2 split-span (43 rows -> ~22 groups): merge to [min(begin), max(end)].
     Upstream splits eras at historical events (e.g. 隋开皇 split at 589
     unification); we collapse to ensure a year maps to a single 年号.
  3. E missing endYear (5 rows): hand-fill 4 from documented history per
     data/dynasties/readme.md; 1 (南诏上元) left NaN with a loud warning
     pointing the user to verify on data.library.sh.cn.
  4. B ancient-name-AD (5 rows): rewrite `dynasty_id` to a disambiguated key
     so 上古夏 (-1989) and 隋末唐初 夏(窦建德/刘虎/刘黑闼) don't collide.

The script consumes only stdlib so it stays in lockstep with the rest of
scripts/dynasties/.
"""

from __future__ import annotations

import csv
import sys
import warnings
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW_CSV = ROOT / "data" / "dynasties" / "dynasty_temporal.csv"
ISSUES_CSV = ROOT / "data" / "dynasties" / "dynasty_issues.csv"
OUT_CSV = ROOT / "data" / "dynasties" / "dynasty_clean.csv"
OUT_MD = ROOT / "data" / "dynasties" / "dynasty_drops.md"

SOURCE_HOMEPAGE = "https://data.library.sh.cn/dynasty/"
ANCIENT_NAMES = {"夏", "商", "周", "西周", "东周", "春秋", "战国"}

# Hand-filled endYear by URI. Sources documented in data/dynasties/readme.md.
# Keyed by URI (most stable identifier).
KNOWN_ENDS: dict[str, tuple[int, str]] = {
    "http://data.library.sh.cn/authority/temporal/glvpbcmcui3yfien": (
        577,
        "北齐承光: 577 年北齐为周所灭 (readme.md)",
    ),
    "http://data.library.sh.cn/authority/temporal/kuvnpho9wvo4azic": (
        926,
        "渤海大諲譔: 926 年被辽灭 (readme.md)",
    ),
    "http://data.library.sh.cn/authority/temporal/n3bv41hw1hoihwy8": (
        925,
        "前蜀咸康/王衍: 925 年为后唐所灭 (readme.md)",
    ),
    "http://data.library.sh.cn/authority/temporal/8uv1kezwk7i1n6kq": (
        968,
        "大理广德/段思聪: 段思聪卒于 968 (readme.md, 待精确史料核)",
    ),
    # 南诏上元 (4eljzv3hcnl3l1uv) is intentionally absent: readme.md gave no
    # historical end. Stays NaN; downstream sees it as a known unknown.
}


class RawDataModifiedWarning(UserWarning):
    """Emitted once per row whose raw values were dropped, merged, filled,
    disambiguated, or otherwise altered between dynasty_temporal.csv and
    dynasty_clean.csv. The message always carries enough info to look the
    record back up at https://data.library.sh.cn/."""


def warn(msg: str) -> None:
    warnings.warn(msg, RawDataModifiedWarning, stacklevel=2)


def to_int(s: str) -> int | None:
    if s == "" or s is None:
        return None
    try:
        return int(s)
    except ValueError:
        return None


def read_raw() -> list[dict]:
    with RAW_CSV.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        rows = []
        for r in reader:
            rows.append(
                {
                    "dynasty": r["dynasty"] or "",
                    "reignTitle": r["reignTitle"] or "",
                    "monarch": r["monarch"] or "",
                    "monarchName": r["monarchName"] or "",
                    "beginYear": to_int(r["beginYear"]),
                    "endYear": to_int(r["endYear"]),
                    "label": r["label"] or "",
                    "uri": r["uri"],
                }
            )
        return rows


def read_issues() -> dict[str, str]:
    """uri -> issues string ('A:end<begin;F1:trunc-dup(...)')."""
    out: dict[str, str] = {}
    with ISSUES_CSV.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for r in reader:
            out[r["uri"]] = r["issues"]
    return out


def has_tag(issues: str, tag: str) -> bool:
    return any(t.split("(", 1)[0] == tag for t in issues.split(";"))


def fmt_uri(uri: str) -> str:
    """As a plain link for warning messages."""
    return f"<{uri}>"


def md_link(uri: str) -> str:
    """As a markdown link for the audit doc."""
    tail = uri.rsplit("/", 1)[-1]
    return f"[{tail}]({uri})"


def row_label(row: dict) -> str:
    """Compact human-readable identifier for warning messages."""
    d = row["dynasty"] or "∅"
    rt = row["reignTitle"]
    mn = row["monarchName"] or row["monarch"] or "∅"
    return f"{d}·{rt}({mn})" if rt else f"{d}·({mn})"


# ---------------------------------------------------------------------------
# Audit document (dynasty_drops.md)
# ---------------------------------------------------------------------------


class AuditLog:
    """Collects per-row records for each cleaning action and writes
    dynasty_drops.md at the end."""

    def __init__(self) -> None:
        self.dropped_f1: list[dict] = []
        self.merged_f2: list[dict] = []  # one entry per merge group
        self.filled_e: list[dict] = []
        self.unfilled_e: list[dict] = []
        self.disambiguated_b: list[dict] = []

    def write(self, raw_n: int, clean_n: int) -> None:
        lines: list[str] = []
        lines.append("# 上图朝代数据清洗审计 (auto-generated)")
        lines.append("")
        lines.append(f"> 数据源: {SOURCE_HOMEPAGE}")
        lines.append(
            f"> 共 {raw_n} 条 → clean 后 {clean_n} 条 ("
            f"丢 {len(self.dropped_f1)}, "
            f"合并 {sum(g['merged_count'] for g in self.merged_f2)}→{len(self.merged_f2)}, "
            f"补全 {len(self.filled_e)}, 留 NaN {len(self.unfilled_e)}, "
            f"重名消歧 {len(self.disambiguated_b)})"
        )
        lines.append("")
        lines.append(
            "> 本文件由 `scripts/dynasties/clean_dynasties.py` 自动生成。"
            "如对任何清洗判断有异议, 点 URI 链接到上图原始记录核对。"
        )
        lines.append("")

        # Section 1: F1 dropped
        lines.append(f"## 1. 丢弃 — F1 截断重复 ({len(self.dropped_f1)} 条)")
        lines.append("")
        lines.append("同一年号同一帝王同时存在两条记录: 一条只有 1 年 (begin=end),")
        lines.append(
            "另一条是真实的多年跨度。前者是上图录入截断, 已被后者覆盖, 故丢弃。"
        )
        lines.append("")
        lines.append(
            "| dynasty | reignTitle | monarchName | dropped (1-yr) | kept (real span) | dropped URI |"
        )
        lines.append("|---|---|---|---|---|---|")
        for r in self.dropped_f1:
            lines.append(
                f"| {r['dynasty'] or '—'} | {r['reignTitle'] or '—'} | "
                f"{r['monarchName'] or '—'} | {r['begin']}~{r['end']} | "
                f"{r['kept_span']} | {md_link(r['uri'])} |"
            )
        lines.append("")
        lines.append("> 如对清洗判断有异议, 点 URI 链接到上图核对原始记录。")
        lines.append("")

        # Section 2: F2 merged
        merged_total = sum(g["merged_count"] for g in self.merged_f2)
        lines.append(
            f"## 2. 合并 — F2 同年号上图按事件拆分 "
            f"({merged_total} 条 → {len(self.merged_f2)} 组)"
        )
        lines.append("")
        lines.append(
            "上图将一些年号按历史事件 (如 589 隋统一、420 北凉迁都) 拆为多段。"
        )
        lines.append(
            "我们合并为 `[min(begin), max(end)]` 单段, 以保证'一年→单一年号'查询。"
        )
        lines.append(
            "拆分点的事件语义在此留痕 — 若下游需要事件级精度, 请回上图查原始 URI。"
        )
        lines.append("")
        lines.append(
            "| dynasty | reignTitle | monarchName | original spans | merged → | kept URI | dropped URIs |"
        )
        lines.append("|---|---|---|---|---|---|---|")
        for g in self.merged_f2:
            spans = ", ".join(f"{a}~{b}" for a, b in g["original_spans"])
            dropped = "<br/>".join(md_link(u) for u in g["dropped_uris"]) or "—"
            lines.append(
                f"| {g['dynasty'] or '—'} | {g['reignTitle'] or '—'} | "
                f"{g['monarchName'] or '—'} | {spans} | "
                f"**{g['merged_begin']}~{g['merged_end']}** | "
                f"{md_link(g['kept_uri'])} | {dropped} |"
            )
        lines.append("")
        lines.append("> 如对清洗判断有异议, 点 URI 链接到上图核对原始记录。")
        lines.append("")

        # Section 3: E filled / unfilled
        lines.append(
            f"## 3. 手工补全 endYear "
            f"({len(self.filled_e)} 条已补 / {len(self.unfilled_e)} 条待用户核查)"
        )
        lines.append("")
        lines.append("上图原始记录缺 endYear。可从已知史实补全的写入 `KNOWN_ENDS` 表, ")
        lines.append("无史实出处的保留 `endYear=NaN` 并标注为待用户核查。")
        lines.append("")
        lines.append(
            "| status | dynasty | reignTitle | monarchName | begin~end | source / note | URI |"
        )
        lines.append("|---|---|---|---|---|---|---|")
        for r in self.filled_e:
            lines.append(
                f"| ✅ filled | {r['dynasty'] or '—'} | {r['reignTitle'] or '—'} | "
                f"{r['monarchName'] or '—'} | {r['begin']}~**{r['filled_end']}** | "
                f"{r['note']} | {md_link(r['uri'])} |"
            )
        for r in self.unfilled_e:
            lines.append(
                f"| ⚠ **TODO 用户核查** | {r['dynasty'] or '—'} | "
                f"{r['reignTitle'] or '—'} | {r['monarchName'] or '—'} | "
                f"{r['begin']}~? | readme.md 未给已知 end | {md_link(r['uri'])} |"
            )
        lines.append("")
        lines.append("> 如对清洗判断有异议, 点 URI 链接到上图核对原始记录。")
        lines.append("")

        # Section 4: B disambiguation
        lines.append(
            f"## 4. 重名消歧 — `dynasty_id` 重写 ({len(self.disambiguated_b)} 条)"
        )
        lines.append("")
        lines.append("上古朝代名 (夏/商/周/...) 在 AD 时期被某些割据政权复用 (如隋末")
        lines.append("唐初窦建德/刘虎/刘黑闼三家'夏')。原 `dynasty` 字段保留, 新增 ")
        lines.append("`dynasty_id` 列加 `(monarchName)` 后缀以唯一区分。")
        lines.append("")
        lines.append("| dynasty | begin~end | monarchName | dynasty_id (new) | URI |")
        lines.append("|---|---|---|---|---|")
        for r in self.disambiguated_b:
            lines.append(
                f"| {r['dynasty']} | {r['begin']}~{r['end']} | "
                f"{r['monarchName'] or '—'} | **{r['dynasty_id']}** | "
                f"{md_link(r['uri'])} |"
            )
        lines.append("")
        lines.append("> 如对清洗判断有异议, 点 URI 链接到上图核对原始记录。")
        lines.append("")

        OUT_MD.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Cleaning steps
# ---------------------------------------------------------------------------


def step_drop_f1(
    rows: list[dict], issues: dict[str, str], audit: AuditLog
) -> list[dict]:
    """Drop F1:trunc-dup rows; emit one warning per dropped URI."""
    # Map (dynasty, reignTitle, monarchName) -> list of rows for finding the kept sibling
    sibling_index: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        sibling_index[(r["dynasty"], r["reignTitle"], r["monarchName"])].append(r)

    keep: list[dict] = []
    dropped_count = 0
    for r in rows:
        tags = issues.get(r["uri"], "")
        if has_tag(tags, "F1:trunc-dup"):
            siblings = [
                s
                for s in sibling_index[
                    (r["dynasty"], r["reignTitle"], r["monarchName"])
                ]
                if s["uri"] != r["uri"]
            ]
            kept_span = "?"
            for s in siblings:
                if s["beginYear"] != s["endYear"]:
                    kept_span = f"{s['beginYear']}~{s['endYear']}"
                    break
            warn(
                f"DROP F1 截断重复: {row_label(r)} {r['beginYear']}~{r['endYear']} "
                f"{fmt_uri(r['uri'])} (已被同年号长跨度条 {kept_span} 覆盖)"
            )
            audit.dropped_f1.append(
                {
                    **r,
                    "begin": r["beginYear"],
                    "end": r["endYear"],
                    "kept_span": kept_span,
                }
            )
            dropped_count += 1
            continue
        keep.append(r)
    print(f"  F1 dropped: {dropped_count} rows", file=sys.stderr)
    return keep


def step_fill_e(
    rows: list[dict], issues: dict[str, str], audit: AuditLog
) -> list[dict]:
    """Hand-fill known-end rows; warn on each (filled or still-missing)."""
    filled_count = 0
    unfilled_count = 0
    for r in rows:
        tags = issues.get(r["uri"], "")
        if not has_tag(tags, "E:missing-year"):
            continue
        if r["endYear"] is not None and r["beginYear"] is not None:
            continue  # only handle the missing-end case (the 5 documented rows)
        if r["uri"] in KNOWN_ENDS:
            new_end, note = KNOWN_ENDS[r["uri"]]
            warn(
                f"FILL E 手工补全 endYear: {row_label(r)} "
                f"{r['beginYear']}~? → {r['beginYear']}~{new_end} "
                f"{fmt_uri(r['uri'])} (来源: {note})"
            )
            audit.filled_e.append(
                {
                    **r,
                    "begin": r["beginYear"],
                    "end": r["endYear"],
                    "filled_end": new_end,
                    "note": note,
                }
            )
            r["endYear"] = new_end
            filled_count += 1
        else:
            warn(
                f"⚠ STILL MISSING endYear: {row_label(r)} {r['beginYear']}~? — "
                f"readme.md 未提供已知值, 输出 endYear=NaN, "
                f"请到 {fmt_uri(r['uri'])} 核查"
            )
            audit.unfilled_e.append(
                {
                    **r,
                    "begin": r["beginYear"],
                    "end": r["endYear"],
                }
            )
            unfilled_count += 1
    print(
        f"  E filled: {filled_count} rows ({unfilled_count} still NaN)", file=sys.stderr
    )
    return rows


def step_merge_f2(
    rows: list[dict], issues: dict[str, str], audit: AuditLog
) -> list[dict]:
    """Merge F2:split-span groups to [min(begin), max(end)].

    A 'group' is rows sharing (dynasty, reignTitle, monarchName) where >=2 rows
    are tagged F2:split-span. Re-detected here because F1 drops may have
    reduced some upstream-tagged groups to a single row (no merge needed)."""
    f2_uris = {u for u, tags in issues.items() if has_tag(tags, "F2:split-span")}

    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        if r["uri"] in f2_uris:
            groups[(r["dynasty"], r["reignTitle"], r["monarchName"])].append(r)

    drop_uris: set[str] = set()
    merged_groups = 0
    merged_total = 0
    for key, group in groups.items():
        if len(group) < 2:
            continue  # F1 drop may have collapsed the group
        begins = [g["beginYear"] for g in group if g["beginYear"] is not None]
        ends = [g["endYear"] for g in group if g["endYear"] is not None]
        if not begins or not ends:
            continue
        new_begin, new_end = min(begins), max(ends)
        kept = group[0]
        dropped = group[1:]
        original_spans = [(g["beginYear"], g["endYear"]) for g in group]
        warn(
            f"MERGE F2 分段合并: {row_label(kept)} "
            f"{original_spans} → {new_begin}~{new_end} "
            f"(kept {fmt_uri(kept['uri'])}; "
            f"dropped {', '.join(fmt_uri(d['uri']) for d in dropped)}; "
            f"上图按事件拆分, 此处合并以保证年份唯一映射)"
        )
        audit.merged_f2.append(
            {
                "dynasty": kept["dynasty"],
                "reignTitle": kept["reignTitle"],
                "monarchName": kept["monarchName"],
                "original_spans": original_spans,
                "merged_begin": new_begin,
                "merged_end": new_end,
                "kept_uri": kept["uri"],
                "dropped_uris": [d["uri"] for d in dropped],
                "merged_count": len(group),
            }
        )
        kept["beginYear"], kept["endYear"] = new_begin, new_end
        for d in dropped:
            drop_uris.add(d["uri"])
        merged_groups += 1
        merged_total += len(group)

    print(
        f"  F2 merged: {merged_total} rows → {merged_groups} groups",
        file=sys.stderr,
    )
    return [r for r in rows if r["uri"] not in drop_uris]


def step_disambiguate_b(
    rows: list[dict], issues: dict[str, str], audit: AuditLog
) -> list[dict]:
    """Compute dynasty_id, rewriting AD-era reuses of ancient names."""
    for r in rows:
        r["dynasty_id"] = r["dynasty"]  # default

    count = 0
    for r in rows:
        if (
            r["dynasty"] in ANCIENT_NAMES
            and r["beginYear"] is not None
            and r["beginYear"] > 0
        ):
            disambiguator = (
                r["monarchName"]
                or r["monarch"]
                or r["reignTitle"]
                or r["uri"].rsplit("/", 1)[-1]
            )
            new_id = f"{r['dynasty']}({disambiguator})"
            warn(
                f"DISAMBIGUATE B 重名消歧: dynasty='{r['dynasty']}' "
                f"({r['beginYear']}~{r['endYear']}, {disambiguator}) 与上古"
                f"{r['dynasty']} 同名 → dynasty_id='{new_id}' "
                f"{fmt_uri(r['uri'])}"
            )
            audit.disambiguated_b.append(
                {
                    **r,
                    "begin": r["beginYear"],
                    "end": r["endYear"],
                    "dynasty_id": new_id,
                }
            )
            r["dynasty_id"] = new_id
            count += 1
    print(f"  B disambiguated: {count} rows", file=sys.stderr)
    return rows


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------


def write_clean(rows: list[dict]) -> None:
    fieldnames = [
        "dynasty_id",
        "dynasty",
        "reignTitle",
        "monarch",
        "monarchName",
        "beginYear",
        "endYear",
        "label",
        "uri",
    ]
    with OUT_CSV.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(
                {
                    "dynasty_id": r["dynasty_id"],
                    "dynasty": r["dynasty"],
                    "reignTitle": r["reignTitle"],
                    "monarch": r["monarch"],
                    "monarchName": r["monarchName"],
                    "beginYear": "" if r["beginYear"] is None else r["beginYear"],
                    "endYear": "" if r["endYear"] is None else r["endYear"],
                    "label": r["label"],
                    "uri": r["uri"],
                }
            )


def main() -> None:
    # Always show every modification — the whole point is transparency.
    warnings.simplefilter("always", RawDataModifiedWarning)

    rows = read_raw()
    issues = read_issues()
    raw_n = len(rows)
    print(f"[clean_dynasties] {raw_n} raw rows", file=sys.stderr)

    audit = AuditLog()
    rows = step_drop_f1(rows, issues, audit)
    rows = step_fill_e(rows, issues, audit)
    rows = step_merge_f2(rows, issues, audit)
    rows = step_disambiguate_b(rows, issues, audit)

    clean_n = len(rows)
    write_clean(rows)
    audit.write(raw_n=raw_n, clean_n=clean_n)

    n_warns = (
        len(audit.dropped_f1)
        + len(audit.merged_f2)
        + len(audit.filled_e)
        + len(audit.unfilled_e)
        + len(audit.disambiguated_b)
    )
    print(
        f"[clean_dynasties] {raw_n} raw → {clean_n} clean | warnings: {n_warns}",
        file=sys.stderr,
    )
    print(f"  wrote {OUT_CSV.relative_to(ROOT)}", file=sys.stderr)
    print(f"  wrote {OUT_MD.relative_to(ROOT)}", file=sys.stderr)


if __name__ == "__main__":
    main()
