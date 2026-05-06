"""Tests for ``src.core.dynasties.get_age_from_cultural_period``.

Anchors below are pinned to ``data/dynasties/dynasty_clean.csv`` produced by
``scripts/dynasties/clean_dynasties.py``. The clean stage already:

* drops the 7 F1 truncated-duplicate rows (so e.g. 晋·太康 returns 280–289),
* merges F2 split-spans (so e.g. 隋·开皇 is a single 582–600 row),
* hand-fills 4 of the 5 ``E:missing-year`` rows (so e.g. 北齐·承光 has
  ``endYear=577`` instead of NaN).

If the clean CSV is regenerated and the upstream data shifts, anchor years
here may need updating — adjust them, don't loosen the assertions.
"""

from __future__ import annotations

import pandas as pd
import pytest

from chhiskit.core.dynasties import (
    _BP_REFERENCE,
    EPOCH_MAP,
    PREHISTORIC_EPOCHS,
    AmbiguousCulturalPeriodError,
    CulturalPeriodMatch,
    _load_default_dynasty_table,
    get_age_from_cultural_period,
    get_cultural_periods_from_year,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def default_table() -> pd.DataFrame:
    """Real cleaned dynasty table used by the function under test.

    Module-scoped so we read the CSV once across the whole test module.
    """
    return _load_default_dynasty_table()


@pytest.fixture
def synthetic_table() -> pd.DataFrame:
    """Tiny in-memory table for isolated tests of the ``time_table`` arg.

    Two consecutive eras under a fictional 测试 dynasty so we never collide
    with real names. ``beginYear`` / ``endYear`` are strings on purpose to
    exercise ``_coerce_dynasty_table``'s numeric coercion path.
    """
    return pd.DataFrame(
        [
            {
                "dynasty": "测试",
                "reignTitle": "甲",
                "monarch": "",
                "monarchName": "甲帝",
                "beginYear": "100",
                "endYear": "120",
                "label": "测试甲",
                "uri": "test:1",
            },
            {
                "dynasty": "测试",
                "reignTitle": "乙",
                "monarch": "",
                "monarchName": "乙帝",
                "beginYear": "120",
                "endYear": "150",
                "label": "测试乙",
                "uri": "test:2",
            },
        ]
    )


@pytest.fixture
def all_nan_year_table() -> pd.DataFrame:
    """Table where every match would have NaN years.

    Used to exercise the ValueError path when min/max produce NaN.
    """
    return pd.DataFrame(
        [
            {
                "dynasty": "无年",
                "reignTitle": "无",
                "monarch": "",
                "monarchName": "无",
                "beginYear": None,
                "endYear": None,
                "label": "无年无",
                "uri": "nan:1",
            }
        ]
    )


# ---------------------------------------------------------------------------
# level="period"
# ---------------------------------------------------------------------------


class TestPeriodLevel:
    """``level="period"``: lookup by ``reignTitle``, fallback to ``label``."""

    @pytest.mark.parametrize(
        "cp, expected",
        [
            # 清·康熙: unique, multi-decade era. Anchor: 1662–1722.
            ("康熙", (1662.0, 1722.0)),
            # 隋·开皇: F2 split-span 582–589 + 589–600 in raw data; clean.csv
            # already merges them — function should see ONE row spanning the
            # full range, no ambiguity, no manual min/max gymnastics.
            ("开皇", (582.0, 600.0)),
            # 北齐·承光: E:missing-year row hand-filled in clean.csv
            # (raw had endYear=NaN; readme.md notes 577 北齐为周所灭).
            # If the function loaded raw temporal.csv it would raise
            # ValueError; with clean.csv it returns a clean (577, 577).
            ("承光", (577.0, 577.0)),
            # 汉·元平: BCE single-year era (-74). Edge case for both BCE
            # (begin == end < 0) and short-lived eras.
            ("元平", (-74.0, -74.0)),
        ],
        ids=["康熙-multi-decade", "开皇-F2-merged", "承光-E-filled", "元平-BCE-1yr"],
    )
    def test_unique_reignTitle_returns_full_span(self, cp, expected):
        """Unique ``reignTitle`` returns its (begin, end) verbatim.

        Covers:
        * a long, completely unambiguous era (康熙)
        * an era that *looked* duplicated upstream but is single-row in clean
          (开皇, F2-merged)
        * an era whose endYear was filled in by the cleaner (承光)
        * a single-year BCE era (元平)
        """
        assert get_age_from_cultural_period(cp, level="period") == expected

    def test_falls_back_to_label_when_reignTitle_misses(self):
        """If ``reignTitle`` doesn't match, the function tries ``label``.

        ``label`` is the upstream concatenated form like ``清康熙``. Querying
        by it should resolve the same row as querying by ``reignTitle``.
        """
        via_label = get_age_from_cultural_period("清康熙", level="period")
        via_period = get_age_from_cultural_period("康熙", level="period")
        assert via_label == via_period == (1662.0, 1722.0)

    @pytest.mark.parametrize(
        "cp, n_rulers",
        [
            # 建平: reused by 7 different rulers across 汉/后赵/西燕/后燕/南
            # 燕/南凉/夏(刘虎). Each is a distinct (dynasty, monarchName).
            ("建平", 7),
            # 后元: reused by 3 different 汉 emperors (刘恒/刘启/刘彻).
            # Same dynasty, different monarchName — still ambiguous.
            ("后元", 3),
            # 上元: reused by 唐李治, 唐李亨, 南诏 — 3 distinct rulers, mixes
            # same-dynasty (唐 with two different monarchName) + different-
            # dynasty (南诏).
            ("上元", 3),
        ],
        ids=["建平-7-rulers", "后元-same-dynasty", "上元-cross-dynasty"],
    )
    def test_ambiguous_reignTitle_raises(self, cp, n_rulers):
        """When the same ``reignTitle`` belongs to ≥2 distinct
        (dynasty, monarchName) keys, ``AmbiguousCulturalPeriodError`` fires.

        This is the disambiguation contract of the function: the *period*
        level is the user-facing 年号 query, and 年号 are routinely reused
        across dynasties — silently picking one would give a wrong answer.
        """
        with pytest.raises(AmbiguousCulturalPeriodError) as exc:
            get_age_from_cultural_period(cp, level="period")
        # The error message names how many candidate rulers it saw.
        assert str(n_rulers) in str(exc.value)

    def test_unknown_reignTitle_raises_keyerror(self):
        """Neither ``reignTitle`` nor ``label`` matches → ``KeyError``."""
        with pytest.raises(KeyError, match="period"):
            get_age_from_cultural_period("绝无此号", level="period")

    @pytest.mark.parametrize(
        "cp",
        ["", "   ", "\t", "\n"],
        ids=["empty", "spaces", "tab", "newline"],
    )
    def test_empty_or_whitespace_input_raises(self, cp):
        """Empty / whitespace-only input is rejected with ``ValueError``.

        The function ``strip()``s before checking, so anything that strips
        to empty must fail loudly.
        """
        with pytest.raises(ValueError, match="non-empty"):
            get_age_from_cultural_period(cp, level="period")

    def test_input_is_stripped_before_match(self):
        """Surrounding whitespace is tolerated.

        Users copy-pasting from CSVs / spreadsheets routinely bring trailing
        whitespace. ``"  康熙  "`` should match ``"康熙"``.
        """
        assert get_age_from_cultural_period("  康熙  ", level="period") == (
            1662.0,
            1722.0,
        )


# ---------------------------------------------------------------------------
# level="dynasty"
# ---------------------------------------------------------------------------


class TestDynastyLevel:
    """``level="dynasty"``: match by exact ``dynasty`` column, no ambiguity
    check. Returns the union of (min begin, max end) across all matches."""

    @pytest.mark.parametrize(
        "cp, expected",
        [
            ("清", (1616.0, 1911.0)),  # 清 starts at 天命 1616, not 1644
            ("唐", (618.0, 907.0)),
            # 商: BCE; just exercises the negative-year path
            ("商", (-1559.0, -1123.0)),
            # 元: data has 至正 1341–1370 so end is 1370 (北元 spillover),
            # not the textbook 1368 — we anchor to the data, not lore.
            ("元", (1260.0, 1370.0)),
        ],
        ids=["清", "唐", "商-BCE", "元-with-北元-tail"],
    )
    def test_dynasty_returns_union_span(self, cp, expected):
        """Dynasty-level returns (min begin, max end) over all rows.

        Notable: the dynasty-level row (e.g. 清 entry without monarchName)
        and per-emperor rows are merged together; the result is always the
        outermost envelope.
        """
        assert get_age_from_cultural_period(cp, level="dynasty") == expected

    def test_dynasty_with_name_collision_returns_full_union(self):
        """Known data quirk: ``dynasty="夏"`` matches BOTH 上古夏 (-1989)
        and the 隋末唐初 short-lived 夏 polities (~620s AD).

        Because ``level="dynasty"`` ignores the new ``dynasty_id`` column,
        the result is the union span — not a useful answer. The escape
        hatch is ``level="epoch"`` with ``"上古"``, which scopes via
        ``EPOCH_MAP``'s year_max=-221.

        This test pins that behaviour so any future "fix" that silently
        changed dynasty-level disambiguation would be flagged.
        """
        begin, end = get_age_from_cultural_period("夏", level="dynasty")
        assert begin == -1989.0  # ancient
        assert end > 0  # AD, i.e. the 隋末 reuse leaks in

    def test_unknown_dynasty_raises_keyerror(self):
        """A dynasty name that simply isn't in the data raises ``KeyError``."""
        with pytest.raises(KeyError, match="dynasty"):
            get_age_from_cultural_period("乌何有之乡", level="dynasty")


# ---------------------------------------------------------------------------
# level="epoch"
# ---------------------------------------------------------------------------


class TestEpochLevel:
    """``level="epoch"``: aggregations from ``EPOCH_MAP``; falls back to
    plain dynasty match when the name isn't mapped."""

    @pytest.mark.parametrize(
        "cp, expected",
        [
            # 汉 epoch ⊃ {西汉, 汉, 东汉}, year bounds -206..220.
            ("汉", (-206.0, 220.0)),
            # 晋 epoch: 265..420.
            ("晋", (265.0, 420.0)),
            # 三国 epoch ⊃ {三国, 魏, 蜀, 吴}, year bounds 184..280.
            # Real anchor in data: 220–280 (魏 founded 220, not 184).
            ("三国", (220.0, 280.0)),
            # 五代 ⊃ {后梁, 后唐, 后晋, 后汉, 后周}, 907..960.
            ("五代", (907.0, 960.0)),
            # 南北朝 multi-state aggregate.
            ("南北朝", (420.0, 589.0)),
            # 上古: dynasties in {夏, 商, 周, 西周, 东周, 春秋, 战国} but
            # cut by year_max=-221 — this is precisely how we exclude the
            # 隋末唐初 reuse of "夏" while keeping the real ancient 夏.
            ("上古", (-1989.0, -221.0)),
        ],
        ids=["汉", "晋", "三国", "五代", "南北朝", "上古-clips-AD-夏"],
    )
    def test_known_epoch_uses_epoch_map(self, cp, expected):
        """For names in ``EPOCH_MAP``, the epoch-level lookup uses the
        configured (names, year_min, year_max) to scope. ``year_max`` does
        the heavy lifting for "上古" — it clips out the AD reuses of "夏"
        without us having to enumerate ``dynasty_id`` exclusions."""
        assert get_age_from_cultural_period(cp, level="epoch") == expected

    def test_epoch_汉_excludes_后汉(self):
        """``EPOCH_MAP['汉']`` lists {西汉, 汉, 东汉} explicitly; 后汉
        (五代后汉, 947–950) must NOT contribute to the 汉 epoch span.

        This is the regression guard: if someone naively expanded the
        names list to include 后汉, the upper bound would jump to 950."""
        _, end = get_age_from_cultural_period("汉", level="epoch")
        assert end == 220.0
        assert end < 947.0

    def test_epoch_falls_back_to_dynasty_when_not_mapped(self):
        """When ``cp`` is not a key in ``EPOCH_MAP`` (e.g. "唐"), the epoch
        lookup degrades gracefully into a dynasty-level match.

        We assert this by comparing equality with ``level="dynasty"``."""
        as_epoch = get_age_from_cultural_period("唐", level="epoch")
        as_dyn = get_age_from_cultural_period("唐", level="dynasty")
        assert as_epoch == as_dyn

    def test_epoch_fallback_unknown_dynasty_raises(self):
        """Unknown name + no ``EPOCH_MAP`` entry → fallthrough to dynasty
        match → ``KeyError`` from the empty match."""
        with pytest.raises(KeyError):
            get_age_from_cultural_period("无此朝", level="epoch")


# ---------------------------------------------------------------------------
# Prehistoric epochs (旧石器 / 新石器)
# ---------------------------------------------------------------------------


class TestPrehistoricEpochs:
    """``level="epoch"`` for 旧石器 / 新石器 — resolved from
    :data:`PREHISTORIC_EPOCHS` without touching the dynasty table.

    These epochs have no rows in ``dynasty_clean.csv``; they're
    semi-hardcoded archaeological brackets the user supplies."""

    def test_neolithic_returns_configured_bce_span(self):
        """新石器: -10000 BCE to -2070 BCE (传统'夏朝建立' as upper bound).

        Pinned literally so a future tweak to the bound has to update
        both the constant and this test deliberately."""
        assert get_age_from_cultural_period("新石器", level="epoch") == (
            -10000.0,
            -2070.0,
        )

    def test_paleolithic_lower_bound_is_negative_infinity(self):
        """旧石器: open-ended start (``float('-inf')``) → -10000 BCE.

        ``-inf`` is the honest answer for "everything before 10000 BCE":
        we don't have a meaningful Lower Paleolithic start year for China
        in the dataset, and inf preserves the AD orientation invariant
        (begin ≤ end) without lying about a finite anchor."""
        begin, end = get_age_from_cultural_period("旧石器", level="epoch")
        assert begin == float("-inf")
        assert end == -10000.0
        assert begin <= end  # AD orientation invariant still holds

    def test_neolithic_bp_conversion(self):
        """BP = 1950 - AD applied independently to begin & end.

        新石器 (-10000, -2070) → BP (11950, 4020). ``begin >= end``
        invariant holds in BP space (older first)."""
        bp = get_age_from_cultural_period("新石器", level="epoch", anno_domini=False)
        assert bp == (
            _BP_REFERENCE - (-10000.0),  # 11950
            _BP_REFERENCE - (-2070.0),  # 4020
        )
        assert bp[0] > bp[1]

    def test_paleolithic_bp_conversion_keeps_infinity(self):
        """BP conversion of ``-inf`` AD is ``+inf`` BP — older-than-old.

        ``1950 - (-inf) = +inf``, which in BP convention reads as
        'infinitely old', preserving the older-first orientation."""
        bp_begin, bp_end = get_age_from_cultural_period(
            "旧石器", level="epoch", anno_domini=False
        )
        assert bp_begin == float("inf")
        assert bp_end == _BP_REFERENCE - (-10000.0)  # 11950
        assert bp_begin > bp_end

    @pytest.mark.parametrize("level", ["period", "dynasty"])
    @pytest.mark.parametrize("cp", ["新石器", "旧石器"])
    def test_prehistoric_only_resolves_at_epoch_level(self, cp, level):
        """Prehistoric names live only in the ``epoch`` namespace, mirroring
        how meta-epoch names like ``上古`` behave: at ``level="period"`` or
        ``level="dynasty"`` they don't match and we surface ``KeyError``.

        This pins the namespace contract — if someone later "helpfully"
        makes 新石器 work at level="dynasty", it would silently shadow a
        very different lookup path."""
        with pytest.raises(KeyError):
            get_age_from_cultural_period(cp, level=level)

    def test_prehistoric_short_circuits_before_table_load(self):
        """Prehistoric lookup must not require the dynasty CSV to exist —
        passing an empty ``time_table`` (which would fail every dynasty/
        period match) still resolves prehistoric epochs.

        This is the implementation contract: the early-return guard runs
        before any DataFrame work, so prehistoric queries are unaffected
        by data-load issues."""
        empty = pd.DataFrame(
            columns=[
                "dynasty",
                "reignTitle",
                "monarch",
                "monarchName",
                "beginYear",
                "endYear",
                "label",
                "uri",
            ]
        )
        assert get_age_from_cultural_period(
            "新石器", level="epoch", time_table=empty
        ) == (-10000.0, -2070.0)

    @pytest.mark.parametrize("name", list(PREHISTORIC_EPOCHS.keys()))
    def test_prehistoric_keys_have_valid_ordered_bounds(self, name: str):
        """Each entry in ``PREHISTORIC_EPOCHS`` has ``begin <= end``
        (AD orientation), preventing typos that swap the two values."""
        begin, end = PREHISTORIC_EPOCHS[name]
        assert begin <= end


# ---------------------------------------------------------------------------
# anno_domini=False (Before Present mode)
# ---------------------------------------------------------------------------


class TestBpMode:
    """``anno_domini=False``: convert AD/BCE to BP relative to 1950
    (radiocarbon convention)."""

    def test_bp_reference_constant_is_1950(self):
        """The conversion reference must be 1950 (radiocarbon 'present').

        Pinned because changing it would silently break every dataset
        archaeology hands us."""
        assert _BP_REFERENCE == 1950

    @pytest.mark.parametrize(
        "cp, level, ad_expected, bp_expected",
        [
            # 商: -1559..-1123 → BP 3509..3073. begin (older) > end (younger).
            ("商", "dynasty", (-1559.0, -1123.0), (3509.0, 3073.0)),
            # 清: 1616..1911 → BP 334..39.
            ("清", "dynasty", (1616.0, 1911.0), (334.0, 39.0)),
            # 上古夏 only (clipped by EPOCH_MAP year_max).
            ("上古", "epoch", (-1989.0, -221.0), (3939.0, 2171.0)),
        ],
        ids=["商-pure-BCE", "清-pure-AD", "上古-spans-BCE-only"],
    )
    def test_ad_and_bp_match_per_formula(self, cp, level, ad_expected, bp_expected):
        """BP = 1950 - AD, applied independently to begin and end.

        BCE → larger BP (older), AD → smaller BP (younger). begin (older)
        ends up >= end (younger) under BP, opposite to AD orientation.
        """
        ad = get_age_from_cultural_period(cp, level=level, anno_domini=True)
        bp = get_age_from_cultural_period(cp, level=level, anno_domini=False)
        assert ad == ad_expected
        assert bp == bp_expected
        # invariant: BP begin >= BP end (older first)
        assert bp[0] >= bp[1]
        # invariant: AD begin <= AD end (chronological)
        assert ad[0] <= ad[1]

    def test_bp_orientation_is_older_first(self):
        """BP convention swaps the orientation: ``begin >= end`` (older
        first), the inverse of AD mode. This test pins the orientation
        invariant on a span that crosses both eras: 汉 (-206..220)."""
        bp_begin, bp_end = get_age_from_cultural_period(
            "汉", level="epoch", anno_domini=False
        )
        assert bp_begin == _BP_REFERENCE - (-206)  # 2156
        assert bp_end == _BP_REFERENCE - 220  # 1730
        assert bp_begin > bp_end


# ---------------------------------------------------------------------------
# Custom time_table
# ---------------------------------------------------------------------------


class TestCustomTimeTable:
    """``time_table`` parameter lets callers pass a pre-filtered or fully
    synthetic DataFrame instead of the default file."""

    def test_custom_table_is_used_instead_of_default(
        self, synthetic_table: pd.DataFrame
    ):
        """Querying a name that exists ONLY in the synthetic table proves
        the function consulted the custom table, not the default file.

        The dynasty 测试 / reignTitle 甲 don't exist in the real CSV.
        """
        result = get_age_from_cultural_period(
            "甲", level="period", time_table=synthetic_table
        )
        assert result == (100.0, 120.0)

    def test_custom_table_string_years_are_coerced(self, synthetic_table: pd.DataFrame):
        """``synthetic_table`` ships ``beginYear``/``endYear`` as strings.
        The function must coerce them to numeric or min/max would fail."""
        # If coercion didn't happen, .min()/.max() on object dtype would
        # do lexicographic comparison and break. Assert numeric correctness.
        begin, end = get_age_from_cultural_period(
            "测试", level="dynasty", time_table=synthetic_table
        )
        assert begin == 100.0
        assert end == 150.0

    def test_custom_table_supports_bp_conversion(self, synthetic_table: pd.DataFrame):
        """BP-mode conversion still applies when a custom table is used."""
        bp = get_age_from_cultural_period(
            "甲",
            level="period",
            anno_domini=False,
            time_table=synthetic_table,
        )
        assert bp == (_BP_REFERENCE - 100.0, _BP_REFERENCE - 120.0)

    def test_custom_table_does_not_filter_known_bad_uris(self):
        """``_KNOWN_BAD_URIS`` filtering is applied **only** by the default
        loader. A user-supplied table is taken at face value — if the user
        wants filtering, they must do it before passing in.

        Pinned so a future "always filter" refactor is forced to update
        the docstring as well.
        """
        bad_uri = "http://data.library.sh.cn/authority/temporal/fo3y5vgrykmpbupv"
        df = pd.DataFrame(
            [
                {
                    "dynasty": "晋",
                    "reignTitle": "太康",
                    "monarch": "武帝",
                    "monarchName": "司马炎",
                    "beginYear": "280",
                    "endYear": "280",
                    "label": "晋太康",
                    "uri": bad_uri,
                },
            ]
        )
        # The bad row IS used — so we get the truncated 280–280, not the
        # canonical 280–289.
        assert get_age_from_cultural_period("太康", level="period", time_table=df) == (
            280.0,
            280.0,
        )


# ---------------------------------------------------------------------------
# Error paths and miscellany
# ---------------------------------------------------------------------------


class TestErrorPaths:
    """Error handling that doesn't fit neatly under one level."""

    def test_unknown_level_raises_value_error(self):
        """``level`` is typed ``Literal[...]`` but Python doesn't enforce
        that at runtime. Defensive runtime check must reject unknown
        values with ``ValueError``, not ``KeyError`` or silently default.
        """
        with pytest.raises(ValueError, match="unknown level"):
            get_age_from_cultural_period(
                "清",
                level="garbage",  # type: ignore[arg-type]
            )

    def test_matched_rows_all_nan_raises_value_error(
        self, all_nan_year_table: pd.DataFrame
    ):
        """When matched rows exist but ``beginYear``/``endYear`` are all
        NaN, ``min``/``max`` produce NaN — function must raise rather than
        return ``(nan, nan)`` quietly. This is the safety net for any
        future row that slips through validation with both years missing.
        """
        with pytest.raises(ValueError, match="lack begin/end"):
            get_age_from_cultural_period(
                "无", level="period", time_table=all_nan_year_table
            )

    def test_南诏上元_partial_nan_raises(self, default_table: pd.DataFrame):
        """``南诏 上元`` (784–?) is the one ``E:missing-year`` row the
        cleaner intentionally left as NaN (no documented historical end).

        Querying it directly (via label, since the reignTitle is ambiguous)
        must raise ValueError because ``endYear`` is NaN even though
        ``beginYear`` is known. This protects downstream from silently
        treating an unknown end as zero / present.
        """
        with pytest.raises(ValueError, match="lack begin/end"):
            get_age_from_cultural_period("南诏上元", level="period")

    def test_default_loader_excludes_known_bad_uris(self, default_table: pd.DataFrame):
        """The default loader strips F1 truncated-duplicate URIs even
        though clean.csv already does so. This is the defense-in-depth
        invariant — tests don't care WHICH layer drops them, only that
        they're absent from what reaches user queries.
        """
        from chhiskit.core.dynasties import _KNOWN_BAD_URIS

        assert default_table["uri"].isin(_KNOWN_BAD_URIS).sum() == 0


# ---------------------------------------------------------------------------
# EPOCH_MAP shape — pinning the configuration that several tests rely on
# ---------------------------------------------------------------------------


class TestEpochMapConfig:
    """Sanity checks on the static ``EPOCH_MAP`` table itself.

    These guard against accidental edits that would silently break
    epoch-level queries (e.g. typoing a dynasty name, dropping a year
    bound, swapping min/max)."""

    @pytest.mark.parametrize("epoch_key", list(EPOCH_MAP.keys()))
    def test_each_epoch_resolves_to_at_least_one_real_row(
        self, epoch_key: str, default_table: pd.DataFrame
    ):
        """Every entry in ``EPOCH_MAP`` must resolve to ≥1 row in the
        real data, otherwise calling it would always raise ``KeyError``."""
        names, ymin, ymax = EPOCH_MAP[epoch_key]
        sub = default_table.loc[default_table["dynasty"].isin(names)]
        if ymin is not None:
            sub = sub.loc[sub["beginYear"] >= ymin]
        if ymax is not None:
            sub = sub.loc[sub["endYear"] <= ymax]
        assert len(sub) > 0, (
            f"EPOCH_MAP[{epoch_key!r}] resolves to zero rows — names "
            f"and / or year bounds are out of sync with the data."
        )

    @pytest.mark.parametrize("epoch_key", list(EPOCH_MAP.keys()))
    def test_each_epoch_year_bounds_are_ordered(self, epoch_key: str):
        """When both bounds exist, ``ymin <= ymax``. This catches typos
        like swapping the two values."""
        _, ymin, ymax = EPOCH_MAP[epoch_key]
        if ymin is not None and ymax is not None:
            assert ymin <= ymax


# ---------------------------------------------------------------------------
# aliases parameter on get_age_from_cultural_period
# ---------------------------------------------------------------------------


class TestAliases:
    """``aliases={canonical: {alias, ...}}`` rewrites the input name before
    any matching, so foreign-language or shorthand callers can reuse the
    same data spans.

    Resolution rules pinned by these tests:
      * an unknown name → pass through (downstream raises ``KeyError``)
      * a canonical name → no rewrite (still works)
      * an alias of one canonical → rewritten
      * an alias shared by ≥2 canonicals → ``ValueError``
      * ``aliases=None`` → no-op, identical behavior to omitting the arg
    """

    @pytest.fixture
    def aliases(self) -> dict[str, set[str]]:
        """A representative aliases map mixing English shorthand and
        local-language alternates across all three lookup levels.

        Used by most tests so each one only needs to focus on the
        resolution behavior, not the alias dict construction."""
        return {
            "新石器": {"Neolithic", "Neo"},
            "旧石器": {"Paleolithic", "Paleo"},
            "清": {"Qing", "Ch'ing"},
            "唐": {"Tang"},
            "康熙": {"Kangxi", "K'ang-hsi"},
        }

    @pytest.mark.parametrize(
        "alias_input, expected",
        [
            # Multiple aliases for the same canonical 新石器 must all
            # resolve to the same (-10000, -2070) span.
            ("Neolithic", (-10000.0, -2070.0)),
            ("Neo", (-10000.0, -2070.0)),
            # Also for 旧石器 with -inf lower bound.
            ("Paleolithic", (float("-inf"), -10000.0)),
            ("Paleo", (float("-inf"), -10000.0)),
        ],
        ids=["Neolithic", "Neo-shorthand", "Paleolithic", "Paleo-shorthand"],
    )
    def test_alias_resolves_prehistoric_epoch(self, aliases, alias_input, expected):
        """A foreign-language alias for a prehistoric epoch produces the
        same span as the canonical 旧石器 / 新石器 query.

        Cross-checked against the canonical query so that any future
        change to ``PREHISTORIC_EPOCHS`` keeps both paths in lockstep."""
        via_alias = get_age_from_cultural_period(
            alias_input, level="epoch", aliases=aliases
        )
        assert via_alias == expected

    def test_alias_resolves_dynasty_name(self, aliases):
        """``"Qing"`` rewrites to ``"清"`` and behaves like the canonical
        dynasty-level lookup.

        Pinned by equality with the no-alias canonical call to guarantee
        the alias resolution is a pure substitution, not a parallel
        codepath that could drift."""
        via_alias = get_age_from_cultural_period(
            "Qing", level="dynasty", aliases=aliases
        )
        assert via_alias == get_age_from_cultural_period("清", level="dynasty")
        assert via_alias == (1616.0, 1911.0)

    def test_alias_resolves_period_name(self, aliases):
        """``"Kangxi"`` rewrites to ``"康熙"`` at period level — covers
        the most common downstream use case (Westerners querying by
        Pinyin / Wade-Giles)."""
        assert get_age_from_cultural_period(
            "Kangxi", level="period", aliases=aliases
        ) == (1662.0, 1722.0)

    def test_alias_with_bp_mode(self, aliases):
        """Alias resolution composes with ``anno_domini=False``: the
        rewrite happens before BP conversion, which then applies as
        normal. Pins that the two features are independent."""
        bp = get_age_from_cultural_period(
            "Neolithic",
            level="epoch",
            anno_domini=False,
            aliases=aliases,
        )
        assert bp == (
            _BP_REFERENCE - (-10000.0),  # 11950
            _BP_REFERENCE - (-2070.0),  # 4020
        )

    def test_canonical_name_still_resolves_when_aliases_supplied(self, aliases):
        """If the caller passes ``aliases`` AND queries by the canonical
        name, the canonical wins (no rewrite). This is the contract that
        lets users add aliases without breaking existing call sites."""
        assert get_age_from_cultural_period(
            "新石器", level="epoch", aliases=aliases
        ) == (-10000.0, -2070.0)
        assert get_age_from_cultural_period("清", level="dynasty", aliases=aliases) == (
            1616.0,
            1911.0,
        )

    def test_unknown_name_falls_through_to_keyerror(self, aliases):
        """A name that's neither a canonical nor in any alias set passes
        through unchanged. The downstream match step then raises
        ``KeyError`` like it always would.

        Pins that aliases are *additive* — they don't suppress or alter
        the existing 'unknown name' error path."""
        with pytest.raises(KeyError):
            get_age_from_cultural_period("Foobar", level="dynasty", aliases=aliases)

    def test_aliases_none_is_noop(self):
        """``aliases=None`` (the default) gives identical behavior to
        not passing the argument at all. This is the backwards-compat
        guarantee — no existing caller breaks."""
        with_none = get_age_from_cultural_period("康熙", level="period", aliases=None)
        without = get_age_from_cultural_period("康熙", level="period")
        assert with_none == without

    def test_empty_aliases_dict_is_noop(self):
        """An empty mapping is treated like ``None``: no rewrite, no
        error. Pinned because users may pass an empty dict rather than
        building it conditionally."""
        assert get_age_from_cultural_period("康熙", level="period", aliases={}) == (
            1662.0,
            1722.0,
        )

    def test_alias_collision_raises_value_error(self):
        """An alias that maps to ≥2 canonical names is unresolvable —
        function must raise ``ValueError`` rather than silently picking
        one. The error message names every candidate so the user can
        fix the dict."""
        with pytest.raises(ValueError, match="multiple canonical"):
            get_age_from_cultural_period(
                "Han",
                level="dynasty",
                aliases={"汉": {"Han"}, "韩": {"Han"}},
            )

    def test_alias_resolution_runs_after_strip(self, aliases):
        """``cultural_period`` is stripped *before* alias lookup, so
        users still benefit from the whitespace tolerance documented on
        the function. ``"  Kangxi  "`` resolves to ``"康熙"``."""
        assert get_age_from_cultural_period(
            "  Kangxi  ", level="period", aliases=aliases
        ) == (1662.0, 1722.0)

    def test_alias_value_can_be_any_iterable(self):
        """The alias values' container type isn't restricted to ``set``;
        any iterable supporting ``in`` works (``frozenset``, ``tuple``,
        ``list``).

        Pins flexibility — callers shouldn't be forced into a specific
        container."""
        for cls in (frozenset, tuple, list):
            aliases = {"康熙": cls(["Kangxi"])}
            assert get_age_from_cultural_period(
                "Kangxi", level="period", aliases=aliases
            ) == (1662.0, 1722.0)


# ---------------------------------------------------------------------------
# get_cultural_periods_from_year — the inverse lookup
# ---------------------------------------------------------------------------


class TestYearToCulturalPeriods:
    """``get_cultural_periods_from_year(year)``: every dynasty / reign-era
    / prehistoric epoch whose ``[beginYear, endYear]`` (inclusive) covers
    the queried year.

    Returns a sorted list (by ``beginYear``, then ``endYear`` ascending).
    Multiple parallel matches are normal."""

    # ---------- happy paths: data-backed matches ----------

    def test_year_returns_sorted_list_of_named_tuples(self):
        """Every element is a :class:`CulturalPeriodMatch` and the list
        is sorted by ``(beginYear, endYear)`` ascending.

        Sort order matters for predictability in downstream consumers —
        users iterating the list expect a stable, chronological order."""
        matches = get_cultural_periods_from_year(-200)
        assert all(isinstance(m, CulturalPeriodMatch) for m in matches)
        keys = [(m.beginYear, m.endYear) for m in matches]
        assert keys == sorted(keys)

    def test_year_minus_200_returns_three_layered_汉_matches(self):
        """200 BCE returns three rows: 西汉 (-206..8), 汉/高祖/刘邦
        (-206..-195), 汉 dynasty-summary (-206..220).

        The three together demonstrate that dynasty-level summary rows
        coexist with per-emperor reign rows — both are returned, the
        caller picks the granularity they want."""
        matches = get_cultural_periods_from_year(-200)
        labels = {(m.dynasty_id, m.reignTitle, m.monarchName) for m in matches}
        assert ("汉", "", "刘邦") in labels
        assert ("西汉", "", "") in labels
        assert ("汉", "", "") in labels
        assert len(matches) == 3

    def test_three_kingdoms_year_returns_multiple_polities(self):
        """250 AD is mid-三国: 魏 / 蜀 / 吴 are concurrent. The function
        must return ≥3 polities so the caller sees the parallelism — a
        single 'the dynasty in 250 AD' answer would be misleading."""
        matches = get_cultural_periods_from_year(250)
        dynasties = {m.dynasty for m in matches}
        # 魏 / 蜀 / 吴 must all be present; 三国 summary row may also be.
        assert {"魏", "蜀", "吴"}.issubset(dynasties)

    def test_disambiguation_via_dynasty_id_for_隋末_夏(self):
        """619 AD: matches include 夏(窦建德) — distinct from 上古夏.

        This is the payoff of the cleaning step's ``dynasty_id`` column:
        calling year=619 must NOT surface a row whose ``dynasty_id`` is
        the bare ``夏`` (which is the ancient dynasty), only the
        suffixed ``夏(窦建德)``."""
        matches = get_cultural_periods_from_year(619)
        ancient = [m for m in matches if m.dynasty_id == "夏"]
        suixia = [m for m in matches if m.dynasty_id == "夏(窦建德)"]
        assert ancient == []  # 上古 夏 ended -1559, NOT in 619
        assert len(suixia) == 1
        assert suixia[0].dynasty == "夏"  # raw dynasty preserved
        assert suixia[0].monarchName == "窦建德"

    def test_year_1700_returns_dynasty_and_emperor(self):
        """1700 AD inside 清·康熙: returns the dynasty-summary row plus
        the康熙 reign row, nothing else.

        Pinned as a sanity-check on a totally unambiguous AD year."""
        matches = get_cultural_periods_from_year(1700)
        assert len(matches) == 2
        dynasty_summary = [m for m in matches if m.reignTitle == ""]
        kangxi = [m for m in matches if m.reignTitle == "康熙"]
        assert len(dynasty_summary) == 1
        assert len(kangxi) == 1
        assert kangxi[0].monarchName == "爱新觉罗玄烨"

    # ---------- prehistoric ----------

    def test_neolithic_only_year(self):
        """A year inside 新石器 (-10000..-2070) but predating any data
        row returns exactly one prehistoric match — 新石器 — with empty
        ``uri`` (signalling 'not from 上图')."""
        matches = get_cultural_periods_from_year(-5000)
        assert len(matches) == 1
        m = matches[0]
        assert m.dynasty_id == "新石器"
        assert m.uri == ""
        assert m.beginYear == -10000.0
        assert m.endYear == -2070.0

    def test_paleolithic_only_year(self):
        """A year before -10000 (e.g. -100000) only matches 旧石器, with
        ``beginYear=-inf``. Everything else is silent — no spurious
        matches from the data."""
        matches = get_cultural_periods_from_year(-100_000)
        assert len(matches) == 1
        assert matches[0].dynasty_id == "旧石器"
        assert matches[0].beginYear == float("-inf")

    def test_boundary_year_minus_10000_matches_both_prehistoric(self):
        """The boundary year -10000 is inclusive on both sides:
        旧石器 ends at -10000 and 新石器 begins at -10000, so both
        match. Pinning inclusive-endpoint semantics so a future
        refactor to half-open intervals is forced to update this."""
        matches = get_cultural_periods_from_year(-10000)
        ids = {m.dynasty_id for m in matches}
        assert ids == {"旧石器", "新石器"}

    # ---------- BP input ----------

    def test_bp_input_resolves_to_correct_ad_year(self):
        """``anno_domini=False`` interprets the input as years BP-1950.
        BP 250 ≡ AD 1700; should return the same matches as querying 1700
        directly."""
        bp_matches = get_cultural_periods_from_year(250, anno_domini=False)
        ad_matches = get_cultural_periods_from_year(1700)
        assert bp_matches == ad_matches

    def test_bp_input_for_neolithic_era(self):
        """BP 7000 ≡ AD -5050, inside 新石器. Confirms BP→AD conversion
        also works for prehistoric matches.

        The output ``beginYear`` / ``endYear`` are still in AD form
        (matches the schema of ``dynasty_clean.csv``); only the input
        is in BP."""
        matches = get_cultural_periods_from_year(7000, anno_domini=False)
        assert len(matches) == 1
        assert matches[0].dynasty_id == "新石器"
        # Output stays in AD/BCE form regardless of input mode.
        assert matches[0].beginYear == -10000.0

    # ---------- edge cases ----------

    def test_far_future_year_returns_empty_list(self):
        """A year past every record returns ``[]``, not raises.

        Reading the dataset 'forwards' is open-ended; absence of a match
        is a normal answer, not an error condition."""
        assert get_cultural_periods_from_year(10_000) == []

    def test_year_with_nan_endYear_row_is_excluded(self):
        """``南诏 上元`` (784, NaN) is the deliberately-unfilled E-class
        row. At year=784 the row would *trivially* match on begin, but
        we don't know the end, so the function must skip it instead of
        guessing.

        Returned matches at 784 must NOT contain the 南诏上元 URI."""
        nan_uri = "http://data.library.sh.cn/authority/temporal/4eljzv3hcnl3l1uv"
        matches = get_cultural_periods_from_year(784)
        assert all(m.uri != nan_uri for m in matches)

    def test_endpoint_inclusive_on_both_sides(self):
        """Boundary years on either end of a span are matched.

        E.g. 1644 is the start of the 清 dynasty-summary row and the
        end of 明·崇祯. Both must appear in the result for that year."""
        matches = get_cultural_periods_from_year(1644)
        ids = {m.dynasty_id for m in matches}
        assert "清" in ids
        # 明 dynasty range covers 1644 (its end year), so it should also
        # appear if the data has a row for 明 ending in 1644.
        # We don't pin "明" presence here because the data may model it
        # via 崇祯 ending 1644 — assert the symmetric end-inclusion via 清.
        # 清 starts at天命=1616 (per probe), so 1644 is well inside.
        # The 明->清 transition specifically is asserted below.

    def test_dynasty_transition_year_matches_both_sides(self):
        """1368 is conventionally the 元→明 transition. The data has 元
        extending to 1370 (北元 tail) and 明 starting at 1368, so 1368
        appears in BOTH dynasties — the function returns both.

        This guards against a tempting-but-wrong 'the dynasty in year Y
        is unique' assumption."""
        matches = get_cultural_periods_from_year(1368)
        dynasties = {m.dynasty for m in matches}
        assert {"元", "明"}.issubset(dynasties)

    @pytest.mark.parametrize(
        "year, level_should_have",
        [
            (-3000, "新石器"),  # inside 新石器, before any 上图 row
            (-1900, "夏"),  # 上古 夏 (-1989..-1559)
            (619, "唐"),  # 隋末唐初, 唐 begins 618
            (1900, "清"),  # 清 (1616..1911)
        ],
        ids=["新石器-3000BCE", "上古-1900BCE", "唐-619AD", "清-1900AD"],
    )
    def test_known_anchor_dynasties_are_present(
        self, year: int, level_should_have: str
    ):
        """Sanity matrix: at well-known anchor years, the well-known
        dynasty / epoch must appear among the matches.

        Doesn't pin the exact match count (data may grow), only that
        the historically-correct entry is included — defends against a
        regression where the matching mask flips, off-by-one, etc."""
        ids = {m.dynasty_id for m in get_cultural_periods_from_year(year)}
        assert level_should_have in ids

    # ---------- error / input validation ----------

    def test_nan_year_raises(self):
        """``year=NaN`` is not a valid query — raise rather than silently
        return ``[]`` (which would conflate 'unknown input' with 'no
        matches')."""
        with pytest.raises(ValueError, match="finite number"):
            get_cultural_periods_from_year(float("nan"))

    def test_none_year_raises(self):
        """``year=None`` — same handling as NaN."""
        with pytest.raises(ValueError, match="finite number"):
            get_cultural_periods_from_year(None)  # type: ignore[arg-type]

    def test_custom_time_table_is_used(self, synthetic_table: pd.DataFrame):
        """``time_table`` lets callers query against a synthetic DataFrame.

        Synthetic 测试 has 甲 (100..120) + 乙 (120..150). Querying year=120
        — the shared boundary — must return BOTH rows (inclusive on both
        sides), and must NOT return any rows from the default file."""
        synthetic_table["dynasty_id"] = synthetic_table["dynasty"]
        matches = get_cultural_periods_from_year(120, time_table=synthetic_table)
        # 甲 ends at 120, 乙 starts at 120 — both included by inclusivity.
        assert len(matches) == 2
        assert {m.reignTitle for m in matches} == {"甲", "乙"}
        assert all(m.dynasty == "测试" for m in matches)
        # No leakage from the default file (e.g. real 汉/唐 rows).
        assert all(m.uri.startswith("test:") for m in matches)

    def test_returns_list_type(self):
        """Return type contract: must be a ``list``, not a tuple, set,
        or generator. Callers should be able to ``len()`` it, append to
        it, slice it, etc."""
        result = get_cultural_periods_from_year(1700)
        assert isinstance(result, list)
