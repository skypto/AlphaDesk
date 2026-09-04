from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from packages.domain.workflow import (
    RankedCandidate,
    RiskCheck,
    RiskDecision,
    RiskDecisionValue,
)


class RiskPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: str = "1"
    max_planned_loss_per_trade_pct_equity: Decimal = Field(default=Decimal("0.50"), gt=0)
    max_total_open_planned_loss_pct_equity: Decimal = Field(default=Decimal("4.0"), gt=0)
    max_underlying_risk_concentration_pct: Decimal = Field(default=Decimal("10.0"), gt=0)
    daily_loss_halt_pct_equity: Decimal = Field(default=Decimal("2.0"), gt=0)
    portfolio_drawdown_halt_pct: Decimal = Field(default=Decimal("10.0"), gt=0)
    max_concurrent_option_structures: int = Field(default=8, ge=1)
    max_abs_portfolio_delta: Decimal = Field(default=Decimal("5000"), gt=0)
    max_abs_portfolio_gamma: Decimal = Field(default=Decimal("1000"), gt=0)
    max_abs_portfolio_theta: Decimal = Field(default=Decimal("1000"), gt=0)
    max_abs_portfolio_vega: Decimal = Field(default=Decimal("5000"), gt=0)


class RiskContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    paper_equity: Decimal = Field(gt=0)
    open_planned_loss: Decimal = Field(ge=0)
    underlying_open_risk: Decimal = Field(ge=0)
    daily_loss: Decimal = Field(ge=0)
    drawdown_percent: Decimal = Field(ge=0)
    concurrent_option_structures: int = Field(ge=0)
    portfolio_delta: Decimal = Decimal("0")
    portfolio_gamma: Decimal = Decimal("0")
    portfolio_theta: Decimal = Decimal("0")
    portfolio_vega: Decimal = Decimal("0")
    broker_execution_allowed: bool
    duplicate_logical_order: bool = False


class RiskEngine:
    def __init__(self, policy: RiskPolicy) -> None:
        self.policy = policy

    def evaluate(self, candidate: RankedCandidate, context: RiskContext) -> RiskDecision:
        loss = candidate.structure.max_loss
        equity = context.paper_equity
        impact = candidate.structure.greeks
        checks = (
            RiskCheck(
                name="broker_state",
                passed=context.broker_execution_allowed,
                detail="Broker state must be fresh, reconciled, connected, and unblocked.",
            ),
            RiskCheck(
                name="duplicate_logical_order",
                passed=not context.duplicate_logical_order,
                detail="An immutable logical order may be submitted only once.",
            ),
            RiskCheck(
                name="per_trade_loss",
                passed=loss / equity * 100 <= self.policy.max_planned_loss_per_trade_pct_equity,
                detail=f"Planned loss {loss} against paper equity {equity}.",
            ),
            RiskCheck(
                name="total_open_loss",
                passed=(context.open_planned_loss + loss) / equity * 100
                <= self.policy.max_total_open_planned_loss_pct_equity,
                detail="Aggregate planned loss after entry.",
            ),
            RiskCheck(
                name="underlying_concentration",
                passed=(context.underlying_open_risk + loss) / equity * 100
                <= self.policy.max_underlying_risk_concentration_pct,
                detail="Underlying risk after entry.",
            ),
            RiskCheck(
                name="daily_loss_halt",
                passed=context.daily_loss / equity * 100 < self.policy.daily_loss_halt_pct_equity,
                detail="Daily loss must remain below the hard halt.",
            ),
            RiskCheck(
                name="drawdown_halt",
                passed=context.drawdown_percent < self.policy.portfolio_drawdown_halt_pct,
                detail="Portfolio drawdown must remain below the hard halt.",
            ),
            RiskCheck(
                name="position_count",
                passed=context.concurrent_option_structures
                < self.policy.max_concurrent_option_structures,
                detail="Concurrent option structure cap.",
            ),
            RiskCheck(
                name="greeks",
                passed=(
                    abs(context.portfolio_delta + impact.delta)
                    <= self.policy.max_abs_portfolio_delta
                    and abs(context.portfolio_gamma + impact.gamma)
                    <= self.policy.max_abs_portfolio_gamma
                    and abs(context.portfolio_theta + impact.theta)
                    <= self.policy.max_abs_portfolio_theta
                    and abs(context.portfolio_vega + impact.vega)
                    <= self.policy.max_abs_portfolio_vega
                ),
                detail="Post-trade portfolio Greeks must remain within caps.",
            ),
        )
        approved = all(check.passed for check in checks)
        return RiskDecision(
            structure_id=candidate.structure_id,
            decision=RiskDecisionValue.APPROVE if approved else RiskDecisionValue.REJECT,
            checks=checks,
            risk_budget_used=loss / equity,
            calculated_max_loss=loss,
        )
