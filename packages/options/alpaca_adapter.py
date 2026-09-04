from __future__ import annotations

import asyncio
from datetime import date
from decimal import Decimal
from typing import Any, cast

from alpaca.data.historical.option import OptionHistoricalDataClient
from alpaca.data.requests import OptionChainRequest
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import AssetStatus
from alpaca.trading.requests import GetOptionContractsRequest
from pydantic import BaseModel, ConfigDict, Field

from packages.domain.options import Greeks, OptionContract, OptionQuote, OptionType


class OptionChainQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    underlying_symbol: str = Field(min_length=1)
    expiration_date_gte: date
    expiration_date_lte: date
    strike_price_gte: Decimal | None = None
    strike_price_lte: Decimal | None = None


class AlpacaOptionChainAdapter:
    """Normalizes Alpaca option reference and market data into domain objects."""

    def __init__(
        self,
        api_key: str,
        secret_key: str,
        *,
        trading_client: Any | None = None,
        data_client: Any | None = None,
    ) -> None:
        if not api_key or not secret_key:
            raise ValueError("Alpaca credentials are required for option market data.")
        self._trading = trading_client or TradingClient(api_key, secret_key, paper=True)
        self._data = data_client or OptionHistoricalDataClient(api_key, secret_key)

    @staticmethod
    def _option_type(value: object) -> OptionType:
        normalized = str(getattr(value, "value", value)).lower()
        if normalized not in {OptionType.CALL, OptionType.PUT}:
            raise ValueError(f"Unsupported option type: {normalized}")
        return OptionType(normalized)

    @staticmethod
    def _map_contract(raw: Any, snapshot: Any) -> OptionContract:
        quote = snapshot.latest_quote
        if quote is None:
            raise ValueError(f"Latest quote unavailable for {raw.symbol}")
        raw_greeks = snapshot.greeks
        greeks = None
        if raw_greeks is not None:
            greeks = Greeks(
                delta=Decimal(str(raw_greeks.delta)),
                gamma=Decimal(str(raw_greeks.gamma)),
                theta=Decimal(str(raw_greeks.theta)),
                vega=Decimal(str(raw_greeks.vega)),
            )
        open_interest = None if raw.open_interest is None else int(raw.open_interest)
        return OptionContract(
            contract_id=str(raw.id),
            symbol=str(raw.symbol),
            underlying_symbol=str(raw.underlying_symbol),
            expiration=raw.expiration_date,
            strike=Decimal(str(raw.strike_price)),
            option_type=AlpacaOptionChainAdapter._option_type(raw.type),
            multiplier=int(raw.size),
            tradable=bool(raw.tradable),
            quote=OptionQuote(
                bid=Decimal(str(quote.bid_price)),
                ask=Decimal(str(quote.ask_price)),
                bid_size=Decimal(str(quote.bid_size)),
                ask_size=Decimal(str(quote.ask_size)),
                quoted_at=quote.timestamp,
                open_interest=open_interest,
                implied_volatility=(
                    None
                    if snapshot.implied_volatility is None
                    else Decimal(str(snapshot.implied_volatility))
                ),
                greeks=greeks,
            ),
        )

    def _get_contracts(self, query: OptionChainQuery) -> list[Any]:
        contracts: list[Any] = []
        page_token: str | None = None
        while True:
            request = GetOptionContractsRequest(
                underlying_symbols=[query.underlying_symbol],
                status=AssetStatus.ACTIVE,
                expiration_date_gte=query.expiration_date_gte,
                expiration_date_lte=query.expiration_date_lte,
                strike_price_gte=(
                    None if query.strike_price_gte is None else str(query.strike_price_gte)
                ),
                strike_price_lte=(
                    None if query.strike_price_lte is None else str(query.strike_price_lte)
                ),
                limit=10000,
                page_token=page_token,
            )
            response = cast(Any, self._trading.get_option_contracts(request))
            contracts.extend(response.option_contracts)
            page_token = response.next_page_token
            if not page_token:
                return contracts

    def _get_snapshots(self, query: OptionChainQuery) -> dict[str, Any]:
        request = OptionChainRequest(
            underlying_symbol=query.underlying_symbol,
            expiration_date_gte=query.expiration_date_gte,
            expiration_date_lte=query.expiration_date_lte,
            strike_price_gte=(
                None if query.strike_price_gte is None else float(query.strike_price_gte)
            ),
            strike_price_lte=(
                None if query.strike_price_lte is None else float(query.strike_price_lte)
            ),
        )
        return self._data.get_option_chain(request)

    async def get_chain(self, query: OptionChainQuery) -> tuple[OptionContract, ...]:
        contracts, snapshots = await asyncio.gather(
            asyncio.to_thread(self._get_contracts, query),
            asyncio.to_thread(self._get_snapshots, query),
        )
        normalized: list[OptionContract] = []
        for contract in contracts:
            snapshot = snapshots.get(str(contract.symbol))
            if snapshot is None or snapshot.latest_quote is None:
                continue
            normalized.append(self._map_contract(contract, snapshot))
        return tuple(
            sorted(normalized, key=lambda item: (item.expiration, item.strike, item.option_type))
        )
