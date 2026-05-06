#!/usr/bin/env python 3.11.0
# -*-coding:utf-8 -*-
# @Author  : Shuang (Twist) Song
# @Contact   : SongshGeo@gmail.com
# GitHub   : https://github.com/SongshGeo
# Website: https://cv.songshgeo.com/
"""Dynasty / reign-era / epoch lookups over ``dynasty_clean.csv``.

Two complementary entry points:

* :func:`get_age_from_cultural_period` — name → ``(begin, end)``.
* :func:`get_cultural_periods_from_year` — year → list of matching rows.

Both consume the cleaned CSV produced by
``scripts/dynasties/clean_dynasties.py`` (which already drops F1 truncated
duplicates, merges F2 split-spans, hand-fills 4 of 5 ``E:missing-year``
rows, and adds a disambiguating ``dynasty_id`` column).
"""

from collections.abc import Iterable, Mapping
from functools import lru_cache
from pathlib import Path
from typing import Literal, NamedTuple

import pandas as pd

_DEFAULT_TABLE_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "dynasties" / "dynasty_clean.csv"
)
_BP_REFERENCE = 1950

# Defense-in-depth: clean.csv already drops these (see scripts/dynasties/
# clean_dynasties.py F1 step), but the filter is kept so a fall-back to the
# raw dynasty_temporal.csv stays safe.
_KNOWN_BAD_URIS = frozenset(
    f"http://data.library.sh.cn/authority/temporal/{i}"
    for i in (
        "fo3y5vgrykmpbupv",  # 晋太康 280-280 (canonical 280-289)
        "348e75qfbzegxsui",  # 晋永安 305-305 (canonical 304-305)
        "vxfb2rg9phlxs47p",  # 西凉永建 420-420 (canonical 420-421)
        "ekjzfp7wkcv8lfxb",  # 安乐 618-618 (canonical 618-623)
        "jp1o55m8a6jepgiz",  # 隋皇泰 618-618 (canonical 618-619)
        "gu17j6je3677vs2d",  # 南平乾祐 948-948 (canonical 948-950)
        "sh9ichrt69298cka",  # 夏五凤 618-618 (canonical 618-621)
    )
)

# Each value is (dynasty_names, year_min, year_max). None = unbounded.
# Year bounds disambiguate name reuse across history (e.g. 三国吴 vs 五代杨吴,
# 西汉 vs 成汉/汉赵, 上古夏 vs 隋末窦建德的夏).
EPOCH_MAP: dict[str, tuple[list[str], int | None, int | None]] = {
    "汉": (["西汉", "汉", "东汉"], -206, 220),
    "晋": (["西晋", "晋", "东晋"], 265, 420),
    "三国": (["三国", "魏", "蜀", "吴"], 184, 280),
    "宋": (["北宋", "宋", "南宋"], 960, 1279),
    "五代": (["后梁", "后唐", "后晋", "后汉", "后周"], 907, 960),
    "南北朝": (
        [
            "南北朝",
            "南齐",
            "南朝宋",
            "梁",
            "陈",
            "北魏",
            "东魏",
            "西魏",
            "北齐",
            "北周",
        ],
        420,
        589,
    ),
    "上古": (["夏", "商", "周", "西周", "东周", "春秋", "战国"], None, -221),
}

# Prehistoric epochs not represented as rows in the dynasty table.
# Bounds in BCE (negative AD years):
#   旧石器 (Paleolithic):  ... → -10000   (open-ended start)
#   新石器 (Neolithic):    -10000 → -2070 (传统'夏朝建立'年份)
# A small gap (-2070 to -1989) exists between 新石器 end and the data's
# 上古 begin (夏 -1989 in dynasty_clean.csv) — it reflects 夏商周断代工程
# vs. 上图原始数据的差异, not a bug in this code.
PREHISTORIC_EPOCHS: dict[str, tuple[float, float]] = {
    "旧石器": (float("-inf"), -10000.0),
    "新石器": (-10000.0, -2070.0),
}


class AmbiguousCulturalPeriodError(ValueError):
    """Raised when a reignTitle resolves to multiple distinct dynasties/rulers."""


class CulturalPeriodMatch(NamedTuple):
    """One row whose temporal span contains the queried year.

    Returned in lists by :func:`get_cultural_periods_from_year` since a year
    typically maps to multiple parallel polities (e.g. 三国 三足鼎立, 隋末
    群雄并起, dynasty-level summary row + per-emperor reign row).

    Fields mirror ``dynasty_clean.csv``. For prehistoric epochs (旧石器/
    新石器), ``uri`` is empty since they're not from 上图 — filter on
    ``uri`` truthiness if you only want data-backed matches.
    """

    dynasty_id: str
    dynasty: str
    reignTitle: str
    monarch: str
    monarchName: str
    beginYear: float
    endYear: float
    label: str
    uri: str


def _resolve_alias(cp: str, aliases: Mapping[str, Iterable[str]] | None) -> str:
    """Resolve ``cp`` against a user-supplied ``{canonical: {aliases}}`` map.

    * No ``aliases`` (or empty) → return ``cp`` unchanged.
    * ``cp`` is itself a canonical key → return it (no rewrite).
    * ``cp`` matches exactly one canonical's alias set → return the canonical.
    * ``cp`` matches multiple canonicals' alias sets → ``ValueError``.
    * No match → return ``cp`` unchanged so the downstream match step can
      report a clean ``KeyError`` against the data.
    """
    if not aliases:
        return cp
    if cp in aliases:
        return cp
    canonicals = [c for c, alts in aliases.items() if cp in alts]
    if len(canonicals) > 1:
        raise ValueError(f"alias {cp!r} maps to multiple canonical names: {canonicals}")
    if canonicals:
        return canonicals[0]
    return cp


def _str_or_empty(value) -> str:
    """Render NaN / None as ``""`` so :class:`CulturalPeriodMatch` typing
    holds. ``dynasty_clean.csv`` is loaded with ``na_values=[""]``, which
    means empty cells come back as NaN in string columns."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value)


@lru_cache(maxsize=1)
def _load_default_dynasty_table() -> pd.DataFrame:
    """Load ``dynasty_clean.csv`` once and cache it.

    Empty cells become NaN (via ``na_values=[""]``); ``beginYear`` and
    ``endYear`` are coerced to numeric. Rows whose ``uri`` is in
    :data:`_KNOWN_BAD_URIS` are filtered out as defense-in-depth even
    though clean.csv already drops them.
    """
    df = pd.read_csv(
        _DEFAULT_TABLE_PATH, dtype=str, keep_default_na=False, na_values=[""]
    )
    df = df.loc[~df["uri"].isin(_KNOWN_BAD_URIS)].copy()
    df["beginYear"] = pd.to_numeric(df["beginYear"], errors="coerce")
    df["endYear"] = pd.to_numeric(df["endYear"], errors="coerce")
    return df


def _coerce_dynasty_table(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of ``df`` with ``beginYear`` / ``endYear`` coerced
    to numeric. Used when the caller passes their own ``time_table`` —
    the default loader handles coercion itself, but user-supplied tables
    may carry string year columns that would otherwise break ``min`` /
    ``max`` arithmetic and inequality masks.
    """
    out = df.copy()
    if "beginYear" in out.columns:
        out["beginYear"] = pd.to_numeric(out["beginYear"], errors="coerce")
    if "endYear" in out.columns:
        out["endYear"] = pd.to_numeric(out["endYear"], errors="coerce")
    return out


def get_age_from_cultural_period(
    cultural_period: str,
    level: Literal["period", "dynasty", "epoch"] = "period",
    *,
    anno_domini: bool = True,
    time_table: pd.DataFrame | None = None,
    aliases: Mapping[str, Iterable[str]] | None = None,
) -> tuple[float, float]:
    """Return ``(begin, end)`` years for a cultural-period name.

    Args:
        cultural_period: 年号 / 朝代 / 历史时期 name (e.g. ``"康熙"``, ``"清"``, ``"汉"``).
        level: Lookup granularity.

            * ``"period"`` (default) — match by ``reignTitle`` (single era;
              falls back to full ``label`` like ``"清康熙"``).
            * ``"dynasty"`` — match by ``dynasty`` column.
            * ``"epoch"`` — match an aggregation in :data:`EPOCH_MAP`, or
              a prehistoric span in :data:`PREHISTORIC_EPOCHS` (旧石器 /
              新石器); falls back to plain dynasty match otherwise.
        anno_domini: If ``True``, return CE/BCE years (BCE negative). If
            ``False``, return ``(older_bp, younger_bp)`` relative to 1950 BP
            (radiocarbon convention).
        time_table: Optional DataFrame matching the schema of
            ``data/dynasty_temporal.csv`` (columns ``dynasty, reignTitle,
            monarch, monarchName, beginYear, endYear, label, uri``). Use to
            inject a pre-filtered slice for disambiguation, or to pass a
            custom timetable.
        aliases: Optional ``{canonical_name: {alias, ...}}`` mapping.
            ``cultural_period`` is rewritten to the canonical name before
            matching, e.g. ``aliases={"新石器": {"Neolithic", "Neo"}}``
            lets ``"Neolithic"`` resolve like ``"新石器"``. An alias that
            maps to multiple canonicals raises ``ValueError``; an
            unknown name passes through unchanged so the downstream
            mismatch surfaces as a normal ``KeyError``.

    Returns:
        ``(begin_year, end_year)``. AD mode: ``begin <= end``. BP mode:
        ``begin >= end`` (begin is older, in BP units).

    Raises:
        KeyError: no matching record found.
        AmbiguousCulturalPeriodError: at ``level="period"``, the reignTitle
            matches multiple ``(dynasty, monarchName)`` combinations.
        ValueError: matched records all lack ``beginYear`` / ``endYear``,
            input is empty, level is unknown, or an alias maps to
            multiple canonical names.
    """
    cp = (cultural_period or "").strip()
    if not cp:
        raise ValueError("cultural_period must be a non-empty string")
    cp = _resolve_alias(cp, aliases)

    # Prehistoric epochs are not represented as rows; resolve before any
    # DataFrame work. Restricted to level="epoch" to mirror how "上古" only
    # resolves at epoch level — keeps the namespace clean.
    if level == "epoch" and cp in PREHISTORIC_EPOCHS:
        begin, end = PREHISTORIC_EPOCHS[cp]
        if not anno_domini:
            return _BP_REFERENCE - begin, _BP_REFERENCE - end
        return begin, end

    df = (
        _load_default_dynasty_table()
        if time_table is None
        else _coerce_dynasty_table(time_table)
    )

    if level == "period":
        matched = df.loc[df["reignTitle"] == cp]
        if matched.empty:
            matched = df.loc[df["label"] == cp]
        keys = matched.drop_duplicates(["dynasty", "monarchName"])
        if len(keys) > 1:
            cands = [
                (r.dynasty, r.monarchName, r.beginYear, r.endYear)
                for r in keys.itertuples()
            ]
            raise AmbiguousCulturalPeriodError(
                f"reignTitle={cp!r} matches {len(cands)} different rulers; "
                f"candidates: {cands}"
            )
    elif level == "dynasty":
        matched = df.loc[df["dynasty"] == cp]
    elif level == "epoch":
        if cp in EPOCH_MAP:
            names, ymin, ymax = EPOCH_MAP[cp]
        else:
            names, ymin, ymax = [cp], None, None  # fallback to dynasty match
        matched = df.loc[df["dynasty"].isin(names)]
        if ymin is not None:
            matched = matched.loc[matched["beginYear"] >= ymin]
        if ymax is not None:
            matched = matched.loc[matched["endYear"] <= ymax]
    else:
        raise ValueError(f"unknown level: {level!r}")

    if matched.empty:
        raise KeyError(f"no entry found for level={level} cultural_period={cp!r}")

    begin = matched["beginYear"].min()
    end = matched["endYear"].max()
    if pd.isna(begin) or pd.isna(end):
        raise ValueError(f"matched rows all lack begin/end for {cp!r}")

    begin = float(begin)
    end = float(end)

    if not anno_domini:
        return _BP_REFERENCE - begin, _BP_REFERENCE - end

    return begin, end


def get_cultural_periods_from_year(
    year: float,
    *,
    anno_domini: bool = True,
    time_table: pd.DataFrame | None = None,
) -> list[CulturalPeriodMatch]:
    """Inverse of :func:`get_age_from_cultural_period`.

    Given a year, return every dynasty / reign-era / prehistoric epoch
    whose ``[beginYear, endYear]`` (inclusive) contains it. Multiple
    matches are normal — at any given year you typically see a dynasty-
    level summary row plus one or more per-emperor reign rows, and during
    三国 / 南北朝 / 五代 / 春秋战国 / 隋末唐初 a handful of parallel
    polities co-exist. Prehistoric epochs (旧石器 / 新石器) participate
    in matching too, with ``uri=""`` to signal they're not from 上图.

    Args:
        year: Query year, AD/BCE convention by default (BCE negative,
            e.g. ``-200`` = 200 BCE). Set ``anno_domini=False`` to
            interpret ``year`` as years BP relative to 1950 instead;
            it is converted to AD before matching.
        anno_domini: How to read ``year``. The OUTPUT ``beginYear`` /
            ``endYear`` on each match is always in AD/BCE form, mirroring
            ``dynasty_clean.csv``.
        time_table: Optional DataFrame with the same schema as
            ``dynasty_clean.csv``. ``_KNOWN_BAD_URIS`` is *not* filtered
            from user-supplied tables (matches the existing convention
            in :func:`get_age_from_cultural_period`).

    Returns:
        List of :class:`CulturalPeriodMatch`, sorted by
        ``(beginYear, endYear)`` ascending — i.e. earliest start first,
        and within ties the row that ends sooner comes first. The list
        is empty when no record covers the year (e.g. far-future years,
        or the gap between 新石器 and 上古夏 in the data).

        Rows with NaN ``endYear`` (the deliberately-unfilled 南诏上元)
        are silently skipped; we don't know whether the year is
        contained, so we don't claim a match.

    Raises:
        ValueError: ``year`` is not a finite number.
    """
    if year is None or (isinstance(year, float) and pd.isna(year)):
        raise ValueError(f"year must be a finite number, got {year!r}")
    year = float(year)
    year_ad = year if anno_domini else _BP_REFERENCE - year

    matches: list[CulturalPeriodMatch] = []

    # Prehistoric: hand-coded brackets, not in the data.
    for name, (p_begin, p_end) in PREHISTORIC_EPOCHS.items():
        if p_begin <= year_ad <= p_end:
            matches.append(
                CulturalPeriodMatch(
                    dynasty_id=name,
                    dynasty=name,
                    reignTitle="",
                    monarch="",
                    monarchName="",
                    beginYear=p_begin,
                    endYear=p_end,
                    label=name,
                    uri="",
                )
            )

    # Data-backed: dynasty_clean.csv (or caller's override).
    df = (
        _load_default_dynasty_table()
        if time_table is None
        else _coerce_dynasty_table(time_table)
    )
    mask = (
        df["beginYear"].notna()
        & df["endYear"].notna()
        & (df["beginYear"] <= year_ad)
        & (df["endYear"] >= year_ad)
    )
    for r in df.loc[mask].itertuples(index=False):
        matches.append(
            CulturalPeriodMatch(
                dynasty_id=_str_or_empty(getattr(r, "dynasty_id", "")),
                dynasty=_str_or_empty(r.dynasty),
                reignTitle=_str_or_empty(r.reignTitle),
                monarch=_str_or_empty(r.monarch),
                monarchName=_str_or_empty(r.monarchName),
                beginYear=float(r.beginYear),
                endYear=float(r.endYear),
                label=_str_or_empty(r.label),
                uri=_str_or_empty(r.uri),
            )
        )

    matches.sort(key=lambda m: (m.beginYear, m.endYear))
    return matches
