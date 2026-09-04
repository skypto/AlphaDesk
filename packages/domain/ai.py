from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Citation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: str = Field(min_length=1)
    claim: str = Field(min_length=1)


class AIContextReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    facts: tuple[str, ...]
    interpretations: tuple[str, ...]
    assumptions: tuple[str, ...]
    catalyst_summary: str
    signal_consistent: bool
    confidence: Decimal = Field(ge=0, le=1)
    reasons: tuple[str, ...] = Field(min_length=1)
    citations: tuple[Citation, ...] = Field(min_length=1)


class DevilsAdvocateReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    alternative_explanations: tuple[str, ...]
    priced_in_risk: str
    extension_risk: str
    contradictory_evidence: tuple[str, ...]
    portfolio_overlap: str
    liquidity_concerns: tuple[str, ...]
    reject_trade: bool
    confidence: Decimal = Field(ge=0, le=1)
    reasons: tuple[str, ...] = Field(min_length=1)
    citations: tuple[Citation, ...] = Field(min_length=1)


class Recommendation(StrEnum):
    PROCEED_TO_STRUCTURE_SELECTION = "PROCEED_TO_STRUCTURE_SELECTION"
    NO_TRADE = "NO_TRADE"
    NEEDS_MORE_DATA = "NEEDS_MORE_DATA"


class DecisionReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    recommendation: Recommendation
    confidence: Decimal = Field(ge=0, le=1)
    facts: tuple[str, ...]
    interpretations: tuple[str, ...]
    reasons: tuple[str, ...] = Field(min_length=1)
    citations: tuple[Citation, ...]


class AIWorkflowResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    provider: str
    model: str
    prompt_versions: dict[str, str]
    schema_version: int = 1
    context: AIContextReport | None
    devils_advocate: DevilsAdvocateReport | None
    decision: DecisionReport
    degraded: bool = False
    failure_reason: str | None = None
    completed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def degraded_results_fail_safe(self) -> AIWorkflowResult:
        if self.degraded and self.decision.recommendation is not Recommendation.NEEDS_MORE_DATA:
            raise ValueError("degraded AI workflow must return NEEDS_MORE_DATA")
        return self
