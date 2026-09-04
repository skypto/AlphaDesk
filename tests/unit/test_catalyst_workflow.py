from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from packages.domain.broker import BrokerOrder, OrderSubmission
from packages.domain.options import (
    Greeks,
    LegSide,
    OptionContract,
    OptionLeg,
    OptionQuote,
    OptionType,
    StructureType,
)
from packages.domain.workflow import (
    CatalystFeatures,
    NoTrade,
    OrderIntent,
    RankedCandidate,
    RiskDecision,
    Signal,
)
from packages.execution.engine import (
    DuplicateSubmission,
    ExecutionEngine,
    ExecutionState,
    InMemoryIntentStore,
)
from packages.execution.intents import create_order_intent
from packages.options.engine import build_structure
from packages.risk.engine import RiskContext, RiskEngine, RiskPolicy
from packages.strategy.catalyst import CatalystMomentumStrategy, score_signal


def features(**updates: object) -> CatalystFeatures:
    values: dict[str, object] = {
        "catalyst_confidence": "0.90",
        "sentiment": "0.80",
        "relative_volume": "3.0",
        "price_momentum": "0.70",
        "gap_percent": "4.0",
        "market_confirmation": "0.30",
        "sector_confirmation": "0.50",
        "liquidity_score": "0.90",
    }
    values.update(updates)
    return CatalystFeatures(**values)


def signal_for(features_: CatalystFeatures) -> Signal:
    return Signal(
        symbol="XYZ",
        observed_at=datetime(2026, 9, 1, 14, tzinfo=UTC),
        features=features_,
        score=score_signal(features_),
        source_versions={"market": "fixture-v1", "news": "fixture-v1"},
    )


def option_leg(strike: str, side: LegSide, price: str) -> OptionLeg:
    return OptionLeg(
        side=side,
        entry_price=Decimal(price),
        contract=OptionContract(
            contract_id=f"id-{strike}",
            symbol=f"XYZ260925C{int(Decimal(strike) * 1000):08d}",
            underlying_symbol="XYZ",
            expiration=date(2026, 9, 25),
            strike=Decimal(strike),
            option_type=OptionType.CALL,
            tradable=True,
            quote=OptionQuote(
                bid="2.00",
                ask="2.10",
                bid_size=20,
                ask_size=20,
                quoted_at=datetime(2026, 9, 1, 14, tzinfo=UTC),
                open_interest=500,
                greeks=Greeks(delta="0.50", gamma="0.02", theta="-0.03", vega="0.10"),
            ),
        ),
    )


def approved_workflow() -> tuple[RankedCandidate, RiskDecision, OrderIntent]:
    strategy = CatalystMomentumStrategy()
    idea = strategy.evaluate_signal(signal_for(features()))
    assert not isinstance(idea, NoTrade)
    structure = build_structure(
        StructureType.BULL_CALL_DEBIT_SPREAD,
        (
            option_leg("100", LegSide.LONG, "3.00"),
            option_leg("105", LegSide.SHORT, "1.50"),
        ),
    )
    candidate = strategy.rank_candidates(idea, (structure,))[0]
    decision = RiskEngine(RiskPolicy()).evaluate(
        candidate,
        RiskContext(
            paper_equity="100000",
            open_planned_loss=0,
            underlying_open_risk=0,
            daily_loss=0,
            drawdown_percent=0,
            concurrent_option_structures=0,
            broker_execution_allowed=True,
        ),
    )
    return candidate, decision, create_order_intent(decision, candidate)


def test_catalyst_signal_produces_ranked_approved_immutable_intent() -> None:
    candidate, decision, intent = approved_workflow()
    assert decision.decision == "APPROVE"
    assert intent.client_order_id.startswith("ad-")
    assert intent.limit_price == Decimal("1.50")
    second = create_order_intent(
        decision,
        candidate,
        created_at=datetime(2026, 9, 1, 15, tzinfo=UTC),
    )
    assert second.order_intent_id != intent.order_intent_id
    assert second.client_order_id == intent.client_order_id


def test_weak_or_extended_signal_deterministically_returns_no_trade() -> None:
    weak = signal_for(features(catalyst_confidence="0.40", gap_percent="18"))
    result = CatalystMomentumStrategy().evaluate_signal(weak)
    assert isinstance(result, NoTrade)
    assert "move_excessively_extended" in result.reason_codes
    assert "weak_catalyst_confidence" in result.reason_codes


def test_risk_veto_cannot_create_order_intent() -> None:
    candidate, _, _ = approved_workflow()
    rejected = RiskEngine(RiskPolicy()).evaluate(
        candidate,
        RiskContext(
            paper_equity="100000",
            open_planned_loss=0,
            underlying_open_risk=0,
            daily_loss=0,
            drawdown_percent=0,
            concurrent_option_structures=0,
            broker_execution_allowed=False,
        ),
    )
    with pytest.raises(ValueError, match="Rejected risk decision"):
        create_order_intent(rejected, candidate)


class FakeAdapter:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.submissions = 0

    async def submit_order(self, order: OrderSubmission) -> BrokerOrder:
        self.submissions += 1
        if self.fail:
            raise TimeoutError("ambiguous timeout")
        now = datetime(2026, 9, 1, 14, tzinfo=UTC)
        return BrokerOrder(
            broker_order_id="broker-1",
            client_order_id=order.client_order_id,
            status="accepted",
            asset_class="us_option",
            order_type="limit",
            order_class="mleg",
            time_in_force="day",
            filled_quantity=0,
            created_at=now,
        )

    async def get_order(self, **kwargs: object) -> BrokerOrder | None:
        return None


@pytest.mark.asyncio
async def test_duplicate_submission_is_impossible() -> None:
    _, _, intent = approved_workflow()
    adapter = FakeAdapter()
    store = InMemoryIntentStore()
    engine = ExecutionEngine(adapter, store)  # type: ignore[arg-type]
    await engine.execute(intent)
    with pytest.raises(DuplicateSubmission):
        await engine.execute(intent)
    assert adapter.submissions == 1


@pytest.mark.asyncio
async def test_timeout_becomes_submission_uncertain_without_resubmit() -> None:
    _, _, intent = approved_workflow()
    adapter = FakeAdapter(fail=True)
    store = InMemoryIntentStore()
    engine = ExecutionEngine(adapter, store)  # type: ignore[arg-type]
    with pytest.raises(TimeoutError):
        await engine.execute(intent)
    assert await store.get_state(intent.client_order_id) is ExecutionState.SUBMISSION_UNCERTAIN
    with pytest.raises(DuplicateSubmission):
        await engine.execute(intent)
    assert adapter.submissions == 1
