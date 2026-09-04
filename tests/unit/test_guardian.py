from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from packages.domain.guardian import (
    GuardianObservation,
    GuardianPolicy,
    GuardianTrigger,
)
from packages.domain.workflow import OrderIntent
from packages.execution.engine import (
    ExecutionBlocked,
    ExecutionEngine,
    InMemoryIntentStore,
)
from packages.guardian.engine import GuardianEngine
from packages.guardian.gate import GuardianExecutionGate
from packages.guardian.store import MemoryGuardianStore
from packages.replay.catalyst import run_catalyst_replay

NOW = datetime(2026, 9, 1, 14, tzinfo=UTC)


def safe_observation(**updates: object) -> GuardianObservation:
    values: dict[str, object] = {
        "observed_at": NOW,
        "latest_market_data_at": NOW,
        "broker_stream_connected": True,
        "broker_reconciled": True,
        "divergence_count": 0,
        "duplicate_order_patterns": 0,
        "risk_policy_breach": False,
        "recent_order_rejections": 0,
        "orders_last_minute": 0,
        "uncovered_short_option_legs": 0,
    }
    values.update(updates)
    return GuardianObservation(**values)


def test_guardian_is_normal_only_when_every_deterministic_check_passes() -> None:
    result = GuardianEngine().evaluate(safe_observation())
    assert not result.halted
    assert result.triggers == ()


def test_injected_failures_activate_every_required_guardian_trigger() -> None:
    result = GuardianEngine(GuardianPolicy()).evaluate(
        safe_observation(
            latest_market_data_at=NOW - timedelta(seconds=16),
            broker_stream_connected=False,
            broker_reconciled=False,
            divergence_count=1,
            duplicate_order_patterns=1,
            risk_policy_breach=True,
            recent_order_rejections=3,
            orders_last_minute=6,
            uncovered_short_option_legs=1,
        )
    )
    assert result.halted
    assert set(result.triggers) == {
        GuardianTrigger.STALE_MARKET_DATA,
        GuardianTrigger.STREAM_DISCONNECTED,
        GuardianTrigger.STATE_DIVERGENCE,
        GuardianTrigger.DUPLICATE_ORDER_PATTERN,
        GuardianTrigger.RISK_POLICY_BREACH,
        GuardianTrigger.REPEATED_ORDER_REJECTIONS,
        GuardianTrigger.ABNORMAL_ORDER_RATE,
        GuardianTrigger.UNCOVERED_OPTION_EXPOSURE,
    }
    assert result.pause_new_intents
    assert result.cancel_eligible_open_orders
    assert result.require_reconciliation


class NeverCalledAdapter:
    async def submit_order(self, order: object) -> Any:
        raise AssertionError(f"Submission must be blocked: {order}")


@pytest.mark.asyncio
async def test_manual_halt_blocks_execution_and_recovery_requires_known_broker_state() -> None:
    store = MemoryGuardianStore()
    await store.halt(
        (GuardianTrigger.MANUAL_KILL_SWITCH,),
        "Operator activated paper kill switch.",
    )
    replay = run_catalyst_replay("approved")
    assert replay.order_intent is not None
    intent = OrderIntent.model_validate(replay.order_intent)
    engine = ExecutionEngine(
        NeverCalledAdapter(),  # type: ignore[arg-type]
        InMemoryIntentStore(),
        preflight=GuardianExecutionGate(store),
    )
    with pytest.raises(ExecutionBlocked, match="paper kill switch"):
        await engine.execute(intent)
    with pytest.raises(RuntimeError, match="known reconciled broker state"):
        await store.recover(broker_state_known=False)
    recovered = await store.recover(broker_state_known=True)
    assert recovered.execution_allowed
