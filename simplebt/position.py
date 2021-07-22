import ib_insync as ibi
import numpy as np
from dataclasses import dataclass
from typing import List

from simplebt.orders import OrderAction
from simplebt.trade import Fill


class Position:
    def __init__(self, contract: ibi.Contract):
        self._contract = contract
        self._position: int = 0
        self._avg_cost: float = 0
        self._entries: List[Fill] = []

    @property
    def contract(self) -> ibi.Contract:
        return self._contract

    @property
    def position(self) -> int:
        return self._position

    @property
    def avg_cost(self) -> float:
        return self._avg_cost

    def update(self, fill: Fill):
        self._entries.append(fill)
        new_position = sum(map(lambda x: x.lots * self._order_action_to_side(x.order_action), self._entries))
        if new_position == 0:
            self._position = 0
            self._avg_cost = 0
            self._entries = []
        else:
            avg_cost = sum(map(lambda x: x.lots * x.price, self._entries)) / sum(map(lambda x: abs(x.lots), self._entries))
            self._avg_cost = avg_cost
            self._position = new_position

    @staticmethod
    def _order_action_to_side(order_action: OrderAction) -> int:
        if order_action == OrderAction.BUY:
            return 1
        elif order_action == OrderAction.SELL:
            return -1
        else:
            raise ValueError("Unknown OrderAction")

@dataclass
class PnLSingle:
    conId: int = 0
    dailyPnL: float = np.nan
    unrealizedPnL: float = np.nan
    realizedPnL: float = np.nan
    position: int = 0
    value: float = np.nan
