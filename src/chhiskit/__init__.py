"""chhiskit — Chinese History Toolkits.

Bidirectional Chinese-history time mapping built on
`Shanghai Library open data <https://data.library.sh.cn/dynasty/>`_.

Typical usage::

    import chhiskit

    chhiskit.get_age_from_cultural_period("康熙")
    # → (1662.0, 1722.0)

    [m.dynasty_id for m in chhiskit.get_cultural_periods_from_year(250)]
    # → ['三国', '吴', '蜀', '魏']
"""

from chhiskit.core.dynasties import (
    EPOCH_MAP,
    PREHISTORIC_EPOCHS,
    AmbiguousCulturalPeriodError,
    CulturalPeriodMatch,
    get_age_from_cultural_period,
    get_cultural_periods_from_year,
)

__version__ = "0.1.0"

__all__ = [
    "get_age_from_cultural_period",
    "get_cultural_periods_from_year",
    "CulturalPeriodMatch",
    "AmbiguousCulturalPeriodError",
    "EPOCH_MAP",
    "PREHISTORIC_EPOCHS",
    "__version__",
]
