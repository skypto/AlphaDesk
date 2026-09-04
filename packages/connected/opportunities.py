from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from alpaca.data.enums import DataFeed
from alpaca.data.historical import NewsClient, StockHistoricalDataClient
from alpaca.data.requests import NewsRequest, StockBarsRequest, StockSnapshotRequest
from alpaca.data.timeframe import TimeFrame
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from packages.broker.projections import PostgresBrokerProjectionStore
from packages.broker.reconciliation import BrokerExecutionGate
from packages.database.models import ConnectedOpportunityRecord, ConnectedScanRunRecord
from packages.domain.options import LegSide, LiquidityPolicy, OptionLeg, OptionType, StructureType
from packages.domain.workflow import CatalystFeatures, NoTrade, Signal
from packages.execution.intents import create_order_intent
from packages.options.alpaca_adapter import AlpacaOptionChainAdapter, OptionChainQuery
from packages.options.engine import build_structure
from packages.options.liquidity import evaluate_contract
from packages.risk.engine import RiskContext, RiskEngine, RiskPolicy
from packages.strategy.catalyst import CatalystMomentumStrategy, score_signal

POSITIVE_WORDS = frozenset(
    {"beats", "beat", "raises", "raised", "approval", "approved", "record", "growth", "wins"}
)
NEGATIVE_WORDS = frozenset(
    {"misses", "miss", "cuts", "cut", "lawsuit", "probe", "downgrade", "recall", "warning"}
)
CATALYST_WORDS = (
    POSITIVE_WORDS
    | NEGATIVE_WORDS
    | {
        "earnings",
        "guidance",
        "merger",
        "acquisition",
        "contract",
        "fda",
    }
)


class ConnectedAnalysis(BaseModel):
    model_config = ConfigDict(frozen=True)

    opportunity_id: UUID
    scan_run_id: UUID | None = None
    symbol: str
    disposition: str
    source: str = "ALPACA_REAL"
    observed_at: datetime
    expires_at: datetime
    signal: dict[str, Any]
    trade_idea: dict[str, Any] | None = None
    candidate: dict[str, Any] | None = None
    risk_decision: dict[str, Any] | None = None
    order_intent: dict[str, Any] | None = None
    reason_codes: tuple[str, ...] = ()


def _decimal(value: Any, default: str = "0") -> Decimal:
    return Decimal(str(default if value is None else value))


def _clamp(value: Decimal, low: Decimal = Decimal("-1"), high: Decimal = Decimal("1")) -> Decimal:
    return min(max(value, low), high)


def _news_items(raw: Any) -> list[Any]:
    data = getattr(raw, "data", raw)
    if isinstance(data, dict):
        values: list[Any] = []
        for item in data.values():
            values.extend(item if isinstance(item, list) else [item])
        return values
    return list(data) if isinstance(data, (list, tuple)) else []


class ConnectedOpportunityService:
    """Builds Catalyst opportunities exclusively from live Alpaca responses."""

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        workspace_id: UUID,
        api_key: str,
        secret_key: str,
    ) -> None:
        self._sessions = sessions
        self._workspace_id = workspace_id
        self._stock = StockHistoricalDataClient(api_key, secret_key)
        self._news = NewsClient(api_key, secret_key)
        self._options = AlpacaOptionChainAdapter(api_key, secret_key)

    def _features(self, symbol: str) -> tuple[CatalystFeatures, Decimal, datetime]:
        now = datetime.now(UTC)
        symbols = [symbol, "SPY", "QQQ"]
        # IEX is available to Alpaca paper accounts without a paid SIP subscription.
        # Always select it explicitly: alpaca-py may otherwise request recent SIP data
        # and reject an otherwise valid paper-account credential.
        snapshots = self._stock.get_stock_snapshot(
            StockSnapshotRequest(symbol_or_symbols=symbols, feed=DataFeed.IEX)
        )
        stock = snapshots[symbol]
        if (
            stock.latest_trade is None
            or stock.daily_bar is None
            or stock.previous_daily_bar is None
        ):
            raise ValueError("Current and previous market snapshots are required")
        price = _decimal(stock.latest_trade.price)
        daily_open = _decimal(stock.daily_bar.open)
        previous_close = _decimal(stock.previous_daily_bar.close)
        bars = self._stock.get_stock_bars(
            StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Day,
                start=now - timedelta(days=35),
                end=now,
                limit=24,
                feed=DataFeed.IEX,
            )
        )
        bar_values = list(getattr(bars, "data", {}).get(symbol, []))
        average_volume = sum(
            (_decimal(item.volume) for item in bar_values), Decimal("0")
        ) / Decimal(max(len(bar_values), 1))
        relative_volume = _decimal(stock.daily_bar.volume) / max(average_volume, Decimal("1"))
        news_raw = self._news.get_news(
            NewsRequest(
                symbols=symbol,
                start=now - timedelta(hours=36),
                end=now,
                limit=20,
                include_content=False,
            )
        )
        news = _news_items(news_raw)
        words = " ".join(str(getattr(item, "headline", "")) for item in news).lower().split()
        positive = sum(word.strip(".,:;!?()") in POSITIVE_WORDS for word in words)
        negative = sum(word.strip(".,:;!?()") in NEGATIVE_WORDS for word in words)
        sentiment = _clamp(Decimal(positive - negative) / Decimal(max(positive + negative, 1)))
        catalyst_hits = sum(word.strip(".,:;!?()") in CATALYST_WORDS for word in words)
        catalyst_confidence = min(
            Decimal("1"),
            Decimal("0.15")
            + Decimal(len(news)) * Decimal("0.06")
            + Decimal(catalyst_hits) * Decimal("0.08"),
        )

        def confirmation(index_symbol: str) -> Decimal:
            snapshot = snapshots.get(index_symbol)
            if snapshot is None or snapshot.latest_trade is None or snapshot.daily_bar is None:
                return Decimal("0")
            index_open = _decimal(snapshot.daily_bar.open)
            index_price = _decimal(snapshot.latest_trade.price)
            return _clamp((index_price / max(index_open, Decimal("0.01")) - 1) * Decimal("20"))

        features = CatalystFeatures(
            catalyst_confidence=catalyst_confidence,
            sentiment=sentiment,
            relative_volume=max(relative_volume, Decimal("0")),
            price_momentum=_clamp((price / max(daily_open, Decimal("0.01")) - 1) * Decimal("20")),
            gap_percent=(daily_open / max(previous_close, Decimal("0.01")) - 1) * Decimal("100"),
            market_confirmation=confirmation("SPY"),
            sector_confirmation=confirmation("QQQ"),
            liquidity_score=Decimal("0.75"),
        )
        return features, price, now

    async def analyze(self, symbol: str, *, scan_run_id: UUID | None = None) -> ConnectedAnalysis:
        normalized = symbol.strip().upper()
        if not normalized.isalnum() or len(normalized) > 16:
            raise ValueError("Invalid symbol")
        features, underlying_price, now = await asyncio.to_thread(self._features, normalized)
        signal = Signal(
            symbol=normalized,
            observed_at=now,
            features=features,
            score=score_signal(features),
            source_versions={
                "market": "alpaca-real-v1",
                "news": "alpaca-real-v1",
                "options": "alpaca-real-v1",
            },
        )
        strategy = CatalystMomentumStrategy()
        idea = strategy.evaluate_signal(signal)
        opportunity_id = uuid4()
        expires_at = now + timedelta(minutes=2)
        if isinstance(idea, NoTrade):
            result = ConnectedAnalysis(
                opportunity_id=opportunity_id,
                scan_run_id=scan_run_id,
                symbol=normalized,
                disposition="NO_TRADE",
                observed_at=now,
                expires_at=expires_at,
                signal=signal.model_dump(mode="json"),
                reason_codes=idea.reason_codes,
            )
            await self._persist(result)
            return result

        contracts = await self._options.get_chain(
            OptionChainQuery(
                underlying_symbol=normalized,
                expiration_date_gte=date.today() + timedelta(days=14),
                expiration_date_lte=date.today() + timedelta(days=45),
                strike_price_gte=underlying_price * Decimal("0.85"),
                strike_price_lte=underlying_price * Decimal("1.15"),
            )
        )
        wanted_type = OptionType.CALL if idea.direction == "BULLISH" else OptionType.PUT
        policy = LiquidityPolicy(
            supported_underlyings=frozenset({normalized}),
            min_dte=14,
            max_dte=45,
            max_spread_ratio=Decimal("0.20"),
            min_open_interest=25,
            max_quote_age_seconds=120,
        )
        eligible = [
            contract
            for contract in contracts
            if contract.option_type is wanted_type
            and evaluate_contract(
                contract, underlying_price=underlying_price, policy=policy, as_of=now
            ).eligible
        ]
        expirations = sorted({item.expiration for item in eligible})
        if not expirations:
            return await self._unavailable(
                opportunity_id,
                signal,
                idea,
                now,
                "no_eligible_option_chain",
                scan_run_id=scan_run_id,
            )
        selected = sorted(
            (item for item in eligible if item.expiration == expirations[0]),
            key=lambda item: item.strike,
        )
        if len(selected) < 2:
            return await self._unavailable(
                opportunity_id,
                signal,
                idea,
                now,
                "insufficient_vertical_legs",
                scan_run_id=scan_run_id,
            )
        if wanted_type is OptionType.CALL:
            long_index = min(
                range(len(selected)), key=lambda i: abs(selected[i].strike - underlying_price)
            )
            if long_index == len(selected) - 1:
                long_index -= 1
            long_contract, short_contract = selected[long_index], selected[long_index + 1]
            structure_type = StructureType.BULL_CALL_DEBIT_SPREAD
        else:
            long_index = min(
                range(len(selected)), key=lambda i: abs(selected[i].strike - underlying_price)
            )
            if long_index == 0:
                long_index = 1
            long_contract, short_contract = selected[long_index], selected[long_index - 1]
            structure_type = StructureType.BEAR_PUT_DEBIT_SPREAD
        structure = build_structure(
            structure_type,
            (
                OptionLeg(
                    side=LegSide.LONG, contract=long_contract, entry_price=long_contract.quote.ask
                ),
                OptionLeg(
                    side=LegSide.SHORT,
                    contract=short_contract,
                    entry_price=short_contract.quote.bid,
                ),
            ),
        )
        candidate = strategy.rank_candidates(idea, (structure,))[0]
        projections = PostgresBrokerProjectionStore(self._sessions, self._workspace_id)
        account = await projections.get_account()
        gate = await BrokerExecutionGate(projections).evaluate(now)
        if account is None:
            return await self._unavailable(
                opportunity_id,
                signal,
                idea,
                now,
                "broker_account_unavailable",
                scan_run_id=scan_run_id,
            )
        positions = await projections.list_positions()
        risk = RiskEngine(RiskPolicy()).evaluate(
            candidate,
            RiskContext(
                paper_equity=account.equity,
                open_planned_loss=0,
                underlying_open_risk=0,
                daily_loss=max(account.last_equity - account.equity, Decimal("0")),
                drawdown_percent=(
                    max(account.last_equity - account.equity, Decimal("0"))
                    / max(account.last_equity, Decimal("1"))
                    * Decimal("100")
                ),
                concurrent_option_structures=len(positions),
                broker_execution_allowed=gate.allowed,
            ),
        )
        intent = create_order_intent(risk, candidate) if risk.decision == "APPROVE" else None
        result = ConnectedAnalysis(
            opportunity_id=opportunity_id,
            scan_run_id=scan_run_id,
            symbol=normalized,
            disposition="TRADE" if intent else "RISK_REJECTED",
            observed_at=now,
            expires_at=expires_at,
            signal=signal.model_dump(mode="json"),
            trade_idea=idea.model_dump(mode="json"),
            candidate=candidate.model_dump(mode="json"),
            risk_decision=risk.model_dump(mode="json"),
            order_intent=None if intent is None else intent.model_dump(mode="json"),
        )
        await self._persist(result)
        return result

    async def _unavailable(
        self,
        opportunity_id: UUID,
        signal: Signal,
        idea: Any,
        now: datetime,
        reason: str,
        *,
        scan_run_id: UUID | None = None,
    ) -> ConnectedAnalysis:
        result = ConnectedAnalysis(
            opportunity_id=opportunity_id,
            scan_run_id=scan_run_id,
            symbol=signal.symbol,
            disposition="UNAVAILABLE",
            observed_at=now,
            expires_at=now + timedelta(minutes=2),
            signal=signal.model_dump(mode="json"),
            trade_idea=idea.model_dump(mode="json"),
            reason_codes=(reason,),
        )
        await self._persist(result)
        return result

    async def _persist(self, result: ConnectedAnalysis) -> None:
        async with self._sessions.begin() as session:
            session.add(
                ConnectedOpportunityRecord(
                    opportunity_id=result.opportunity_id,
                    workspace_id=self._workspace_id,
                    scan_run_id=result.scan_run_id,
                    symbol=result.symbol,
                    state=result.disposition,
                    source="ALPACA_REAL",
                    payload=result.model_dump(mode="json"),
                    observed_at=result.observed_at,
                    expires_at=result.expires_at,
                    created_at=datetime.now(UTC),
                )
            )


async def start_scan_run(
    sessions: async_sessionmaker[AsyncSession],
    workspace_id: UUID,
    *,
    trigger: str,
    attempted_count: int,
) -> ConnectedScanRunRecord:
    record = ConnectedScanRunRecord(
        scan_run_id=uuid4(),
        workspace_id=workspace_id,
        trigger=trigger,
        source="ALPACA_REAL",
        started_at=datetime.now(UTC),
        completed_at=None,
        attempted_count=attempted_count,
        completed_count=0,
        failed_count=0,
    )
    async with sessions.begin() as session:
        session.add(record)
    return record


async def complete_scan_run(
    sessions: async_sessionmaker[AsyncSession],
    scan_run_id: UUID,
    *,
    completed_count: int,
    failed_count: int,
) -> ConnectedScanRunRecord:
    async with sessions.begin() as session:
        record = await session.get(ConnectedScanRunRecord, scan_run_id, with_for_update=True)
        if record is None:
            raise RuntimeError("Connected scan run disappeared before completion")
        record.completed_at = datetime.now(UTC)
        record.completed_count = completed_count
        record.failed_count = failed_count
    return record
