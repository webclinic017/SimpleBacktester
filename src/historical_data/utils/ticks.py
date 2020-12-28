"""
The way reqHistoricalTicks works backward is clear.
Since it still works with kind of second bars it won't include ticks registered at endDateTime.
Sometimes it gets stuck at the first tick of the day and starts returning empty lists,
at that point the workaround working for me is to bring the clock to the first minute of the day (more under updateEndDateTime).

But going forward, it doesn't behave the same!
It's gonna get stuck at the last tick of the day and start returning the same one tick instead of empty lists.
I guess that's because, as opposed to the logic endDateTime, the function with startDateTime is including the input date into the return list.
"""
import datetime
import asyncio
from ib_insync import Contract
from ib_insync.objects import HistoricalTickLast, HistoricalTickBidAsk
from typing import List, Union
from src.db import DbTicks
from src.logger import get_logger
from src.utils import strptime, to_utc
from src.utils.ib import start_ib

logger = get_logger(name=__name__)


def download_and_store_hist_ticks(
    client_id: int,
    port: int,
    timeout: int,
    contract: Contract,
    start_datetime: datetime.datetime,
    tick_type: str = "TRADES",
    max_attempts: int = 10,
):
    """
    Download and save hist ticks to db
    TODO: consider splitting this in
        - get ticks component, yielding ticks from while lopp
        - insert into db component
    """

    ib = start_ib(client_id=client_id, port=port, timeout=timeout)

    db = DbTicks(contract=contract, tick_type=tick_type)
    db.create_table()
    
    end_datetime: datetime.datetime = _choose_end_date_download(db, contract)

    n_trials: int = 0
    while (end_datetime > start_datetime) and (n_trials < max_attempts):
        try:
            logger.info(f"{end_datetime}")
            ticks = ib.reqHistoricalTicks(
                contract=contract,
                startDateTime="",  # one of startDateTime / endDateTime must be blank
                endDateTime=end_datetime,
                numberOfTicks=1000,
                whatToShow=tick_type,
                ignoreSize=False,
                useRth=False,
            )
            end_datetime = _update_end_datetime(ticks, end_datetime)
            if len(ticks) > 0:
                n_trials = 0
                db.insert_execute_values_iterator(ticks=filter(_istick, ticks))
            else:
                n_trials += 1
                logger.info(f"No ticks returned. Trial: {n_trials}/{max_attempts}")
        except asyncio.TimeoutError:
            logger.info("-----------Timeout-----------")
            ib.disconnect()
            ib.sleep(secs=timeout)
            ib = start_ib(client_id=client_id, port=port, timeout=timeout)
            end_datetime = _choose_end_date_download(db, contract)
    ib.disconnect()


def _choose_end_date_download(db: DbTicks, contract: Contract) -> datetime.datetime:
    """
    Choose a date to start the backward download of historical ticks.
    Being a backward download, we call it end_date.
    If there are ticks in the db, we'll resume downloading from the oldest available.
    Otherwise we fallback on the estimate_most_recent_tick_date func
    """
    d = db.get_oldest_tick_date()
    if d is None:
        d = _estimate_most_recent_tick_date(contract)
    return d

def _estimate_most_recent_tick_date(contract: Contract) -> datetime.datetime:
    if contract.secType == "FUT":
        _date = strptime(contract.lastTradeDateOrContractMonth)  # + datetime.timedelta(days=1)
    else:
        _date = datetime.datetime.now()
    return to_utc(_date)


def _update_end_datetime(
    ticks: List[Union[HistoricalTickLast, HistoricalTickBidAsk]],
    end_datetime: datetime.datetime,
) -> datetime.datetime:
    """
    Use the oldest tick time if got a non-empty response from the gateway.
    Jump to midnight after the previous day otherwise (ex. Jun-23 h15:56 -> Jun-23 h00:00)
    """
    if len(ticks) > 0:
        end_datetime = ticks[0].time
    else:
        # NOTE: verify that this assumption works under all weathers!
        end_datetime -= datetime.timedelta(
            hours=end_datetime.hour,
            minutes=end_datetime.minute,
            seconds=end_datetime.second,
            microseconds=end_datetime.microsecond,
        )
    return end_datetime


def _istick(t) -> bool:
    return isinstance(t, HistoricalTickLast) or isinstance(t, HistoricalTickBidAsk)
