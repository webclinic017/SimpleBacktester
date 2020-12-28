import datetime
from queue import Queue
from ib_insync import Contract
from src.historical_data.load.ticks_loader import BidAskTicksLoader, TradesTicksLoader
from src.events import Event, Nothing, ChangeBestBatch, MktTradeBatch
from src.book import BookL0

class Market:
    def __init__(
        self,
        start_time: datetime.datetime,
        contract: Contract
    ):
        self.time = start_time
        self.contract = contract
        self._trades_loader = TradesTicksLoader(contract, chunksize=50000)
        self._bidask_loader = BidAskTicksLoader(contract, chunksize=50000)
        
        self._trades_ticks = MktTradeBatch(events=[], time=start_time)
        self._bidask_ticks = ChangeBestBatch(events=[], time=start_time)
        self._load_events(time=self.time)
        self._best: BookL0 = self._bidask_ticks.events[-1].best

    def get_book_best(self):
        return self._best

    def set_time(self, time: datetime.datetime):
        if self.time != time:
            self.time = time
        self._load_events(time=time)
    
    def get_events(self) -> "Queue[Event]":
        q: Queue[Event] = Queue()  # FIFO
        if self._trades_ticks.events:
            q.put(self._trades_ticks)
        if self._bidask_ticks.events:
            q.put(self._bidask_ticks)
        if q.empty():
            q.put(Nothing(time=self.time))
        return q
    
    def _load_events(self, time: datetime.datetime):
        self._trades_ticks = self._trades_loader.get_ticks_batch_by_time(time=time)
        self._bidask_ticks = self._bidask_loader.get_ticks_batch_by_time(time=time)

        if self._bidask_ticks.events:
            self._l0 = self._bidask_ticks.events[-1]
