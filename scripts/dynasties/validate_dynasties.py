"""Sanity checks on data/dynasties.json.

Flags six categories of likely-incorrect rows:
  A. endYear < beginYear            (impossible)
  B. ancient-name collision         (dynasty in {夏,商,周,...} but beginYear > 0)
  C. one-year span                  (beginYear == endYear; mostly real 短命年号 — review only)
  D. missing critical fields        (reignTitle exists but no monarchName, post-Qin)
  E. missing begin or end           (beginYear or endYear is null)
  F. duplicate (dynasty,reignTitle) (multiple entries with same label/dynasty/reign — pick canonical)
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "dynasties.json"
OUT = ROOT / "data" / "dynasty_issues.csv"

ONT = "http://www.library.sh.cn/ontology"
LABEL = "http://bibframe.org/vocab/label"
ANCIENT_NAMES = {"夏", "商", "周", "西周", "东周", "春秋", "战国"}


def fv(record: dict, predicate: str) -> str | None:
    bucket = record.get(predicate)
    return bucket[0]["value"] if bucket else None


def to_int(s: str | None) -> int | None:
    if s is None:
        return None
    try:
        return int(s)
    except ValueError:
        return None


def flatten(uri: str, record: dict) -> dict:
    return {
        "uri": uri,
        "dynasty": fv(record, f"{ONT}/dynasty"),
        "reignTitle": fv(record, f"{ONT}/reignTitle"),
        "monarch": fv(record, f"{ONT}/monarch"),
        "monarchName": fv(record, f"{ONT}/monarchName"),
        "begin": to_int(fv(record, f"{ONT}/beginYear")),
        "end": to_int(fv(record, f"{ONT}/endYear")),
        "label": fv(record, LABEL),
    }


def main() -> None:
    data = json.loads(SRC.read_text(encoding="utf-8"))
    rows = [flatten(u, r) for u, r in data.items()]

    # detect *true* duplicates: same dynasty + reignTitle + monarchName (same ruler),
    # so reused era names across different rulers (e.g. 后元) don't count.
    dup_groups: dict[tuple[str, str, str], list[dict]] = {}
    for row in rows:
        if row["reignTitle"]:
            key = (row["dynasty"] or "", row["reignTitle"], row["monarchName"] or "")
            dup_groups.setdefault(key, []).append(row)
    duplicates: dict[str, list[dict]] = {}  # uri -> peer rows
    for key, group in dup_groups.items():
        if len(group) > 1:
            for row in group:
                duplicates[row["uri"]] = [r for r in group if r["uri"] != row["uri"]]

    flagged: list[dict] = []

    for row in rows:
        issues: list[str] = []

        if row["begin"] is None or row["end"] is None:
            issues.append("E:missing-year")

        if row["begin"] is not None and row["end"] is not None:
            if row["end"] < row["begin"]:
                issues.append("A:end<begin")
            elif row["begin"] == row["end"]:
                # short-lived eras DO exist; flag for review only
                issues.append("C:1yr-span")

        if (
            row["dynasty"] in ANCIENT_NAMES
            and row["begin"] is not None
            and row["begin"] > 0
        ):
            issues.append("B:ancient-name-AD")

        if (
            row["reignTitle"]
            and not row["monarchName"]
            and row["begin"] is not None
            and row["begin"] >= -221  # post-Qin
        ):
            issues.append("D:no-monarch")

        if row["uri"] in duplicates:
            peers = duplicates[row["uri"]]
            peer_str = "|".join(f"{p['begin']}~{p['end']}" for p in peers)
            # split into "truncated dup" (this row is 1yr and a peer has a longer
            # span overlapping it) vs "split-span" (both have multi-year spans).
            this_is_1yr = (
                row["begin"] is not None
                and row["end"] is not None
                and row["begin"] == row["end"]
            )
            peer_has_longer_overlapping = any(
                p["begin"] is not None
                and p["end"] is not None
                and p["begin"] != p["end"]
                and p["begin"] <= (row["begin"] or 0) <= p["end"]
                for p in peers
            )
            if this_is_1yr and peer_has_longer_overlapping:
                issues.append(f"F1:trunc-dup({peer_str})")
            else:
                issues.append(f"F2:split-span({peer_str})")

        if issues:
            row["issues"] = ";".join(issues)
            flagged.append(row)

    print(f"total entries: {len(rows)}")
    print(f"flagged:       {len(flagged)}")
    print()

    by_issue: dict[str, list[dict]] = {}
    for row in flagged:
        for tag in row["issues"].split(";"):
            top = tag.split("(", 1)[0]
            by_issue.setdefault(top, []).append(row)

    titles = {
        "A:end<begin": "A. endYear < beginYear (impossible)",
        "B:ancient-name-AD": "B. ancient dynasty name (夏/商/周...) but beginYear > 0",
        "C:1yr-span": "C. one-year era (beginYear == endYear) — mostly real 短命年号, review",
        "D:no-monarch": "D. has reignTitle but missing monarchName",
        "E:missing-year": "E. beginYear or endYear is null",
        "F1:trunc-dup": "F1. truncated duplicate (1yr entry + longer-span twin) — likely BAD",
        "F2:split-span": "F2. split-span duplicate (same era split into pieces) — review",
    }

    for tag in (
        "A:end<begin",
        "F1:trunc-dup",
        "E:missing-year",
        "B:ancient-name-AD",
        "D:no-monarch",
        "F2:split-span",
        "C:1yr-span",
    ):
        bucket = by_issue.get(tag, [])
        print(f"### {titles[tag]} — {len(bucket)} rows")
        for row in bucket[:50]:
            d = row["dynasty"] or "∅"
            rt = row["reignTitle"] or ""
            mo = row["monarch"] or "∅"
            mn = row["monarchName"] or "∅"
            lb = row["label"] or "∅"
            print(
                f"  [{row['begin']}~{row['end']}] {d:<4} "
                f"{rt:<10} monarch={mo:<6} name={mn:<14} label={lb:<14} "
                f"<{row['uri'].rsplit('/', 1)[-1]}>"
            )
        if len(bucket) > 50:
            print(f"  ... and {len(bucket) - 50} more")
        print()

    with OUT.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "issues",
                "dynasty",
                "reignTitle",
                "monarch",
                "monarchName",
                "begin",
                "end",
                "label",
                "uri",
            ],
        )
        writer.writeheader()
        for row in flagged:
            writer.writerow(
                {
                    "issues": row["issues"],
                    "dynasty": row["dynasty"],
                    "reignTitle": row["reignTitle"],
                    "monarch": row["monarch"],
                    "monarchName": row["monarchName"],
                    "begin": row["begin"],
                    "end": row["end"],
                    "label": row["label"],
                    "uri": row["uri"],
                }
            )
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
