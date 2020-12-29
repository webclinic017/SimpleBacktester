from dataclasses import dataclass
from typing import List

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
