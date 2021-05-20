from abc import ABC, abstractmethod
from dataclasses import dataclass
import datetime
from typing import List, Set
from simplebt.events.market import StrategyTrade
from simplebt.events.batches import PendingTicker
from simplebt.orders import Order

@dataclass(frozen=True)
class Action(ABC):
    time: datetime.datetime

@dataclass(frozen=True)
class PlaceOrder(Action):
    order: Order

@dataclass(frozen=True)
class CancelOrder(Action):
    order: Order


class StrategyInterface(ABC):
    """
    This class defines the architecture of the Strategy.
    This class will have a concrete form for every different Strategy we want to write.
    """
    @abstractmethod
    def set_time(self, time: datetime.datetime) -> List[Action]:
        raise NotImplementedError

    @abstractmethod
    def on_pending_tickers(self, event: Set[PendingTicker]):
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
    def on_new_order_event(self, order: Order):
        raise NotImplementedError

    @abstractmethod
    def on_fill(self, event: StrategyTrade):
        """
        Series of actions to be done when there is a proprietary trade.
        """
        raise NotImplementedError

    @abstractmethod
    def on_pnl(self, event: PnL):
        raise NotImplementedError

    @abstractmethod
    def get_trades(self) -> List[StrategyTrade]:
        """Return trades"""
        raise NotImplementedError
