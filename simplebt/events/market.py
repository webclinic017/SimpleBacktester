import datetime
from dataclasses import dataclass
from simplebt.book import BookL0
from simplebt.orders import Order
from simplebt.events.generic import Event


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
