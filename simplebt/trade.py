import datetime
from dataclasses import dataclass
from simplebt.orders import Order


@dataclass
class StrategyTrade:
    time: datetime.datetime
    price: float
    lots: int  # positive or negative
    order: Order  # IBKR returns the order associated with the trade
