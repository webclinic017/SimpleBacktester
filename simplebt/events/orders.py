from dataclasses import dataclass
from simplebt.events.generic import Event
from simplebt.trade import StrategyTrade


@dataclass(frozen=True)
class OrderReceivedEvent(Event):
    trade: StrategyTrade


@dataclass(frozen=True)
class OrderCanceledEvent(Event):
    trade: StrategyTrade
