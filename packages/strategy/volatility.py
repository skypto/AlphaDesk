from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from packages.domain.options import OptionStructure, StructureType


class VolatilityPremiumContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    iv_percentile: Decimal = Field(ge=0, le=1)
    realized_volatility_percentile: Decimal = Field(ge=0, le=1)
    event_risk: bool
    tail_risk_score: Decimal = Field(ge=0, le=1)
    trend_score: Decimal = Field(ge=-1, le=1)


class VolatilityAssessment(BaseModel):
    model_config = ConfigDict(frozen=True)

    eligible: bool
    premium_edge: Decimal
    reason_codes: tuple[str, ...]
    preferred_structure: StructureType | None


class VolatilityPremiumStrategy:
    def evaluate(self, context: VolatilityPremiumContext) -> VolatilityAssessment:
        edge = context.iv_percentile - context.realized_volatility_percentile
        reasons = []
        if edge < Decimal("0.20"):
            reasons.append("insufficient_volatility_premium")
        if context.event_risk:
            reasons.append("event_risk")
        if context.tail_risk_score > Decimal("0.70"):
            reasons.append("tail_risk_elevated")
        eligible = not reasons
        preferred = None
        if eligible:
            preferred = (
                StructureType.BULL_PUT_CREDIT_SPREAD
                if context.trend_score >= 0
                else StructureType.BEAR_CALL_CREDIT_SPREAD
            )
        return VolatilityAssessment(
            eligible=eligible,
            premium_edge=edge,
            reason_codes=tuple(reasons),
            preferred_structure=preferred,
        )

    def rank_candidates(
        self, assessment: VolatilityAssessment, candidates: tuple[OptionStructure, ...]
    ) -> tuple[OptionStructure, ...]:
        if not assessment.eligible or assessment.preferred_structure is None:
            return ()
        filtered = (
            item for item in candidates if item.structure_type is assessment.preferred_structure
        )
        return tuple(
            sorted(
                filtered,
                key=lambda item: (
                    -(item.max_profit or Decimal("0")) / item.max_loss,
                    item.max_loss,
                ),
            )
        )
