import itertools
import logging
import datetime
import queue
from typing import Dict, List, Optional
import ib_insync as ibi

from simplebt.events.generic import Event
from simplebt.events.orders import OrderReceivedEvent, OrderCanceledEvent
from simplebt.market import Market
from simplebt.events.market import FillEvent, PnLSingleEvent, PendingTickersEvent
from simplebt.orders import Order
from simplebt.position import Position, PnLSingle
from simplebt.strategy import StrategyInterface
from simplebt.ticker import TickByTickBidAsk, Ticker
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
        # shuffle_events: bool = None,
    ):
        if start_time.tzinfo != datetime.timezone.utc:
            raise ValueError(f"Parameter start_time should have tzinfo=datetime.timezone.utc, got {start_time.tzinfo}")
        self.time = start_time
        if end_time.tzinfo != datetime.timezone.utc:
            raise ValueError(f"Parameter end_time should have tzinfo=datetime.timezone.utc, got {end_time.tzinfo}")
        self.end_time = end_time
        self.time_step = time_step
       
        self.strat = strat
        self.mkts: Dict[int, Market] = {
            c.conId: Market(contract=c, start_time=start_time)
            for c in contracts
        }
        self._positions: List[Position] = [Position(c) for c in contracts]

        self._events: "queue.Queue[Event]" = queue.Queue()
        # self.shuffle_events: bool = shuffle_events or False

        self._bt_history_of_events: List[Event] = []

    # @property
    def positions(self) -> List[Position]:
        return self._positions

    def get_best(self, contract: ibi.Contract) -> TickByTickBidAsk:
        return self.mkts[contract.conId].get_book_best()

    def place_order(self, order: Order) -> StrategyTrade:
        mkt: Market = self.mkts[order.contract.conId]
        trade: StrategyTrade = mkt.add_order(order=order)
        self._events.put(OrderReceivedEvent(time=trade.time, trade=trade))
        return trade

    def cancel_order(self, order: Order) -> StrategyTrade:
        mkt: Market = self.mkts[order.contract.conId]
        # if random.randint(0, 10) > 1:  # some randomness here
        canceled_trade: StrategyTrade = mkt.cancel_order(order=order)
        self._events.put(OrderCanceledEvent(time=canceled_trade.time, trade=canceled_trade))
        return canceled_trade

    def _update_positions(self, fill_events: List[FillEvent]):
        def update_single_position(position: Position):
            # if position.contract in map(lambda e: e.trade.order.contract, fill_events):
            for event in filter(lambda x: x.trade.order.contract == position.contract, fill_events):
                position.update(fill=event.fill)
            return position

        self._positions = list(map(lambda p: update_single_position(p), self._positions))

    def _set_mkts_time(self, time: datetime.datetime):
        for mkt in self.mkts.values():
            mkt.set_time(time=time)

    def _add_new_mkt_events_to_queue(self):
        fill_events: List[FillEvent] = self._get_mkts_fill_events()
        pending_tickers: PendingTickersEvent = self._get_pending_tickers_events()
        pnls: List[PnLSingleEvent] = list(itertools.chain(
            *(self._get_pnl_events(ticker=t) for t in pending_tickers.tickers))
        )

        for e in fill_events:
            self._events.put(e)
        for e in pnls:
            self._events.put(e)
        if pending_tickers:
            self._events.put(pending_tickers)  # IBKR pass these in batches

    def _get_mkts_fill_events(self) -> List[FillEvent]:
        fills: List[FillEvent] = []
        for mkt in self.mkts.values():
            fills += mkt.get_fill_events()
        fills = list(sorted(fills, key=lambda f: f.time, reverse=False))
        self._update_positions(fills)
        return fills

    def _get_pending_tickers_events(self) -> PendingTickersEvent:
        _tickers: List[Ticker] = []  # NOTE: IBKR actually returns a set
        for mkt in self.mkts.values():
            _t: Optional[Ticker] = mkt.get_pending_ticker()
            if _t:
                _tickers.append(_t)
        return PendingTickersEvent(time=self.time, tickers=_tickers)

    def _get_pnl_events(self, ticker: Ticker) -> List[PnLSingleEvent]:
        """
        If there are change best, the method calculates a pnl and spits an event
        """
        pnl_events: List[PnLSingleEvent] = []
        position: Position = next(filter(lambda p: p.contract == ticker.contract, self.positions()))
        if position.position != 0:
            change_bests = filter(lambda tick: isinstance(tick, TickByTickBidAsk), ticker.tickByTicks)
            unique_bests = set(map(lambda x: (x.best.bid, x.best.ask), change_bests))
            for bid, ask in unique_bests:
                pnl = self._calc_unrealized_pnl(bid=bid, ask=ask, position=position)
                pnl_events.append(PnLSingleEvent(time=self.time, pnl=pnl))
        return pnl_events

    @staticmethod
    def _calc_unrealized_pnl(bid: float, ask: float, position: Position) -> PnLSingle:
        if position.position > 0:
            delta = bid - position.avg_cost
        else:
            delta = position.avg_cost - ask
        unrealized_pnl: float = delta * position.position
        if isinstance(position.contract, ibi.Future):
            unrealized_pnl *= int(position.contract.multiplier)
        return PnLSingle(conId=position.contract.conId, position=position.position, unrealizedPnL=unrealized_pnl)

    def _forward_event_to_strategy(self, event: Event):
        if isinstance(event, PendingTickersEvent):
            self.strat.on_pending_tickers_event(tickers=event.tickers)
        elif isinstance(event, OrderReceivedEvent) or isinstance(event, OrderCanceledEvent):
            self._bt_history_of_events.append(event)
            self.strat.on_new_order_event(trade=event.trade)
        elif isinstance(event, FillEvent):
            self._bt_history_of_events.append(event)
            self.strat.on_exec_details_event(trade=event.trade, fill=event.fill)
        elif isinstance(event, PnLSingleEvent):
            self.strat.on_pnl_single_event(pnl=event.pnl)
        else:
            raise ValueError(f"Got unexpected event: {event}")

    def run(self) -> List[Event]:
        self.strat.backtester = self
        while self.time <= self.end_time:
            logger.debug(f"Next timestamp: {self.time}")
            self._set_mkts_time(time=self.time)
            self._add_new_mkt_events_to_queue()
            self.strat.set_time(self.time)
            while not self._events.empty():
                e = self._events.get_nowait()
                self._forward_event_to_strategy(event=e)
            self.time += self.time_step

        logger.info("Hey jerk! We're done backtesting. You happy with the results?")
        return self._bt_history_of_events
