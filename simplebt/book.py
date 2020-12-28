import datetime
from dataclasses import dataclass

@dataclass(frozen=True)
class BookL0:
    bid: float
    ask: float
    bid_size: float
    ask_size: float
    time: datetime.datetime

