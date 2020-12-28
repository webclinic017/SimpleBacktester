import psycopg2
import psycopg2.extras
import datetime
from ib_insync import Contract
from ib_insync.objects import HistoricalTickLast, HistoricalTickBidAsk
from typing import Iterator, Optional, Union, Dict, Tuple
from src.db import Db, TableRef
from src.resources.config import TICKS_SCHEMA_NAME
from src.utils import to_utc


CREATE_TABLE_QUERIES: Dict[str, str] = {
    "TRADES": """
        create table if not exists {schema}.{table} (
             time       timestamptz
            ,price      float
            ,size       integer
            ,exchange   varchar(50)
            ,pk         varchar(255) primary key
        );
        create index if not exists {table}_time_ix on {schema}.{table} using btree(time);
    """,
    "BID_ASK": """
        create table if not exists {schema}.{table} (
             time           timestamptz
            ,bid            float
            ,ask            float
            ,bid_size       integer
            ,ask_size       integer
            ,bid_decrease   boolean
            ,ask_increase   boolean
            ,pk             varchar(255) primary key
        );
        create index if not exists {table}_time_ix on {schema}.{table} using btree(time);
    """,
}


def extract_tick_info(
    tick: Union[HistoricalTickLast, HistoricalTickBidAsk]
) -> Union[
    Tuple[datetime.datetime, float, int, str],
    Tuple[datetime.datetime, float, float, int, int, bool, bool],
]:
    if isinstance(tick, HistoricalTickLast):
        return tick.time, tick.price, tick.size, tick.exchange
    elif isinstance(tick, HistoricalTickBidAsk):
        return (
            tick.time,
            tick.priceBid,
            tick.priceAsk,
            tick.sizeBid,
            tick.sizeAsk,
            tick.tickAttribBidAsk.bidPastLow,
            tick.tickAttribBidAsk.askPastHigh,
        )


def hashed_tick_info_gen(
    ticks: Iterator[Union[HistoricalTickLast, HistoricalTickBidAsk]]
):
    """
    Based on the assumption that the IBKR API will continue to include all ticks belonging to the same second in a single request
    """
    i = 0
    for t in ticks:
        i += 1
        hashed_tick_info = extract_tick_info(t) + (f"{t.time}_{i}",)
        yield hashed_tick_info


class DbTicks(Db):
    def __init__(self, contract: Contract, tick_type: str, db_connection=None):
        super().__init__(db_connection=db_connection)
        self.table_ref: TableRef = self.get_table_reference(
            contract=contract, tick_type=tick_type
        )
        self.create_table_query: str = CREATE_TABLE_QUERIES[tick_type].format(
            schema=self.table_ref.schema, table=self.table_ref.table
        )

    @staticmethod
    def get_table_reference(contract: Contract, tick_type: str) -> TableRef:
        """
        Return named tuple with schema and table names.
        If future it will include the last open_trade date in the name, otherwise just symbol and conId.
        """
        exp: str = (
            contract.lastTradeDateOrContractMonth if contract.secType == "FUT" else ""
        )
        table_name: str = f"{contract.symbol}{exp}_{contract.conId}_{tick_type}".lower()
        return TableRef(TICKS_SCHEMA_NAME, table_name)

    def get_oldest_tick_date(self) -> Optional[datetime.datetime]:
        with self.conn.cursor() as cursor:
            cursor.execute("set TimeZone = UTC;")
            cursor.execute(
                f"select min(time) from {self.table_ref.schema}.{self.table_ref.table};"
            )
            date = cursor.fetchone()[0]  # each result is a tuple, that's why the [0] slicing
        if isinstance(date, datetime.datetime):
            return to_utc(date)
        else:
            return None

    def create_table(self) -> None:
        with self.conn.cursor() as cursor:
            cursor.execute(self.create_table_query)

    def insert_execute_values_iterator(
        self,
        ticks: Iterator[Union[HistoricalTickLast, HistoricalTickBidAsk]],
        page_size: int = 100,
    ) -> None:
        """
        THANKS: https://hakibenita.com/fast-load-data-python-postgresql
        """
        table = f"{self.table_ref.schema}.{self.table_ref.table}"
        to_insert = hashed_tick_info_gen(ticks)
        with self.conn.cursor() as cursor:
            psycopg2.extras.execute_values(
                cursor,
                "insert into " + table + " values %s;",
                to_insert,
                page_size=page_size,
            )
