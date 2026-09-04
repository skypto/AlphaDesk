from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from packages.connected.market_clock import AlpacaMarketClockAdapter


@pytest.mark.asyncio
async def test_market_clock_is_normalized_without_alpaca_types() -> None:
    client = SimpleNamespace(
        get_clock=lambda: SimpleNamespace(
            is_open=True,
            timestamp=datetime(2026, 9, 3, 14, 0, tzinfo=UTC),
            next_open=datetime(2026, 9, 4, 13, 30, tzinfo=UTC),
            next_close=datetime(2026, 9, 3, 20, 0, tzinfo=UTC),
        )
    )
    adapter = AlpacaMarketClockAdapter("paper-key", "paper-secret", client=client)

    clock = await adapter.get_clock()

    assert clock.is_open
    assert clock.source == "ALPACA_REAL"
    assert clock.timezone == "America/New_York"
    assert clock.next_close == datetime(2026, 9, 3, 20, 0, tzinfo=UTC)
