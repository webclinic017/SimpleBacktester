import itertools
import logging
import datetime
import pathlib
import queue
import pandas as pd
from typing import Dict, List, Optional
import ib_insync as ibi

from simplebt.book import BookL0
from simplebt.events.batches import PendingTickerEvent, PendingTickerSetEvent
from simplebt.events.generic import Event
from simplebt.events.orders import OrderReceivedEvent, OrderCanceledEvent
from simplebt.events.position import PnLSingleEvent
from simplebt.market import Market
from simplebt.events.market import ChangeBestEvent, FillEvent
from simplebt.orders import Order
from simplebt.position import Position, PnLSingle
from simplebt.strategy import StrategyInterface
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

        self._events: "queue.Queue[Event]" = queue.Queue()
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

    def _update_positions(self, fill_events: List[FillEvent]):
        def update_single_position(position: Position):
            if position.contract in map(lambda e: e.trade.order.contract, fill_events):
                for event in filter(lambda x: x.order.contract == position.contract, fill_events):
                    position.update(fill=event.trade)
            return position

        self._positions = list(map(lambda p: update_single_position(p), self._positions))

    def _set_mkts_time(self, time: datetime.datetime):
        for mkt in self.mkts.values():
            mkt.set_time(time=time)

    def _get_events_from_mkts(self) -> "queue.Queue[Event]":
        def _get_mkts_fills() -> List[FillEvent]:
            fills: List[FillEvent] = []
            for mkt in self.mkts.values():
                fills += mkt.get_fills()
            fills = list(sorted(fills, key=lambda f: f.time, reverse=False))
            self._update_positions(fills)
            return fills

        def _get_pending_tickers() -> PendingTickerSetEvent:
            _tickers: List[PendingTickerEvent] = []
            for mkt in self.mkts.values():
                _t: Optional[PendingTickerEvent] = mkt.get_pending_ticker()
                if _t:
                    _tickers.append(_t)
            # returning a set just to simulate IBKR's behavior
            return PendingTickerSetEvent(time=self.time, events=_tickers)

        fill_events: List[FillEvent] = _get_mkts_fills()
        pending_ticker_events: PendingTickerSetEvent = _get_pending_tickers()
        pnl_events: List[PnLSingleEvent] = list(itertools.chain(*(self._get_pnl_events(ticker=t) for t in pending_ticker_events.events)))

        q: "queue.Queue[Event]" = queue.Queue()
        # NOTE: The order I insert events in the queue is debatable
        for e in fill_events:
            q.put(e)
        for e in pnl_events:
            q.put(e)
        if pending_ticker_events:
            q.put(pending_ticker_events)  # IBKR pass these in batches
        return q

    def _get_pnl_events(self, ticker: PendingTickerEvent) -> List[PnLSingleEvent]:
        """
        If there are change best, the method calculates a pnl and spits an event
        """
        def _calc_pnl() -> List[PnLSingle]:
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
        pnl_events = [PnLSingleEvent(time=self.time, pnl=pnl) for pnl in _calc_pnl()]
        return pnl_events

    def _forward_event_to_strategy(self, event: Event):
        if isinstance(event, PendingTickerSetEvent):
            self.strat.on_pending_tickers(pending_tickers_event=event)
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
            if trades:
                df = pd.DataFrame(
                    [(t.time, t.fills, t.order) for t in trades],
                    columns=["time", "fills", "order"]
                )
                df.to_csv(save_path)
