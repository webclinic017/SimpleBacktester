import datetime
import pathlib
import random
from typing import List, Union, Optional
import ib_insync as ibi
import pandas as pd
import trading_calendars as tc

from simplebt.events.market import MktOpen, MktClose, StrategyTrade
from simplebt.historical_data.load.ticks import BidAskTicksLoader, TradesTicksLoader
from simplebt.events.generic import Event, Nothing
from simplebt.events.batches import ChangeBestBatch, MktTradeBatch
from simplebt.book import BookL0
from simplebt.events.orders import Order, MktOrder, LmtOrder


class Market:
    def __init__(
        self,
        start_time: datetime.datetime,
        contract: ibi.Contract,
        data_dir: pathlib.Path,
        chunksize: int = None
    ):
        self.time = start_time
        self.contract = contract

        # NOTE: beware this might not be accurate
        self.calendar: tc.TradingCalendar = tc.get_calendar(contract.exchange)
        self._is_mkt_open: bool = self.calendar.is_open_on_minute(pd.Timestamp(self.time))

        if not chunksize:
            chunksize = 50000
        self._trades_loader = TradesTicksLoader(contract, chunksize=chunksize, data_dir=data_dir)
        self._bidask_loader = BidAskTicksLoader(contract, chunksize=chunksize, data_dir=data_dir)

        self._open_orders: List[Order] = []

        # The following collections/variables can be accessed by self.get_events()
        self._trades_ticks = MktTradeBatch(events=[], time=start_time)
        self._bidask_ticks = ChangeBestBatch(events=[], time=start_time)
        self._best: Optional[BookL0] = None
        self._cal_event: Optional[Union[MktOpen, MktClose]] = None
        self._strat_trades: List[StrategyTrade] = []
        # this method may populate the collections above
        self.set_time(time=self.time)

    def get_book_best(self) -> BookL0:
        return self._best

    def add_order(self, order: Order):
        self._open_orders.append(order)

    def set_time(self, time: datetime.datetime):
        """
        Set_time() updates the collection/variables that caches mkt events.
        Until the method is called again, these events can be queried by external actors.
        """
        if self.time != time:
            self.time = time
        self._cal_event = self._create_cal_events(time=time)

        self._trades_ticks = self._trades_loader.get_ticks_batch_by_time(time=time)
        self._bidask_ticks = self._bidask_loader.get_ticks_batch_by_time(time=time)

        if self._bidask_ticks.events:
            self._best = self._bidask_ticks.events[-1]

        if self._is_mkt_open:
            self._strat_trades = self._process_pending_orders()
        else:
            self._strat_trades = []

    def get_events(self) -> List[Event]:
        events: List[Event] = []  # FIFO
        if self._cal_event:
            events.append(self._cal_event)
        if self._strat_trades:
            events += self._strat_trades  # append as single events
        if self._trades_ticks.events:
            events.append(self._trades_ticks)  # append as batch
        if self._bidask_ticks.events:
            events.append(self._bidask_ticks)
        if not events:
            # TODO: remove
            events.append(Nothing(time=self.time))
        return events
    
    def _create_cal_events(self, time: datetime.datetime) -> Optional[Union[MktOpen, MktClose]]:
        event = None
        is_mkt_open: bool = self.calendar.is_open_on_minute(pd.Timestamp(time))
        if is_mkt_open != self._is_mkt_open:
            if is_mkt_open:
                event = MktOpen(time=time)
            else:
                event = MktClose(time=time)
        return event

    def _process_pending_orders(self) -> List[StrategyTrade]:
        trades: List[StrategyTrade] = []
        not_matched: List[Order] = []
        for order in self._open_orders:
            trade: Optional[StrategyTrade] = None
            if isinstance(order, MktOrder):
                trade = self._exec_mkt_order(order=order)
            elif isinstance(order, LmtOrder):
                trade = self._exec_lmt_order(order=order)
            if trade:
                trades.append(trade)
            else:
                # NOTE: treating everything as a Good Til Cancelled for the moment
                not_matched.append(order)
        self._open_orders = not_matched
        return trades

    def _exec_mkt_order(self, order: MktOrder) -> Optional[StrategyTrade]:
        # if new changeBest available, pick a random one
        if self._bidask_ticks.events:
            best = random.choice(self._bidask_ticks.events)
        else:  # otherwise default to the L0 retrieved from the latest changeBest
            best = self._best
        # pick the side according to the order type (Long vs Short)
        if order.lots > 0:
            price = best.ask
            if best.ask_size < order.lots:
                return None
        else:
            price = best.bid
            if best.bid_size < abs(order.lots):
                return None
        trade = StrategyTrade(
            time=self.time,
            price=price,
            lots=order.lots
        )
        return trade

    def _exec_lmt_order(self, order: LmtOrder) -> Optional[StrategyTrade]:
        raise NotImplementedError
