from dataclasses import dataclass
import datetime


@dataclass(frozen=True)
class Event:
    time: datetime.datetime


@dataclass(frozen=True)
class Nothing(Event):
    time: datetime.datetime
