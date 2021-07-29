from abc import ABC, abstractmethod
import datetime
from typing import Union

from simplebt.events.orders import OrderReceivedEvent, OrderCanceledEvent
from simplebt.trade import StrategyTrade, Fill
from simplebt.events.batches import PendingTickerSetEvent
from simplebt.position import PnLSingle


class StrategyInterface(ABC):
    """
    This class defines the architecture of the Strategy.
    This class will have a concrete form for every different Strategy we want to write.
    """
    _time: datetime.datetime

    @property
    def time(self) -> datetime.datetime:
        return self._time

    @time.setter
    def time(self, time: datetime.datetime):
        raise NotImplementedError

    @abstractmethod
    def on_pending_tickers(self, pending_tickers_event: PendingTickerSetEvent):
        """
        Series of actions to be done when the first level of a book changes
        or there is a new trade in the market
        """
        raise NotImplementedError

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
