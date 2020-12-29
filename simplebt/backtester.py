# TODO: orders should be processed by the market not by the backtester
import logging
import datetime
import pathlib
from queue import Queue
from typing import Optional
import ib_insync as ibi

from simplebt.events.generic import Event
from simplebt.events.market import StrategyTrade
from simplebt.market import Market
from simplebt.orders import Order, MktOrder
from simplebt.strategy import StrategyInterface


class Backtester:
    def __init__(
        self,
        strat: StrategyInterface,
        contract: ibi.Contract,
        start_time: datetime.datetime,
        end_time: datetime.datetime,
        time_step: datetime.timedelta,
        data_dir: pathlib.Path,
        logger: logging.Logger = None,
    ):
        self.time = start_time
        self.end_time = end_time
        self.time_step = time_step
        
        self.strat = strat
        self.mkt = Market(start_time=start_time - datetime.timedelta(seconds=1), contract=contract, data_dir=data_dir)

        self._strat_pending_orders: "Queue[Order]" = Queue()
        self._events: "Queue[Event]" = Queue()
        
        self.logger = logger or logging.getLogger(__name__)

    def _process_pending_orders(self) -> "Queue[StrategyTrade]":
        q: "Queue[StrategyTrade]" = Queue()
        while not self._strat_pending_orders.empty:
            order = self._strat_pending_orders.get_nowait()
            if isinstance(order, MktOrder):
                trade = self._simulate_mkt_order(order)
                q.put(trade)
        return q

    def _simulate_mkt_order(self, order: MktOrder) -> StrategyTrade:
        # delay = datetime.timedelta(seconds=1)  #TODO: random?
        # self.time += delay
        # self.mkt.set_time(time=self.time)
        book = self.mkt.get_book_best()
        if order.lots > 0:
            price = book.ask
        else:
            price = book.bid
        trade = StrategyTrade(
            time=self.time,
            price=price,
            lots=order.lots
        )
        return trade

    def _process_events(self, events: "Queue[Event]"):
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
            self.mkt.set_time(time=self.time)
            
            strat_trades: "Queue[StrategyTrade]" = self._process_pending_orders()
            self._process_events(events=strat_trades)
            
            mkt_events: Queue[Event] = self.mkt.get_events()
            self._process_events(events=mkt_events)

            self.time += self.time_step
