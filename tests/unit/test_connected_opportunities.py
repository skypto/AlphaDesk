from types import SimpleNamespace
from typing import Any

from alpaca.data.enums import DataFeed

from packages.connected.opportunities import ConnectedOpportunityService


class StockClientStub:
    def __init__(self) -> None:
        self.snapshot_request: Any = None
        self.bars_request: Any = None

    def get_stock_snapshot(self, request: Any) -> dict[str, Any]:
        self.snapshot_request = request
        stock = SimpleNamespace(
            latest_trade=SimpleNamespace(price=101),
            daily_bar=SimpleNamespace(open=100, volume=1000),
            previous_daily_bar=SimpleNamespace(close=99),
        )
        index = SimpleNamespace(
            latest_trade=SimpleNamespace(price=101),
            daily_bar=SimpleNamespace(open=100),
        )
        return {"AAPL": stock, "SPY": index, "QQQ": index}

    def get_stock_bars(self, request: Any) -> Any:
        self.bars_request = request
        return SimpleNamespace(data={"AAPL": [SimpleNamespace(volume=1000)]})


class NewsClientStub:
    def get_news(self, request: Any) -> list[Any]:
        return []


def test_connected_stock_requests_explicitly_use_iex_feed() -> None:
    stock = StockClientStub()
    service = ConnectedOpportunityService.__new__(ConnectedOpportunityService)
    service._stock = stock
    service._news = NewsClientStub()

    service._features("AAPL")

    assert stock.snapshot_request.feed is DataFeed.IEX
    assert stock.bars_request.feed is DataFeed.IEX
