import datetime
import ib_insync as ibi
from dataclasses import dataclass
from typing import Union, List


@dataclass(frozen=True)
class TickByTickAllLast:
    time: datetime.datetime
    price: float
    size: float


@dataclass(frozen=True)
class TickByTickBidAsk:
    time: datetime.datetime
    bid: float
    bid_size: int
    ask: float
    ask_size: int


@dataclass(frozen=True)
class Ticker:
    contract: ibi.Contract
    tickByTicks: List[Union[TickByTickAllLast, TickByTickBidAsk]]
