import datetime
from ib_insync import Contract
from dataclasses import dataclass
from simplebt.events.generic import Event

@dataclass(frozen=True)
class Order(Event):  # GTC
    contract: Contract
    time: datetime.datetime

@dataclass(frozen=True)
class MktOrder(Order):
    lots: int  # TODO: instert > 0 check

@dataclass(frozen=True)
class LmtOrder(Order):
    lots: int  # TODO: instert > 0 check
    price: float

# @dataclass
# class PendingOrder(Order):
#     """
#     This should be created by the bt not by the strat
#     """
#     order_id: int
#     order: Order
