from __future__ import annotations

from datetime import UTC

from packages.domain.guardian import (
    GuardianEvaluation,
    GuardianObservation,
    GuardianPolicy,
    GuardianTrigger,
)


class GuardianEngine:
    def __init__(self, policy: GuardianPolicy | None = None) -> None:
        self.policy = policy or GuardianPolicy()

    def evaluate(self, observation: GuardianObservation) -> GuardianEvaluation:
        triggers: list[GuardianTrigger] = []
        if observation.latest_market_data_at is None:
            triggers.append(GuardianTrigger.STALE_MARKET_DATA)
        else:
            age = (
                observation.observed_at.astimezone(UTC)
                - observation.latest_market_data_at.astimezone(UTC)
            ).total_seconds()
            if age < 0 or age > self.policy.max_market_data_age_seconds:
                triggers.append(GuardianTrigger.STALE_MARKET_DATA)
        if not observation.broker_stream_connected:
            triggers.append(GuardianTrigger.STREAM_DISCONNECTED)
        if not observation.broker_reconciled or observation.divergence_count > 0:
            triggers.append(GuardianTrigger.STATE_DIVERGENCE)
        if observation.duplicate_order_patterns > 0:
            triggers.append(GuardianTrigger.DUPLICATE_ORDER_PATTERN)
        if observation.risk_policy_breach:
            triggers.append(GuardianTrigger.RISK_POLICY_BREACH)
        if observation.recent_order_rejections >= self.policy.max_recent_order_rejections:
            triggers.append(GuardianTrigger.REPEATED_ORDER_REJECTIONS)
        if observation.orders_last_minute > self.policy.max_orders_per_minute:
            triggers.append(GuardianTrigger.ABNORMAL_ORDER_RATE)
        if observation.uncovered_short_option_legs > 0:
            triggers.append(GuardianTrigger.UNCOVERED_OPTION_EXPOSURE)
        halted = bool(triggers)
        return GuardianEvaluation(
            halted=halted,
            triggers=tuple(triggers),
            pause_new_intents=halted,
            cancel_eligible_open_orders=halted,
            require_reconciliation=halted,
        )
