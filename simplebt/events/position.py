import datetime
from dataclasses import dataclass

from simplebt.events.generic import Event
from simplebt.position import PnLSingle


@dataclass(frozen=True)
class PnLSingleEvent(Event):
    time: datetime.datetime
    pnl: PnLSingle
