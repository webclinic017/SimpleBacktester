import datetime
import pathlib
from typing import List, Union, Optional
import ib_insync as ibi
import trading_calendars as tc

from simplebt.events.market import MktOpen, MktClose
from simplebt.historical_data.load.ticks_loader import BidAskTicksLoader, TradesTicksLoader
from simplebt.events.generic import Event, Nothing
from simplebt.events.batches import ChangeBestBatch, MktTradeBatch
from simplebt.book import BookL0


class Market:
    def __init__(
        self,
        start_time: datetime.datetime,
        contract: ibi.Contract,
        data_dir: pathlib.Path
    ):
        self.time = start_time
        self.contract = contract

        self.calendar: tc.TradingCalendar = tc.get_calendar(contract.exchange)
        self._is_mkt_open: bool = self.calendar.is_open_on_minute(self.time)
        self._cal_event: Optional[Union[MktOpen, MktClose]] = None

        self._trades_loader = TradesTicksLoader(contract, chunksize=50000, data_dir=data_dir)
        self._bidask_loader = BidAskTicksLoader(contract, chunksize=50000, data_dir=data_dir)
        
        self._trades_ticks = MktTradeBatch(events=[], time=start_time)
        self._bidask_ticks = ChangeBestBatch(events=[], time=start_time)
        self._load_events(time=self.time)
        self._best: BookL0 = self._bidask_ticks.events[-1].best

    def get_book_best(self):
        return self._best

    def set_time(self, time: datetime.datetime):
        if self.time != time:
            self.time = time
        self._create_cal_events(time=time)
        self._load_events(time=time)
    
    def get_events(self) -> List[Event]:
        q: List[Event] = []  # FIFO
        if self._cal_event:
            q.append(self._cal_event)
        if self._trades_ticks.events:
            q += self._trades_ticks
        if self._bidask_ticks.events:
            q += self._bidask_ticks
        if not q:
            q.append(Nothing(time=self.time))
        return q
    
    def _load_events(self, time: datetime.datetime):
        self._trades_ticks = self._trades_loader.get_ticks_batch_by_time(time=time)
        self._bidask_ticks = self._bidask_loader.get_ticks_batch_by_time(time=time)

        if self._bidask_ticks.events:
            self._l0 = self._bidask_ticks.events[-1]

    def _create_cal_events(self, time: datetime.datetime):
        self._cal_event = None
        is_mkt_open: bool = self.calendar.is_open_on_minute(time)
        if is_mkt_open != self._is_mkt_open:
            if is_mkt_open:
                self._cal_event = MktOpen(time=time)
            else:
                self._cal_event = MktClose(time=time)
