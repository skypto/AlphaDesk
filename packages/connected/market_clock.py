from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from alpaca.trading.client import TradingClient
from pydantic import BaseModel, ConfigDict


class ConnectedMarketClock(BaseModel):
    model_config = ConfigDict(frozen=True)

    is_open: bool
    timestamp: datetime
    next_open: datetime
    next_close: datetime
    timezone: str = "America/New_York"
    regular_session: str = "9:30 AM-4:00 PM ET"
    source: str = "ALPACA_REAL"


def _aware(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


class AlpacaMarketClockAdapter:
    """Read-only tenant-bound Alpaca market clock boundary."""

    def __init__(self, api_key: str, secret_key: str, *, client: Any | None = None) -> None:
        if not api_key or not secret_key:
            raise ValueError("Alpaca credentials are required for the market clock")
        self._client = client or TradingClient(api_key, secret_key, paper=True)

    async def get_clock(self) -> ConnectedMarketClock:
        raw = await asyncio.to_thread(self._client.get_clock)
        return ConnectedMarketClock(
            is_open=bool(raw.is_open),
            timestamp=_aware(raw.timestamp),
            next_open=_aware(raw.next_open),
            next_close=_aware(raw.next_close),
        )
