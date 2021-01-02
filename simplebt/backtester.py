# TODO: orders should be processed by the market not by the backtester
import itertools
import logging
import datetime
import pathlib
import random
import queue
from typing import Optional, Tuple, Dict, Iterable
import ib_insync as ibi

from simplebt.events.generic import Event
from simplebt.events.market import StrategyTrade
from simplebt.market import Market
from simplebt.events.orders import Order
from simplebt.strategy import StrategyInterface


class Backtester:
    def __init__(
        self,
        strat: StrategyInterface,
        contracts: Tuple[ibi.Contract],
        start_time: datetime.datetime,
        end_time: datetime.datetime,
        time_step: datetime.timedelta,
        data_dir: pathlib.Path,
        shuffle_events: bool = None,
        logger: logging.Logger = None,
    ):
        """
        :param contracts: the order matters unless shuffle_events is set to True
        :param shuffle_events: whether to shuffle the events coming from different mkts
        """
        self.time = start_time
        self.end_time = end_time
        self.time_step = time_step
        
        self.strat = strat
        self.mkts: Dict[ibi.Contract, Market] = {
            contract: Market(start_time=start_time, contract=contract, data_dir=data_dir)
            for contract in contracts
        }

        self._strat_pending_orders: "queue.Queue[Order]" = queue.Queue()
        self._events: "queue.Queue[Event]" = queue.Queue()
        self.shuffle_events: bool = shuffle_events or False

        self.logger = logger or logging.getLogger(__name__)

    def _set_mkts_time(self, time: datetime.datetime):
        for mkt in self.mkts.values():
            mkt.set_time(time=time)

    def _get_events_from_mkts(self) -> queue.Queue[Event]:
        q: queue.Queue[Event] = queue.Queue()
        all_events: Iterable[Event] = itertools.chain.from_iterable(
            (mkt.get_events() for mkt in self.mkts.values())
        )
        if self.shuffle_events:
            all_events = sorted(all_events, key=lambda k: random.random())
        for e in all_events:
            q.put(e)
        return q

    def _feed_events_to_strat(self, events: "queue.Queue[Event]"):
        while not events.empty():
            event = events.get_nowait()
            strat_action: Optional[Order] = self.strat.process_event(event)
            if isinstance(strat_action, Order):
                self._strat_pending_orders.put(strat_action)
            # elif isinstance(answer, CancelOrder):
            #     self._cancel_order(answer)

    def run(self):
        while self.time <= self.end_time:
            self.logger.info(self.time)
            self._set_mkts_time(time=self.time)
            
            mkt_events: queue.Queue[Event] = self._get_events_from_mkts()
            self._feed_events_to_strat(events=mkt_events)

            self.time += self.time_step
