from dataclasses import dataclass
from simplebt.events.generic import Event
from simplebt import orders


@dataclass(frozen=True)
class OrderReceivedEvent(Event):
    order: orders.Order


@dataclass(frozen=True)
class OrderCanceledEvent(Event):
    order: orders.Order
