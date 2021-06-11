import datetime
from typing import List
from dataclasses import dataclass
from simplebt.orders import Order


@dataclass(frozen=True)
class Fill:
    time: datetime.datetime
    price: float
    lots: int


class StrategyTrade:
    def __init__(self, order: Order):
        self._time = datetime.datetime.now()
        self._fills: List[Fill] = []
        self._order: Order = order  # IBKR returns the order associated with the trade
        self._filled_lots: int = 0

    @property
    def time(self) -> datetime.datetime:
        return self._time

    @property
    def fills(self) -> List[Fill]:
        return self._fills

    @property
    def order(self) -> Order:
        return self._order

    @order.setter
    def order(self, order):
        self._order = order

    def add_fill(self, fill: Fill):
        self._fills.append(fill)
        self._filled_lots += fill.lots
        if self._filled_lots > self._order.lots:
            raise ValueError

    def filled(self) -> bool:
        if self._filled_lots == self._order.lots:
            return True
        else:
            return False
