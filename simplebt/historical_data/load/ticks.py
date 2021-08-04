import abc
import datetime
import logging
from typing import List
from ib_insync import Contract
from simplebt.db import DbTicks
from simplebt.events.market import ChangeBestEvent, MktTradeEvent
from simplebt.events.batches import ChangeBestBatchEvent, MktTradeBatchEvent
from simplebt.book import BookL0


logger = logging.getLogger("TicksLoader")


class TicksLoader(abc.ABC):
    def __init__(
            self,
            contract: Contract,
            tick_type: str,
            date_col: str,
    ):
        self._db = DbTicks(contract=contract, tick_type=tick_type)
        with self._db.conn.cursor() as cur:
            cur.execute("SET TIME ZONE 'UTC';")
        self._date_col: str = date_col
        logger.debug("Initialized loader")

    def _select_query(self, time: datetime.datetime) -> str:
        return f"""
        SELECT * FROM {self._db.table_ref.schema}.{self._db.table_ref.table}
        WHERE {self._date_col} = '{time}'
        ORDER BY pk ASC
        """

    def _get_ticks_by_time(self, time: datetime.datetime):
        """Returns a list of tuples of different sizes depending on the table queried"""
        with self._db.conn.cursor() as cur:
            cur.execute(self._select_query(time=time))
            rows = cur.fetchall()
        return rows

    @abc.abstractmethod
    def get_ticks_batch_by_time(self, time: datetime.datetime):
        raise NotImplementedError


class BidAskTicksLoader(TicksLoader):
    def __init__(self, contract: Contract):
        super().__init__(
            contract=contract,
            tick_type="BID_ASK",
            date_col="time",
        )

    def get_ticks_batch_by_time(self, time: datetime.datetime) -> ChangeBestBatchEvent:
        ticks = self._get_ticks_by_time(time=time)
        event_list: List[ChangeBestEvent] = []
        for db_time, bid, ask, bid_size, ask_size, _, _, _ in ticks:
            l0 = BookL0(bid=bid, ask=ask, bid_size=bid_size, ask_size=ask_size, time=time)
            event = ChangeBestEvent(best=l0, time=time)
            event_list.append(event)
        return ChangeBestBatchEvent(events=event_list, time=time)


class TradesTicksLoader(TicksLoader):
    def __init__(self, contract: Contract):
        super().__init__(
            contract=contract,
            tick_type="TRADES",
            date_col="time",
        )

    def get_ticks_batch_by_time(self, time: datetime.datetime) -> MktTradeBatchEvent:
        ticks = self._get_ticks_by_time(time=time)
        event_list = []
        for db_time, price, size, _, _ in ticks:
            trade = MktTradeEvent(price=price, size=size, time=time)
            event_list.append(trade)
        return MktTradeBatchEvent(events=event_list, time=time)
