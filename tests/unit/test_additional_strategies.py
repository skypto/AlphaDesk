from __future__ import annotations

from decimal import Decimal

from packages.domain.options import StructureType
from packages.strategy.protection import PortfolioProtectionStrategy, ProtectionContext
from packages.strategy.volatility import VolatilityPremiumContext, VolatilityPremiumStrategy


def test_portfolio_protection_activates_only_after_deterministic_deterioration() -> None:
    strategy = PortfolioProtectionStrategy()
    normal = strategy.evaluate(
        ProtectionContext(
            portfolio_delta=1000,
            drawdown_percent="1",
            volatility_percentile="0.30",
            trend_score="0.4",
            concentration_percent="5",
            correlation_score="0.2",
        )
    )
    stressed = strategy.evaluate(
        ProtectionContext(
            portfolio_delta=3000,
            drawdown_percent="8",
            volatility_percentile="0.90",
            trend_score="-0.8",
            concentration_percent="18",
            correlation_score="0.9",
        )
    )
    assert not normal.activated
    assert stressed.activated
    assert stressed.preferred_structures[0] is StructureType.PROTECTIVE_PUT_SPREAD


def test_volatility_premium_selects_only_defined_risk_credit_spreads() -> None:
    strategy = VolatilityPremiumStrategy()
    bullish = strategy.evaluate(
        VolatilityPremiumContext(
            iv_percentile="0.9",
            realized_volatility_percentile="0.4",
            event_risk=False,
            tail_risk_score="0.3",
            trend_score="0.2",
        )
    )
    bearish = strategy.evaluate(
        VolatilityPremiumContext(
            iv_percentile="0.9",
            realized_volatility_percentile="0.4",
            event_risk=False,
            tail_risk_score="0.3",
            trend_score="-0.2",
        )
    )
    vetoed = strategy.evaluate(
        VolatilityPremiumContext(
            iv_percentile="0.9",
            realized_volatility_percentile="0.4",
            event_risk=True,
            tail_risk_score="0.3",
            trend_score="0.2",
        )
    )
    assert bullish.preferred_structure is StructureType.BULL_PUT_CREDIT_SPREAD
    assert bearish.preferred_structure is StructureType.BEAR_CALL_CREDIT_SPREAD
    assert not vetoed.eligible
    assert "event_risk" in vetoed.reason_codes
    assert bullish.premium_edge == Decimal("0.5")
