from __future__ import annotations

from datetime import UTC, date, datetime
from types import SimpleNamespace

import pytest

from packages.domain.options import OptionContract, OptionType
from packages.options.alpaca_adapter import AlpacaOptionChainAdapter, OptionChainQuery


class FakeTradingClient:
    def get_option_contracts(self, request: object) -> SimpleNamespace:
        assert request is not None
        return SimpleNamespace(
            option_contracts=[
                SimpleNamespace(
                    id="contract-1",
                    symbol="XYZ260925C00100000",
                    underlying_symbol="XYZ",
                    expiration_date=date(2026, 9, 25),
                    strike_price=100.0,
                    type=SimpleNamespace(value="call"),
                    size="100",
                    tradable=True,
                    open_interest="900",
                )
            ],
            next_page_token=None,
        )


class FakeDataClient:
    def get_option_chain(self, request: object) -> dict[str, SimpleNamespace]:
        assert request is not None
        return {
            "XYZ260925C00100000": SimpleNamespace(
                latest_quote=SimpleNamespace(
                    bid_price=4.9,
                    ask_price=5.1,
                    bid_size=12,
                    ask_size=10,
                    timestamp=datetime(2026, 9, 1, 14, tzinfo=UTC),
                ),
                implied_volatility=0.24,
                greeks=SimpleNamespace(delta=0.52, gamma=0.04, theta=-0.03, vega=0.15),
            )
        }


@pytest.mark.asyncio
async def test_alpaca_option_types_are_normalized_at_boundary() -> None:
    adapter = AlpacaOptionChainAdapter(
        "paper-key",
        "paper-secret",
        trading_client=FakeTradingClient(),
        data_client=FakeDataClient(),
    )
    result = await adapter.get_chain(
        OptionChainQuery(
            underlying_symbol="XYZ",
            expiration_date_gte=date(2026, 9, 15),
            expiration_date_lte=date(2026, 10, 15),
        )
    )

    assert len(result) == 1
    assert isinstance(result[0], OptionContract)
    assert result[0].option_type is OptionType.CALL
    assert result[0].strike.as_tuple().exponent == -1
    assert result[0].quote.open_interest == 900
    assert result[0].quote.greeks is not None
    assert result[0].quote.greeks.delta.as_tuple().exponent == -2
