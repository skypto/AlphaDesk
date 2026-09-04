from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from packages.domain.options import OptionStructure, StructureType


class ProtectionContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    portfolio_delta: Decimal
    drawdown_percent: Decimal = Field(ge=0)
    volatility_percentile: Decimal = Field(ge=0, le=1)
    trend_score: Decimal = Field(ge=-1, le=1)
    concentration_percent: Decimal = Field(ge=0)
    correlation_score: Decimal = Field(ge=0, le=1)


class ProtectionAssessment(BaseModel):
    model_config = ConfigDict(frozen=True)

    activated: bool
    score: Decimal
    reasons: tuple[str, ...]
    preferred_structures: tuple[StructureType, ...]


class PortfolioProtectionStrategy:
    def evaluate(self, context: ProtectionContext) -> ProtectionAssessment:
        deterioration = max(-context.trend_score, Decimal("0"))
        score = (
            min(context.drawdown_percent / Decimal("10"), Decimal("1")) * Decimal("30")
            + context.volatility_percentile * Decimal("20")
            + deterioration * Decimal("20")
            + min(context.concentration_percent / Decimal("20"), Decimal("1")) * Decimal("15")
            + context.correlation_score * Decimal("15")
        ).quantize(Decimal("0.01"))
        reasons = []
        if context.drawdown_percent >= Decimal("5"):
            reasons.append("portfolio_drawdown")
        if context.trend_score <= Decimal("-0.4"):
            reasons.append("trend_deterioration")
        if context.concentration_percent >= Decimal("15"):
            reasons.append("concentration")
        return ProtectionAssessment(
            activated=score >= Decimal("55"),
            score=score,
            reasons=tuple(reasons),
            preferred_structures=(
                StructureType.PROTECTIVE_PUT_SPREAD,
                StructureType.PROTECTIVE_PUT,
            ),
        )

    def rank_candidates(
        self, candidates: tuple[OptionStructure, ...]
    ) -> tuple[OptionStructure, ...]:
        supported = {
            StructureType.PROTECTIVE_PUT,
            StructureType.PROTECTIVE_PUT_SPREAD,
        }
        return tuple(
            sorted(
                (item for item in candidates if item.structure_type in supported),
                key=lambda item: (item.max_loss, item.net_premium_per_share),
            )
        )
