import itertools
import logging
import datetime
import pathlib
import random
import queue
import pandas as pd
from typing import Dict, Iterable, List, Optional
import ib_insync as ibi

from simplebt.events.generic import Event
from simplebt.market import Market
from simplebt.events.market import StrategyTrade
from simplebt.orders import Order
from simplebt.strategy import StrategyInterface, PlaceOrder, CancelOrder

# NOTE: The queue lib still doesn't go well with type annotations
#  Using queue.Queue[Event] raises the Exception: type object is not subscriptable
#  Declaring `EventQueue = typing.NewType("EventQueue", queue.Queue[Event])` doesn't work either
#  The only workaround is to enclose it in a str like "queue.Queue[Event]" but I don't like that

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Backtester:
    def __init__(
        self,
        strat: StrategyInterface,
        contracts: List[ibi.Contract],
        start_time: datetime.datetime,
        end_time: datetime.datetime,
        time_step: datetime.timedelta,
        data_dir: pathlib.Path,
        chunksize: int = None,
        shuffle_events: bool = None,
    ):
        """
        :param contracts: the order matters unless shuffle_events is set to True
        :param shuffle_events: whether to shuffle the events coming from different mkts
        """
        if start_time.tzinfo != datetime.timezone.utc:
            raise ValueError(f"Parameter start_time should have tzinfo=datetime.timezone.utc, got {start_time.tzinfo}")
        self.time = start_time
        if end_time.tzinfo != datetime.timezone.utc:
            raise ValueError(f"Parameter end_time should have tzinfo=datetime.timezone.utc, got {end_time.tzinfo}")
        self.end_time = end_time
        self.time_step = time_step
       
        if not chunksize:
            logger.info("Setting chunksize to 1 million rows")
            chunksize = int(1e6)
        self.strat = strat
        self.mkts: Dict[int, Market] = {
            c.conId: Market(contract=c, start_time=start_time, data_dir=data_dir, chunksize=chunksize)
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

    def _forward_strat_action(self, action):
        event: Optional[Event] = None
        if isinstance(action, PlaceOrder):
            event = self.mkts[action.order.contract.conId].add_order(action.order)
        elif isinstance(action, CancelOrder):
            event = self.mkts[action.order.contract.conId].cancel_order(action.order)
        if event:
            self._events.put(event)

    def _run_strat(self, events: queue.Queue):
        action: Optional[Order] = self.strat.set_time(time=self.time)
        if action:
            self._forward_strat_action(action=action)

        while not events.empty():
            event = events.get_nowait()
            action = self.strat.process_event(event)
            if action:
                self._forward_strat_action(action=action)

    def run(self, save_path: pathlib.Path = None):
        while self.time <= self.end_time:
            logger.info(f"Next timestamp: {self.time}")

            self._set_mkts_time(time=self.time)
            mkt_events: queue.Queue = self._get_events_from_mkts()

            self._run_strat(events=mkt_events)

            self.time += self.time_step

        logger.info("Hey jerk! We're done backtesting. You happy with the results?")
        if save_path:
            trades: List[StrategyTrade] = self.strat.get_trades()
            df = pd.DataFrame(
                [(t.time, t.price, t.lots, t.order.time) for t in trades],
                columns=["time", "price", "lots", "order_time"]
            )
            df.to_csv(save_path)
