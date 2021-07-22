import datetime
from dataclasses import dataclass


@dataclass(frozen=True)
class BookL0:
    bid: float
    ask: float
    bid_size: int
    ask_size: int
    time: datetime.datetime

