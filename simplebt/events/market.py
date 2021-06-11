import datetime
from dataclasses import dataclass
from simplebt.book import BookL0
from simplebt.events.generic import Event
from simplebt.trade import StrategyTrade, Fill


@dataclass(frozen=True)
class FillEvent(Event):
    time: datetime.datetime
    fill: Fill
    trade: StrategyTrade


@dataclass(frozen=True)
class ChangeBestEvent(Event):
    time: datetime.datetime
    best: BookL0


@dataclass(frozen=True)
class MktTradeEvent(Event):
    time: datetime.datetime
    price: float
    size: int


# Market Calendar Events
@dataclass(frozen=True)
class MktOpenEvent(Event):
    time: datetime.datetime


@dataclass(frozen=True)
class MktCloseEvent(Event):
    time: datetime.datetime
