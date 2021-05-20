import ib_insync as ibi
from dataclasses import dataclass
from typing import List, Union

from simplebt.events.market import ChangeBest, MktTrade
from simplebt.events.generic import Event


# ChangeBestBatch = NewType("ChangeBestBatch", List[ChangeBest])
@dataclass(frozen=True)
class ChangeBestBatch(Event):
    events: List[ChangeBest]


# MktTradeBatch = NewType("MktTradeBatch", List[MktTrade])
@dataclass(frozen=True)
class MktTradeBatch(Event):
    events: List[MktTrade]


@dataclass(frozen=True)
class PendingTicker(Event):
    contract: ibi.Contract
    events: List[Union[MktTrade, ChangeBest]]
