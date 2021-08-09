import datetime
from dataclasses import dataclass
from typing import List

from simplebt.events.generic import Event
from simplebt.position import PnLSingle
from simplebt.ticker import Ticker
from simplebt.trade import StrategyTrade, Fill


@dataclass(frozen=True)
class PendingTickersEvent(Event):
    time: datetime.datetime
    tickers: List[Ticker]


@dataclass(frozen=True)
class FillEvent(Event):
    time: datetime.datetime
    fill: Fill
    trade: StrategyTrade


@dataclass(frozen=True)
class PnLSingleEvent(Event):
    time: datetime.datetime
    pnl: PnLSingle


# Market Calendar Events
@dataclass(frozen=True)
class MktOpenEvent(Event):
    time: datetime.datetime


@dataclass(frozen=True)
class MktCloseEvent(Event):
    time: datetime.datetime
