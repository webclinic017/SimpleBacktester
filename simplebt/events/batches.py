import ib_insync as ibi
from dataclasses import dataclass
from typing import List, Union, Set

from simplebt.events.market import ChangeBestEvent, MktTradeEvent
from simplebt.events.generic import Event


# ChangeBestBatch = NewType("ChangeBestBatch", List[ChangeBest])
@dataclass(frozen=True)
class ChangeBestBatchEvent(Event):
    events: List[ChangeBestEvent]


# MktTradeBatch = NewType("MktTradeBatch", List[MktTrade])
@dataclass(frozen=True)
class MktTradeBatchEvent(Event):
    events: List[MktTradeEvent]


@dataclass(frozen=True)
class PendingTickerEvent(Event):
    contract: ibi.Contract
    events: List[Union[MktTradeEvent, ChangeBestEvent]]


@dataclass(frozen=True)
class PendingTickerSetEvent(Event):
    events: Set[PendingTickerEvent]
