import abc
import datetime
import ib_insync as ibi
from enum import Enum
from typing import ClassVar, Set
from dataclasses import dataclass


class OrderAction(Enum):
    BUY = 1
    SELL = -1


@dataclass
class OrderStatus:
    status = ""

    PendingSubmit: ClassVar[str] = "PendingSubmit"
    PendingCancel: ClassVar[str] = "PendingCancel"
    PreSubmitted: ClassVar[str] = "PreSubmitted"
    Submitted: ClassVar[str] = "Submitted"
    ApiPending: ClassVar[str] = "ApiPending"
    ApiCancelled: ClassVar[str] = "ApiCancelled"
    Cancelled: ClassVar[str] = "Cancelled"
    Filled: ClassVar[str] = "Filled"
    Inactive: ClassVar[str] = "Inactive"

    DoneStates: ClassVar[Set[str]] = {"Filled", "Cancelled", "ApiCancelled"}
    ActiveStates: ClassVar[Set[str]] = {"PendingSubmit", "ApiPending", "PreSubmitted", "Submitted"}


class Order(abc.ABC):
    def __init__(
        self,
        contract: ibi.Contract,
        action: OrderAction,
        lots: int,
        time: datetime.datetime,
    ):
        if lots <= 0:
            raise ValueError(f"Lots must be positive. Got {lots}")
        if action not in (OrderAction.BUY, OrderAction.SELL):
            raise ValueError("Action must be either BUY or SELL")
        self._contract = contract
        self._lots = lots
        self._action = action
        self._time = time
        self._order_status: OrderStatus = OrderStatus()
        # self.id = None
        # self.id = f"{time.timestamp()}{self.contract.symbol}{self.lots}{self.side}"  # pseudo-random id

    @property
    def contract(self) -> ibi.Contract:
        return self._contract

    @property
    def lots(self) -> int:
        return self._lots

    @property
    def action(self) -> OrderAction:
        return self._action

    @property
    def time(self) -> datetime.datetime:
        return self._time

    @property
    def order_status(self) -> OrderStatus:
        return self._order_status

    def submitted(self):
        self._order_status.status = OrderStatus.Submitted

    def filled(self):
        self._order_status.status = OrderStatus.Filled

    def cancelled(self):
        self._order_status.status = OrderStatus.ApiCancelled


class MktOrder(Order):
    def __init__(
            self,
            contract: ibi.Contract,
            action: OrderAction,
            lots: int,
            time: datetime.datetime,
    ):
        super().__init__(contract=contract, action=action, lots=lots, time=time)


class LmtOrder(Order):
    def __init__(
            self,
            contract: ibi.Contract,
            action: OrderAction,
            lots: int,
            price: float,
            time: datetime.datetime,
    ):
        super().__init__(contract=contract, lots=lots, action=action, time=time)
        self._price = price

    @property
    def price(self) -> float:
        return self._price
