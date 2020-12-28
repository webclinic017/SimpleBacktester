import abc
import datetime
import numpy as np
import pandas as pd
import pathlib
from typing import List, Dict, Generator
from ib_insync import Contract
from src.db import DbTicks
from src.resources.config import DELIMITER, DATA_DIR
from src.events import ChangeBest, MktTrade, ChangeBestBatch, MktTradeBatch
from src.book import BookL0
from src.utils import to_utc

class TicksLoader(abc.ABC):
    def __init__(
        self,
        contract: Contract,
        tick_type: str,
        data_dir: pathlib.Path,
        dtypes: Dict[str, np.dtype],
        date_col: str,
        chunksize: int,
    ):
        table_name: str = DbTicks.get_table_reference(contract=contract, tick_type=tick_type).table
        csv_path: pathlib.Path = data_dir / f"{table_name}.csv"
        self.csv_path = csv_path.resolve()
        if not csv_path.exists():
            self._ticks_postgres_to_csv(contract, tick_type, self.csv_path)

        self.chunks = self._read_csv_chunks(dtypes=dtypes, date_col=date_col, chunksize=chunksize)
        self.out_of_ticks: bool = False
        self._ticks: pd.DataFrame = pd.DataFrame()
        self.load_chunk()

    @staticmethod
    def _ticks_postgres_to_csv(contract, tick_type, csv_path):
        db = DbTicks(contract=contract, tick_type=tick_type)
        select_q = f"SELECT * FROM {db.table_ref.schema}.{db.table_ref.table} ORDER BY pk ASC"
        copy_q = f"COPY ({select_q}) TO STDOUT WITH (FORMAT CSV, HEADER, DELIMITER '{DELIMITER}')"
        with db.conn.cursor() as cur:
            with open(csv_path, "w") as f_output:
                cur.copy_expert(copy_q, f_output)

    def _read_csv_chunks(self, dtypes: Dict[str, np.dtype], date_col: str, chunksize: int) -> Generator[pd.DataFrame, None, None]:
        return pd.read_csv(
            filepath_or_buffer=self.csv_path,
            delimiter=DELIMITER,
            dtype=dtypes,
            parse_dates=[date_col],
            date_parser=lambda t: to_utc(pd.to_datetime(t)),
            usecols=list(dtypes.keys()) + [date_col],
            index_col=date_col,
            low_memory=True,
            chunksize=chunksize,
        )

    def load_chunk(self):
        self._ticks = self._load_chunk()

    def _load_chunk(self) -> pd.DataFrame:
        def _load_chunk_rec():
            try:
                df = next(self.chunks)
                if df.index[0] == df.index[-1]:
                    return pd.concat((df, _load_chunk_rec()), axis=0)
            except StopIteration:
                df = pd.DataFrame()
                self.out_of_ticks = True
            return df
        return _load_chunk_rec()

    def get_ticks_by_time(self, time: datetime.datetime) -> pd.DataFrame:
        def get_ticks_by_time_rec():
            if self.out_of_ticks is True:
                return pd.DataFrame()
            elif self._ticks.index[0] <= time <= self._ticks.index[-1]:
                return self._ticks.loc[time:time]
            else:
                self.load_chunk()
                return get_ticks_by_time_rec()
        return get_ticks_by_time_rec()

    @abc.abstractmethod
    def get_ticks_batch_by_time(self, time: datetime.datetime):
        raise NotImplementedError


class BidAskTicksLoader(TicksLoader):
    def __init__(self, contract: Contract, chunksize: int, data_dir: pathlib.Path = DATA_DIR):
        dtypes = {
            "bid": np.dtype(float),
            "ask": np.dtype(float),
            "bid_size": np.dtype(int),
            "ask_size": np.dtype(int),
        }
        super().__init__(
            contract=contract,
            tick_type="BID_ASK",
            data_dir=data_dir,
            dtypes=dtypes,
            date_col="time",
            chunksize=chunksize
        )

    def get_ticks_batch_by_time(self, time: datetime.datetime) -> ChangeBestBatch:
        ticks_df = self.get_ticks_by_time(time=time)
        event_list: List[ChangeBest] = []
        for bid, ask, bid_size, ask_size in ticks_df.itertuples(index=False):
            l0 = BookL0(bid=bid, ask=ask, bid_size=bid_size, ask_size=ask_size, time=time)
            event = ChangeBest(best=l0, time=time)
            event_list.append(event)
        return ChangeBestBatch(events=event_list, time=time)


class TradesTicksLoader(TicksLoader):
    def __init__(self, contract: Contract, chunksize: int, data_dir: pathlib.Path = DATA_DIR):
        dtypes = {"price": np.dtype(float), "size": np.dtype(int)}
        super().__init__(
            contract=contract,
            tick_type="TRADES",
            data_dir=data_dir,
            dtypes=dtypes,
            date_col="time",
            chunksize=chunksize
        )

    def get_ticks_batch_by_time(self, time: datetime.datetime) -> MktTradeBatch:
        ticks_df = self.get_ticks_by_time(time=time)
        event_list = []
        for price, size in ticks_df.itertuples(index=False):
            trade = MktTrade(price=price, size=size, time=time)
            event_list.append(trade)
        return MktTradeBatch(events=event_list, time=time)
