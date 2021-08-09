import abc
import datetime
from typing import List

import simplebt.backtester as bt
from simplebt.ticker import Ticker
from simplebt.trade import StrategyTrade, Fill
from simplebt.position import PnLSingle


class StrategyInterface(abc.ABC):
    """
    This class defines the architecture of the Strategy.
    This class will have a concrete form for every different Strategy we want to write.
    """
    backtester: bt.Backtester = None

    @abc.abstractmethod
    def set_time(self, time: datetime.datetime):
        raise NotImplementedError

    @abc.abstractmethod
    def on_pending_tickers_event(self, tickers: List[Ticker]):
        raise NotImplementedError

    @abc.abstractmethod
    def on_new_order_event(self, trade: StrategyTrade):
        raise NotImplementedError

    @abc.abstractmethod
    def on_exec_details_event(self, trade: StrategyTrade, fill: Fill):
        raise NotImplementedError

    @abc.abstractmethod
    def on_pnl_single_event(self, pnl: PnLSingle):
        raise NotImplementedError
