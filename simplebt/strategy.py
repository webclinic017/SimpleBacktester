from abc import ABC, abstractmethod
from dataclasses import dataclass
import datetime
from typing import List, Set, Union

from simplebt.events.orders import OrderReceivedEvent, OrderCanceledEvent
from simplebt.trade import StrategyTrade, Fill
from simplebt.events.batches import PendingTickerEvent
from simplebt.orders import Order
from simplebt.position import PnLSingle


class StrategyInterface(ABC):
    """
    This class defines the architecture of the Strategy.
    This class will have a concrete form for every different Strategy we want to write.
    """
    @abstractmethod
    def set_time(self, time: datetime.datetime):
        raise NotImplementedError

    @abstractmethod
    def on_pending_tickers(self, tickers: Set[PendingTickerEvent]):
        """
        Series of actions to be done when the first level of a book changes
        or there is a new trade in the market
        """
        raise NotImplementedError

    # @abstractmethod
    # def on_change_best(self, event: ChangeBestBatch):
    #     raise NotImplementedError

    # @abstractmethod
    # def on_market_trade(self, event: MktTradeBatch):
    #     raise NotImplementedError

    @abstractmethod
    def on_new_order_event(self, order: Union[OrderReceivedEvent, OrderCanceledEvent]):
        raise NotImplementedError

    @abstractmethod
    def on_fill(self, trade: StrategyTrade, fill: Fill):
        """
        Series of actions to be done when there is a proprietary trade.
        """
        raise NotImplementedError

    @abstractmethod
    def on_pnl(self, pnl: PnLSingle):
        raise NotImplementedError

    @abstractmethod
    def get_trades(self) -> List[StrategyTrade]:
        """Return trades"""
        raise NotImplementedError
