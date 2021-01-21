import itertools
import logging
import datetime
import pathlib
import random
import queue
from typing import Dict, Iterable, List, Optional
import ib_insync as ibi

from simplebt.events.generic import Event
from simplebt.market import Market
from simplebt.events.orders import Order
from simplebt.strategy import StrategyInterface

# NOTE: The queue lib still doesn't go well with type annotations
#  Using queue.Queue[Event] raises the Exception: type object is not subscriptable
#  Declaring `EventQueue = typing.NewType("EventQueue", queue.Queue[Event])` doesn't work either
#  The only workaround is to enclose it in a str like "queue.Queue[Event]" but I don't like that

logger = logging.getLogger(__name__)

class Backtester:
    def __init__(
        self,
        strat: StrategyInterface,
        contracts: List[ibi.Contract],
        start_time: datetime.datetime,
        end_time: datetime.datetime,
        time_step: datetime.timedelta,
        latency: bool,
        data_dir: pathlib.Path,
        chunksize: int = None,
        shuffle_events: bool = None,
    ):
        """
        :param contracts: the order matters unless shuffle_events is set to True
        :param shuffle_events: whether to shuffle the events coming from different mkts
        """
        self.time = start_time
        self.end_time = end_time
        self.time_step = time_step
        
        self.strat = strat
        self.mkts: Dict[int, Market] = {
            c.conId: Market(contract=c, start_time=start_time, latency=latency, data_dir=data_dir, chunksize=chunksize)
            for c in contracts
        }

        self._events = queue.Queue()
        self.shuffle_events: bool = shuffle_events or False

    def _set_mkts_time(self, time: datetime.datetime):
        for mkt in self.mkts.values():
            mkt.set_time(time=time)

    def _get_events_from_mkts(self) -> queue.Queue:
        q: queue.Queue = queue.Queue()
        all_events: Iterable[Event] = itertools.chain.from_iterable(
            (mkt.get_events() for mkt in self.mkts.values())
        )
        if self.shuffle_events:
            all_events = sorted(all_events, key=lambda k: random.random())
        for e in all_events:
            q.put(e)
        return q

    def _feed_events_to_strat(self, events: queue.Queue):
        while not events.empty():
            event = events.get_nowait()
            action: Optional[Order] = self.strat.process_event(event)
            if isinstance(action, Order):
                self.mkts[action.contract.conId].add_order(action)

    def run(self):
        while self.time <= self.end_time:
            logger.info(f"Process time {self.time}")
            self._set_mkts_time(time=self.time)
            
            mkt_events: queue.Queue = self._get_events_from_mkts()
            self._feed_events_to_strat(events=mkt_events)

            self.time += self.time_step
