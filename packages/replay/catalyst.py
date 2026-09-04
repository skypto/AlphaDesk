from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from packages.domain.options import (
    Greeks,
    LegSide,
    OptionContract,
    OptionLeg,
    OptionQuote,
    OptionType,
    StructureType,
)
from packages.domain.workflow import CatalystFeatures, NoTrade, Signal
from packages.execution.intents import create_order_intent
from packages.options.engine import build_structure
from packages.risk.engine import RiskContext, RiskEngine, RiskPolicy
from packages.strategy.catalyst import CatalystMomentumStrategy, score_signal

ReplayScenario = Literal[
    "approved",
    "no_trade",
    "risk_veto",
    "partial_fill",
    "submission_uncertain",
    "guardian_recovery",
]


class CatalystReplay(BaseModel):
    model_config = ConfigDict(frozen=True)

    scenario: ReplayScenario
    disposition: str
    signal: dict[str, object]
    trade_idea: dict[str, object] | None = None
    candidate: dict[str, object] | None = None
    risk_decision: dict[str, object] | None = None
    order_intent: dict[str, object] | None = None
    audit_timeline: tuple[str, ...]


def _leg(strike: str, side: LegSide, entry: str) -> OptionLeg:
    return OptionLeg(
        side=side,
        entry_price=Decimal(entry),
        contract=OptionContract(
            contract_id=f"fixture-{strike}",
            symbol=f"NVDA260925C{int(Decimal(strike) * 1000):08d}",
            underlying_symbol="NVDA",
            expiration=date(2026, 9, 25),
            strike=Decimal(strike),
            option_type=OptionType.CALL,
            tradable=True,
            quote=OptionQuote(
                bid=Decimal(entry) - Decimal("0.05"),
                ask=Decimal(entry) + Decimal("0.05"),
                bid_size=40,
                ask_size=38,
                quoted_at=datetime(2026, 9, 1, 14, tzinfo=UTC),
                open_interest=2400,
                volume=850,
                implied_volatility=Decimal("0.38"),
                greeks=Greeks(delta="0.50", gamma="0.03", theta="-0.04", vega="0.12"),
            ),
        ),
    )


def run_catalyst_replay(scenario: ReplayScenario) -> CatalystReplay:
    if scenario in {"partial_fill", "submission_uncertain", "guardian_recovery"}:
        base = run_catalyst_replay("approved")
        additions = {
            "partial_fill": (
                "ORDER_SUBMISSION_STARTED",
                "ORDER_ACCEPTED",
                "ORDER_PARTIALLY_FILLED",
            ),
            "submission_uncertain": (
                "ORDER_SUBMISSION_STARTED",
                "ORDER_SUBMISSION_UNCERTAIN",
                "BROKER_RECONCILIATION_STARTED",
            ),
            "guardian_recovery": (
                "GUARDIAN_HALT_ACTIVATED",
                "BROKER_RECONCILIATION_STARTED",
                "BROKER_RECONCILIATION_COMPLETED",
            ),
        }
        dispositions = {
            "partial_fill": "ORDER_PARTIALLY_FILLED",
            "submission_uncertain": "SUBMISSION_UNCERTAIN",
            "guardian_recovery": "RECOVERY_RECONCILED",
        }
        return base.model_copy(
            update={
                "scenario": scenario,
                "disposition": dispositions[scenario],
                "audit_timeline": (*base.audit_timeline, *additions[scenario]),
            }
        )
    weak = scenario == "no_trade"
    features = CatalystFeatures(
        catalyst_confidence="0.40" if weak else "0.91",
        sentiment="0.76",
        relative_volume="3.2",
        price_momentum="0.68",
        gap_percent="17" if weak else "4.2",
        market_confirmation="0.30",
        sector_confirmation="0.52",
        liquidity_score="0.93",
    )
    signal = Signal(
        signal_id=UUID("10000000-0000-0000-0000-000000000001"),
        symbol="NVDA",
        observed_at=datetime(2026, 9, 1, 14, tzinfo=UTC),
        features=features,
        score=score_signal(features),
        source_versions={"market": "synthetic-v1", "news": "synthetic-v1"},
    )
    strategy = CatalystMomentumStrategy()
    idea = strategy.evaluate_signal(signal)
    if isinstance(idea, NoTrade):
        return CatalystReplay(
            scenario=scenario,
            disposition="NO_TRADE",
            signal=signal.model_dump(mode="json"),
            audit_timeline=("MARKET_EVENT_INGESTED", "SIGNAL_CREATED", "NO_TRADE_DECISION"),
        )

    idea = idea.model_copy(update={"trade_idea_id": UUID("20000000-0000-0000-0000-000000000001")})
    structure = build_structure(
        StructureType.BULL_CALL_DEBIT_SPREAD,
        (_leg("120", LegSide.LONG, "4.20"), _leg("125", LegSide.SHORT, "2.10")),
    )
    candidate = strategy.rank_candidates(idea, (structure,))[0].model_copy(
        update={"structure_id": UUID("30000000-0000-0000-0000-000000000001")}
    )
    risk = (
        RiskEngine(RiskPolicy())
        .evaluate(
            candidate,
            RiskContext(
                paper_equity="100000",
                open_planned_loss=0,
                underlying_open_risk=0,
                daily_loss=0,
                drawdown_percent=0,
                concurrent_option_structures=0,
                broker_execution_allowed=scenario != "risk_veto",
            ),
        )
        .model_copy(
            update={
                "risk_decision_id": UUID("40000000-0000-0000-0000-000000000001"),
                "created_at": datetime(2026, 9, 1, 14, 0, 1, tzinfo=UTC),
            }
        )
    )
    timeline = (
        "MARKET_EVENT_INGESTED",
        "SIGNAL_CREATED",
        "TRADE_IDEA_CREATED",
        "STRUCTURE_CANDIDATES_CREATED",
        "STRUCTURE_SELECTED",
        "RISK_APPROVED" if risk.decision == "APPROVE" else "RISK_REJECTED",
    )
    if risk.decision != "APPROVE":
        return CatalystReplay(
            scenario=scenario,
            disposition="RISK_REJECTED",
            signal=signal.model_dump(mode="json"),
            trade_idea=idea.model_dump(mode="json"),
            candidate=candidate.model_dump(mode="json"),
            risk_decision=risk.model_dump(mode="json"),
            audit_timeline=timeline,
        )
    intent = create_order_intent(
        risk,
        candidate,
        created_at=datetime(2026, 9, 1, 14, 0, 1, tzinfo=UTC),
    ).model_copy(update={"order_intent_id": UUID("50000000-0000-0000-0000-000000000001")})
    return CatalystReplay(
        scenario=scenario,
        disposition="ORDER_INTENT_CREATED",
        signal=signal.model_dump(mode="json"),
        trade_idea=idea.model_dump(mode="json"),
        candidate=candidate.model_dump(mode="json"),
        risk_decision=risk.model_dump(mode="json"),
        order_intent=intent.model_dump(mode="json"),
        audit_timeline=(*timeline, "ORDER_INTENT_CREATED"),
    )
