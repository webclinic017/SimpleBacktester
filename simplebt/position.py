import ib_insync as ibi
import numpy as np
from dataclasses import dataclass
from typing import List
from simplebt.trade import StrategyTrade


class Position:
    def __init__(self, contract: ibi.Contract):
        self._contract = contract
        self._position: int = 0
        self._avg_cost: float = 0
        self._entries: List[StrategyTrade] = []

    @property
    def contract(self) -> ibi.Contract:
        return self._contract

    @property
    def position(self) -> int:
        return self._position

    @property
    def avg_cost(self) -> float:
        return self._avg_cost

    # @position.setter
    # def position(self, position: int):
    #     self._position = position

    # @avg_cost.setter
    # def avg_cost(self, avg_cost: float):
    #     self._avg_cost = avg_cost

    def update(self, fill: StrategyTrade):
        self._entries.append(fill)
        new_position = sum(map(lambda x: x.lots, self._entries))
        avg_cost = sum(map(lambda x: abs(x.lots) * x.price, self._entries)) / sum(map(lambda x: abs(x.lots), self._entries))
        self._avg_cost = avg_cost
        self._position = new_position


@dataclass
class PnLSingle:
    conId: int = 0
    dailyPnL: float = np.nan
    unrealizedPnL: float = np.nan
    realizedPnL: float = np.nan
    position: int = 0
    value: float = np.nan
