import datetime
from ib_insync import Future
from src.backtester import Backtester
from src.ns_strategy import NsScalperStrategy
from src.utils import to_utc

contract = Future(
    symbol="BZ",
    conId="97481898",
    exchange="NYMEX",
    lastTradeDateOrContractMonth="20201030"
)

strat = NsScalperStrategy(
    contract=contract,
    size_trigger=100,
    stop_loss=1,
    take_profit=2,
)

start_time = to_utc(datetime.datetime(2020, 9, 30, 1, 46, 48))
end_time = to_utc(datetime.datetime(2020, 10, 23, 20, 32))
time_step = datetime.timedelta(seconds=1)

backtester = Backtester(
    strat=strat,
    contract=contract,
    start_time=start_time,
    end_time=end_time,
    time_step=time_step,
)

backtester.run()
