import datetime
from dataclasses import dataclass
from simplebt.book import BookL0

from simplebt.events.generic import Event


# Created by the strategy
@dataclass(frozen=True)
class StrategyTrade(Event):
    price: float
    lots: int  # positive or negative
    time: datetime.datetime


# Market Events
@dataclass(frozen=True)
class ChangeBest(Event):
    best: BookL0
    time: datetime.datetime


@dataclass(frozen=True)
class MktTrade(Event):
    price: float
    size: int
    time: datetime.datetime


# Market Calendar Events
@dataclass(frozen=True)
class MktOpen(Event):
    time: datetime.datetime


@dataclass(frozen=True)
class MktClose(Event):
    time: datetime.datetime
