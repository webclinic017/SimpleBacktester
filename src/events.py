import datetime
from dataclasses import dataclass
from src.book import BookL0
from typing import Iterable, List


@dataclass(frozen=True)
class Event:
    time: datetime.datetime


@dataclass(frozen=True)
class Nothing(Event):
    time: datetime.datetime


@dataclass(frozen=True)
class StrategyTrade(Event):
    price: float
    lots: int  # positive or negative
    time: datetime.datetime


@dataclass(frozen=True)
class ChangeBest(Event):
    best: BookL0
    time: datetime.datetime


@dataclass(frozen=True)
class MktTrade(Event):
    price: float
    size: int
    time: datetime.datetime


# ChangeBestBatch = NewType("ChangeBestBatch", List[ChangeBest])
@dataclass(frozen=True)
class ChangeBestBatch(Event):
    events: List[ChangeBest]


# MktTradeBatch = NewType("MktTradeBatch", List[MktTrade])
@dataclass(frozen=True)
class MktTradeBatch(Event):
    events: List[MktTrade]
