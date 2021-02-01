from dataclasses import dataclass
from simplebt.events.generic import Event
from simplebt import orders

@dataclass(frozen=True)
class OrderReceived(Event):
    order: orders.Order

@dataclass(frozen=True)
class OrderCanceled(Event):
    order: orders.Order
