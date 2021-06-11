import itertools
import logging
import datetime
import pathlib
import random
import queue
import pandas as pd
from typing import Dict, Iterable, List, Optional, Set, Union
import ib_insync as ibi

from simplebt.book import BookL0
from simplebt.events.batches import PendingTickerEvent
from simplebt.events.generic import Event
from simplebt.events.orders import OrderReceivedEvent, OrderCanceledEvent
from simplebt.events.position import PnLSingleEvent
from simplebt.market import Market
from simplebt.events.market import ChangeBestEvent, FillEvent
from simplebt.orders import Order
from simplebt.position import Position, PnLSingle
from simplebt.strategy import StrategyInterface

# NOTE: The queue lib still doesn't go well with type annotations
#  Using queue.Queue[Event] raises the Exception: type object is not subscriptable
#  Declaring `EventQueue = typing.NewType("EventQueue", queue.Queue[Event])` doesn't work either
#  The only workaround is to enclose it in a str like "queue.Queue[Event]" but I don't like that
from simplebt.trade import StrategyTrade

logger = logging.getLogger("Backtester")
logger.setLevel(logging.INFO)


class Backtester:
    def __init__(
        self,
        strat: StrategyInterface,
        contracts: List[ibi.Contract],
        start_time: datetime.datetime,
        end_time: datetime.datetime,
        time_step: datetime.timedelta,
        data_dir: pathlib.Path,
        chunksize: int = None,
        # shuffle_events: bool = None,
    ):
        if start_time.tzinfo != datetime.timezone.utc:
            raise ValueError(f"Parameter start_time should have tzinfo=datetime.timezone.utc, got {start_time.tzinfo}")
        self.time = start_time
        if end_time.tzinfo != datetime.timezone.utc:
            raise ValueError(f"Parameter end_time should have tzinfo=datetime.timezone.utc, got {end_time.tzinfo}")
        self.end_time = end_time
        self.time_step = time_step
       
        if not chunksize:
            logger.info("Setting chunksize to 1 million rows")
            chunksize = int(1e6)
        self.strat = strat
        self.mkts: Dict[int, Market] = {
            c.conId: Market(contract=c, start_time=start_time, data_dir=data_dir, chunksize=chunksize)
            for c in contracts
        }
        self._positions: List[Position] = [Position(c) for c in contracts]

        self._events = queue.Queue()
        # self.shuffle_events: bool = shuffle_events or False

    # @property
    def positions(self) -> List[Position]:
        return self._positions

    def get_best(self, contract: ibi.Contract) -> BookL0:
        return self.mkts[contract.conId].get_book_best()

    def schedule(self, *args, **kwargs):
        pass

    def place_order(self, order: Order) -> StrategyTrade:
        mkt: Market = self.mkts[order.contract.conId]
        trade: StrategyTrade = mkt.add_order(order=order)
        self._events.put(OrderReceivedEvent(time=trade.time, order=trade.order))
        return trade

    def cancel_order(self, order: Order) -> StrategyTrade:
        mkt: Market = self.mkts[order.contract.conId]
        # if random.randint(0, 10) > 1:  # some randomness here
        canceled_trade: StrategyTrade = mkt.cancel_order(order=order)
        self._events.put(OrderCanceledEvent(time=canceled_trade.time, order=canceled_trade.order))
        return canceled_trade

    def _update_positions(self, fills: List[StrategyTrade]):
        def update_single_position(position: Position):
            if position.contract in map(lambda fill: fill.order.contract, fills):
                for f in filter(lambda x: x.order.contract == position.contract, fills):
                    position.update(fill=f)
            return position

        self._positions = list(map(lambda p: update_single_position(p), self._positions))

    def _set_mkts_time(self, time: datetime.datetime):
        for mkt in self.mkts.values():
            mkt.set_time(time=time)

    def _get_events_from_mkts(self) -> queue.Queue:
        def _get_mkts_fills() -> List[StrategyTrade]:
            fills: List[StrategyTrade] = []
            for mkt in self.mkts.values():
                fills += mkt.get_fills()
            fills = list(sorted(fills, key=lambda f: f.time, reverse=False))
            self._update_positions(fills)
            return fills

        def _get_pending_tickers() -> Set[PendingTickerEvent]:
            _tickers: List[PendingTickerEvent] = []
            for mkt in self.mkts.values():
                _t: Optional[PendingTickerEvent] = mkt.get_pending_ticker()
                if _t:
                    _tickers.append(_t)
            # returning a set just to simulate IBKR's behavior
            return set(_tickers)

        q: queue.Queue = queue.Queue()
        # all_events: Iterable[Event] = itertools.chain.from_iterable(
        #     (mkt.get_events() for mkt in self.mkts.values())
        # )
        # if self.shuffle_events:
        #     all_events = sorted(all_events, key=lambda k: random.random())
        # for e in all_events:
        #     q.put(e)
        # The above is replaced by
        for fill in _get_mkts_fills():
            q.put(fill)
        tickers: Set[PendingTickerEvent] = _get_pending_tickers()
        for t in tickers:
            pnl_list: List[PnLSingle] = self._calc_pnl(ticker=t)
            for pnl in pnl_list:
                q.put(PnLSingleEvent(time=self.time, pnl=pnl))
        if tickers:
            q.put(tickers)
        return q

    def _calc_pnl(self, ticker: PendingTickerEvent) -> List[PnLSingle]:
        pnls: List[PnLSingle] = []
        position: Position = next(filter(lambda p: p.contract == ticker.contract, self.positions()))
        if position.position != 0:
            change_bests = list(filter(lambda e: isinstance(e, ChangeBestEvent), ticker.events))
            for change_best in change_bests:
                bid, ask = change_best.best.bid, change_best.best.ask
                if position.position > 0:
                    delta = bid - position.avg_cost
                else:
                    delta = position.avg_cost - ask
                pnl = delta * position.position
                pnls.append(PnLSingle(conId=ticker.contract.conId, unrealizedPnL=pnl))
        return pnls

    def _forward_event_to_strategy(self, event: Event):
        if isinstance(event, set) and isinstance(event[0].events, PendingTickerEvent):
            self.strat.on_pending_tickers(event)
        elif isinstance(event, OrderReceivedEvent) or isinstance(event, OrderCanceledEvent):
            self.strat.on_new_order_event(event)
        elif isinstance(event, FillEvent):
            self.strat.on_fill(trade=event.trade, fill=event.fill)
        elif isinstance(event, PnLSingleEvent):
            self.strat.on_pnl(pnl=event.pnl)
        else:
            raise ValueError(f"Got unexpected event: {event}")

    def run(self, save_path: pathlib.Path = None):
        self.strat.bt = self
        while self.time <= self.end_time:
            logger.info(f"Next timestamp: {self.time}")

            self._set_mkts_time(time=self.time)
            mkt_events: queue.Queue = self._get_events_from_mkts()

            self.strat.set_time(time=self.time)
            while not mkt_events.empty():
                e = mkt_events.get_nowait()
                self._forward_event_to_strategy(e)

            self.time += self.time_step

        logger.info("Hey jerk! We're done backtesting. You happy with the results?")
        if save_path:
            trades: List[StrategyTrade] = self.strat.get_trades()
            df = pd.DataFrame(
                [(t.time, t.price, t.lots, t.order.time) for t in trades],
                columns=["time", "price", "lots", "order_time"]
            )
            df.to_csv(save_path)
