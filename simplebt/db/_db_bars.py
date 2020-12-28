import psycopg2
import psycopg2.extras
import datetime
from ib_insync import Contract
from ib_insync.objects import BarDataList
from typing import Optional
from simplebt.db import Db, TableRef
from simplebt.resources.config import BARS_SCHEMA_DICT


class DbBars(Db):
    def __init__(self, contract: Contract, bar_type: str, bar_size: str):
        super().__init__()
        self.contract = contract
        self.bar_type = bar_type
        self.bar_size = bar_size
        self.table_ref = self.get_table_reference(contract=contract, bar_type=bar_type, bar_size=bar_size)
        self.create_table()

    @staticmethod
    def get_table_reference(
        contract: Contract, bar_type: str, bar_size: str
    ) -> TableRef:
        """
        Return named tuple with schema and table names.
        If future it will include the last open_trade date in the name, otherwise just symbol and conId.
        """
        barsize: str = bar_size.replace(" ", "")
        if contract.secType == "Forex":
            schema_name = "fx_bars"
            table_name = f"{contract.symbol}{contract.currency}_{barsize}_{bar_type}".lower()
        else:
            expiry: str = contract.lastTradeDateOrContractMonth if contract.secType == "FUT" else ""
            schema_name = BARS_SCHEMA_DICT[bar_type]
            table_name = f"{contract.symbol}{expiry}_{barsize}_{contract.conId}".lower()
        return TableRef(schema_name, table_name)

    def create_table(self):
        with self.conn.cursor() as cursor:
            cursor.execute(
                f"""
                create table if not exists {self.table_ref.schema}.{self.table_ref.table} (
                     date       timestamptz primary key
                    ,open       float
                    ,high       float
                    ,low        float
                    ,close      float
                    ,volume     bigint
                    ,average    float
                    ,barCount   integer
                );
            """
            )

    def insert_execute_values_iterator(
        self, bars: BarDataList, page_size: int = 100
    ):
        """
        THANKS: https://hakibenita.com/fast-load-data-python-postgresql
        """
        table = f"{self.table_ref.schema}.{self.table_ref.table}"
        with self.conn.cursor() as cursor:
            psycopg2.extras.execute_values(
                cursor,
                "insert into " + table + " values %s;",
                (
                    (
                        bar.date,
                        bar.open,
                        bar.high,
                        bar.low,
                        bar.close,
                        bar.volume,
                        bar.average,
                        bar.barCount,
                    )
                    for bar in bars
                ),
                page_size=page_size,
            )

    def get_bar_date(
        self, func: str = "min"
    ) -> Optional[datetime.datetime]:
        if func not in ("min", "max"):
            raise ValueError("Either min or max")
        date: Optional[datetime.datetime] = None
        with self.conn.cursor() as cursor:
            cursor.execute("set TimeZone = UTC;")
            cursor.execute(
                f"select {func}(date) from {self.table_ref.schema}.{self.table_ref.table};"
            )
            result = cursor.fetchone()[0]  # each result is a tuple, that's why the [0] slicing
        if result is not None:
            date = result.replace(tzinfo=datetime.timezone.utc)
        return date
