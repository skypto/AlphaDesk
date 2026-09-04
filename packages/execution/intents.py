from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from packages.domain.options import LegSide
from packages.domain.workflow import (
    IntentLeg,
    OrderIntent,
    RankedCandidate,
    RiskDecision,
    RiskDecisionValue,
    stable_client_order_id,
)


def create_order_intent(
    decision: RiskDecision,
    candidate: RankedCandidate,
    *,
    quantity: int = 1,
    limit_price: Decimal | None = None,
    execution_policy: str = "LIMIT_AT_CALCULATED_NET_V1",
    created_at: datetime | None = None,
) -> OrderIntent:
    if decision.structure_id != candidate.structure_id:
        raise ValueError("Risk decision does not belong to candidate")
    if decision.decision is not RiskDecisionValue.APPROVE:
        raise ValueError("Rejected risk decision cannot produce OrderIntent")
    if quantity != candidate.structure.quantity:
        raise ValueError("Intent quantity must match risk-evaluated structure quantity")
    price = limit_price if limit_price is not None else candidate.structure.net_premium_per_share
    legs = tuple(
        IntentLeg(
            symbol=leg.contract.symbol,
            side="buy" if leg.side is LegSide.LONG else "sell",
            ratio=leg.ratio,
        )
        for leg in candidate.structure.legs
    )
    client_order_id = stable_client_order_id(
        decision.risk_decision_id, legs, quantity, price, "day", execution_policy
    )
    return OrderIntent(
        order_intent_id=uuid4(),
        client_order_id=client_order_id,
        risk_decision_id=decision.risk_decision_id,
        legs=legs,
        quantity=quantity,
        limit_price=price,
        execution_policy=execution_policy,
        created_at=created_at or datetime.now(UTC),
    )
