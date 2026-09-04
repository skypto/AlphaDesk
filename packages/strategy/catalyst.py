from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from packages.domain.options import OptionStructure, StructureType
from packages.domain.workflow import (
    CatalystFeatures,
    Direction,
    NoTrade,
    RankedCandidate,
    Signal,
    TradeIdea,
)


def _clamp(value: Decimal, low: Decimal, high: Decimal) -> Decimal:
    return min(max(value, low), high)


def score_signal(features: CatalystFeatures) -> Decimal:
    direction = Decimal("1") if features.sentiment >= 0 else Decimal("-1")
    directional_momentum = _clamp(features.price_momentum * direction, Decimal("-1"), Decimal("1"))
    directional_market = _clamp(
        features.market_confirmation * direction, Decimal("-1"), Decimal("1")
    )
    directional_sector = _clamp(
        features.sector_confirmation * direction, Decimal("-1"), Decimal("1")
    )
    volume = _clamp(
        (features.relative_volume - Decimal("1")) / Decimal("2"), Decimal("0"), Decimal("1")
    )
    normalized = (
        features.catalyst_confidence * Decimal("0.30")
        + abs(features.sentiment) * Decimal("0.15")
        + ((directional_momentum + 1) / 2) * Decimal("0.20")
        + volume * Decimal("0.10")
        + ((directional_market + 1) / 2) * Decimal("0.075")
        + ((directional_sector + 1) / 2) * Decimal("0.075")
        + features.liquidity_score * Decimal("0.10")
    )
    return (normalized * Decimal("100")).quantize(Decimal("0.01"))


class CatalystMomentumStrategy:
    def __init__(
        self, *, minimum_score: Decimal = Decimal("65"), maximum_gap: Decimal = Decimal("12")
    ) -> None:
        self._minimum_score = minimum_score
        self._maximum_gap = maximum_gap

    def evaluate_signal(self, signal: Signal) -> TradeIdea | NoTrade:
        reasons: list[str] = []
        if signal.score < self._minimum_score:
            reasons.append("score_below_threshold")
        if abs(signal.features.gap_percent) > self._maximum_gap:
            reasons.append("move_excessively_extended")
        direction = Direction.BULLISH if signal.features.sentiment > 0 else Direction.BEARISH
        directional_momentum = signal.features.price_momentum * (
            Decimal("1") if direction is Direction.BULLISH else Decimal("-1")
        )
        if directional_momentum <= 0:
            reasons.append("price_action_not_confirming")
        if signal.features.catalyst_confidence < Decimal("0.60"):
            reasons.append("weak_catalyst_confidence")
        if reasons:
            return NoTrade(signal_id=signal.signal_id, reason_codes=tuple(reasons))
        return TradeIdea(
            signal_id=signal.signal_id,
            symbol=signal.symbol,
            direction=direction,
            thesis="High-confidence catalyst with confirming abnormal volume and price momentum.",
            holding_horizon=timedelta(days=10),
            entry_window=timedelta(hours=4),
            exit_logic="Exit at target, stop, catalyst invalidation, or two DTE.",
            confidence=(signal.score / Decimal("100")),
        )

    def rank_candidates(
        self, trade_idea: TradeIdea, structures: tuple[OptionStructure, ...]
    ) -> tuple[RankedCandidate, ...]:
        wanted = (
            StructureType.BULL_CALL_DEBIT_SPREAD
            if trade_idea.direction is Direction.BULLISH
            else StructureType.BEAR_PUT_DEBIT_SPREAD
        )
        ranked: list[RankedCandidate] = []
        for structure in structures:
            if structure.structure_type is not wanted or structure.max_profit is None:
                continue
            reward_risk = structure.max_profit / structure.max_loss
            spread_cost = sum(
                (leg.contract.quote.spread_ratio or Decimal("1")) for leg in structure.legs
            ) / Decimal(len(structure.legs))
            score = (reward_risk * Decimal("50") - spread_cost * Decimal("100")).quantize(
                Decimal("0.0001")
            )
            ranked.append(
                RankedCandidate(
                    trade_idea_id=trade_idea.trade_idea_id,
                    structure=structure,
                    rank_score=score,
                    rank_components={"reward_risk": reward_risk, "spread_cost": spread_cost},
                )
            )
        return tuple(
            sorted(
                ranked, key=lambda candidate: (-candidate.rank_score, str(candidate.structure_id))
            )
        )
