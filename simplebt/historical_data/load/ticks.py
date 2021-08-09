import abc
import datetime
import logging
from typing import List
from ib_insync import Contract
from simplebt.db import DbTicks
from simplebt.ticker import TickByTickAllLast, TickByTickBidAsk

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

    def get_ticks_batch_by_time(self, time: datetime.datetime) -> List[TickByTickBidAsk]:
        ticks: List[TickByTickBidAsk] = []
        ticks_db = self._get_ticks_by_time(time=time)  # iterator of tuples
        for db_time, bid, ask, bid_size, ask_size, _, _, _ in ticks_db:
            t = TickByTickBidAsk(bid=bid, ask=ask, bid_size=bid_size, ask_size=ask_size, time=time)
            ticks.append(t)
        return ticks


class TradesTicksLoader(TicksLoader):
    def __init__(self, contract: Contract):
        super().__init__(
            contract=contract,
            tick_type="TRADES",
            date_col="time",
        )

    def get_ticks_batch_by_time(self, time: datetime.datetime) -> List[TickByTickAllLast]:
        ticks: List[TickByTickAllLast] = []
        ticks_db = self._get_ticks_by_time(time=time)
        for db_time, price, size, _, _ in ticks_db:
            trade = TickByTickAllLast(price=price, size=size, time=time)
            ticks.append(trade)
        return ticks
