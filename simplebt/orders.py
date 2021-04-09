import abc
import datetime
import ib_insync as ibi


class Order(abc.ABC):
    def __init__(
        self,
        contract: ibi.Contract,
        lots: int,
        side: int,
        time: datetime.datetime,
    ):
        self.contract = contract
        if lots <= 0:
            raise ValueError(f"Lots must be positive. Got {lots}")
        self.lots = lots
        if abs(side) != 1:
            raise ValueError(f"Side should be either -1 or 1. Got {side}")
        self.side = side
        self.time = time
        self.id = None
        self.received: bool = False
        self.active: bool = True
        self.id = f"{time.timestamp()}{self.contract.symbol}{self.lots}{self.side}"  # pseudo-random id

    def validate(self):
        """To be called by the mkt when the order is validated"""
        self.received = True
        self.active = True

    def cancel(self):
        self.active = False


class MktOrder(Order):
    def __init__(
            self,
            contract: ibi.Contract,
            lots: int,
            side: int,
            time: datetime.datetime,
    ):
        super().__init__(contract, lots, side, time)


class LmtOrder(Order):
    def __init__(
            self,
            contract: ibi.Contract,
            lots: int,
            side: int,
            price: float,
            time: datetime.datetime,
    ):
        super().__init__(contract, lots, side, time)
        self.price = price
