import datetime
from dataclasses import dataclass
from simplebt.book import BookL0
from simplebt.events.orders import Order
from simplebt.events.generic import Event


# Created by the strategy
@dataclass(frozen=True)
class StrategyTrade(Event):
    time: datetime.datetime
    price: float
    lots: int  # positive or negative
    order: Order  # IBKR returns the order associated with the trade


# Market Events
@dataclass(frozen=True)
class ChangeBest(Event):
    time: datetime.datetime
    best: BookL0


# TODO: make market trade object and then add event
@dataclass(frozen=True)
class MktTrade(Event):
    time: datetime.datetime
    price: float
    size: int


# Market Calendar Events
@dataclass(frozen=True)
class MktOpen(Event):
    time: datetime.datetime


@dataclass(frozen=True)
class MktClose(Event):
    time: datetime.datetime
