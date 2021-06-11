import datetime
import pathlib
import random
from typing import List, Union, Optional, Tuple
import ib_insync as ibi
import pandas as pd
import trading_calendars as tc

from simplebt.events.market import MktOpen, MktClose, MktTrade, ChangeBest
from simplebt.historical_data.load.ticks import BidAskTicksLoader, TradesTicksLoader
from simplebt.events.batches import ChangeBestBatch, MktTradeBatch, PendingTicker
from simplebt.book import BookL0
from simplebt.orders import Order, LmtOrder, MktOrder
# from simplebt.events.orders import OrderCanceled, OrderReceived
from simplebt.trade import StrategyTrade, Fill


class Market:
    def __init__(
        self,
        start_time: datetime.datetime,
        contract: ibi.Contract,
        data_dir: pathlib.Path,
        chunksize: int
    ):
        self.time: datetime.datetime = start_time
        self.contract = contract

        # NOTE: beware this might not be accurate
        self.calendar: tc.TradingCalendar = tc.get_calendar(contract.exchange)
        self._is_mkt_open: bool = self.calendar.is_open_on_minute(pd.Timestamp(self.time))

        self._trades_loader = TradesTicksLoader(contract, chunksize=chunksize, data_dir=data_dir)
        self._bidask_loader = BidAskTicksLoader(contract, chunksize=chunksize, data_dir=data_dir)

        self._trades_with_pending_orders: List[StrategyTrade] = []

        # The following collections/variables can be accessed by self.get_events()
        self._trades_ticks = MktTradeBatch(events=[], time=start_time)
        self._bidask_ticks = ChangeBestBatch(events=[], time=start_time)
        self._best: BookL0 = BookL0(time=start_time, bid=-1, ask=-1, bid_size=0, ask_size=0)
        self._cal_event: Optional[Union[MktOpen, MktClose]] = None
        self._fills: List[Tuple[StrategyTrade, Fill]] = []
        # this method may populate the collections above
        self.set_time(time=self.time)

    def get_book_best(self) -> BookL0:
        return self._best

    def _get_book_best(self) -> BookL0:
        """
        Private alternative to get_book_best.
        To use when the quote is used at a random time between the beginning and the end of
        a 1 sec interval.
        If new changeBest (bid ask) ticks are available, pick a random one. Otherwise return self._best
        """
        if self._bidask_ticks.events:
            best: BookL0 = random.choice(self._bidask_ticks.events).best
        else:  # otherwise default to the L0 retrieved from the latest changeBest
            best = self._best
        return best

    def add_order(self, order: Order) -> StrategyTrade:
        # validate order and add ID
        order.submitted()
        trade = StrategyTrade(order)
        self._trades_with_pending_orders.append(trade)
        return trade

    def cancel_order(self, order: Order) -> StrategyTrade:
        corresponding_trade = next(filter(lambda t: t.order == order, self._trades_with_pending_orders))
        self._trades_with_pending_orders.remove(corresponding_trade)
        order.cancelled()
        corresponding_trade.order = order
        return corresponding_trade

    def set_time(self, time: datetime.datetime):
        """
        Set_time() updates the collection/variables that caches mkt events.
        Until the method is called again, these events can be queried by external actors.
        """
        if self.time != time:
            self.time = time
        self._cal_event = self._update_cal_and_get_event(time=time)

        self._trades_ticks = self._trades_loader.get_ticks_batch_by_time(time=time)
        self._bidask_ticks = self._bidask_loader.get_ticks_batch_by_time(time=time)

        if self._bidask_ticks.events:
            self._best = self._bidask_ticks.events[-1].best

        if self._is_mkt_open:
            self._fills = self._process_pending_orders()
        else:
            self._fills = []

    def get_fills(self) -> List[Tuple[StrategyTrade, Fill]]:
        return self._fills

    def get_pending_ticker(self) -> Optional[PendingTicker]:
        events: List[Union[ChangeBest, MktTrade]] = []
        events += self._trades_ticks.events if self._trades_ticks.events else []
        events += self._bidask_ticks.events if self._bidask_ticks.events else []
        if events:
            ticker = PendingTicker(
                contract=self.contract,
                events=events,
                time=self._bidask_ticks.time or self._trades_ticks.time
            )
            return ticker

    # def get_events(self) -> List[Event]:
    #     events: List[Event] = []  # FIFO
    #     # Commented because no broker API will give you this
    #     # if self._cal_event:
    #     #     events.append(self._cal_event)
    #     if self._strat_trades:
    #         events += self._strat_trades  # append as single events

    #     # Here I build a PendingTicker object (instead of passing MktTradeBatch and ChangeBestBatch directly)
    #     # to simulate the behavior of the IBKR API
    #     ticks: List[Union[ChangeBest, MktTrade]] = []
    #     ticks += self._trades_ticks.events if self._trades_ticks.events else []
    #     ticks += self._bidask_ticks.events if self._bidask_ticks.events else []
    #     if ticks:
    #         ticker = PendingTicker(
    #             contract=self.contract,
    #             events=ticks,
    #             time=self._bidask_ticks.time or self._trades_ticks.time
    #         )
    #         events.append(ticker)
    #     # before it was:
    #     # if self._bidask_ticks.events:
    #     #     events.append(self._bidask_ticks)
    #     # if self._trades_ticks.events:
    #     #     events.append(self._trades_ticks)
    #     if not events:
    #         events.append(Nothing(time=self.time))
    #     return events
    
    def _update_cal_and_get_event(self, time: datetime.datetime) -> Optional[Union[MktOpen, MktClose]]:
        is_mkt_open: bool = self.calendar.is_open_on_minute(pd.Timestamp(time))
        if is_mkt_open != self._is_mkt_open:
            # first, update the class state
            self._is_mkt_open = is_mkt_open
            # second, yield the appropriate event
            if is_mkt_open:
                return MktOpen(time=time)
            else:
                return MktClose(time=time)
        return None

    def _process_pending_orders(self) -> List[Tuple[StrategyTrade, Fill]]:
        trades: List[Tuple[StrategyTrade, Fill]] = []
        if self._is_mkt_open:
            not_filled: List[StrategyTrade] = []
            for trade_with_pending_order in self._trades_with_pending_orders:
                trade, fill = self._process_order(trade_with_pending_order)
                if fill:
                    trades.append((trade, fill))
                if not trade.filled():
                    # NOTE: treating everything as a Good Til Cancelled for the moment
                    not_filled.append(trade_with_pending_order)
            self._trades_with_pending_orders = not_filled
        else:
            raise Exception(
                f"Can't call _process_pending_orders() when the mkt is not open. Bt time {self.time.timestamp()}"
            )
        return trades

    def _process_order(self, trade: StrategyTrade) -> Tuple[StrategyTrade, Optional[Fill]]:
        fill: Optional[Fill] = None
        if isinstance(trade.order, MktOrder):
            fill = self._exec_mkt_order(order=trade.order)
        elif isinstance(trade.order, LmtOrder):
            fill = self._exec_lmt_order(order=trade.order)

        if fill:
            trade.add_fill(fill)
        return trade, fill

    def _exec_mkt_order(self, order: MktOrder) -> Optional[Fill]:
        best: BookL0 = self._get_book_best()
        price: Optional[float] = None
        # pick the side according to the order type (Long vs Short)
        if order.lots > 0:
            # Don't have book depth, approximate
            if best.ask_size >= order.lots:
                price = best.ask
        else:
            if best.bid_size >= order.lots:
                price = best.bid
        if price:
            return Fill(
                time=self.time,
                price=price,
                lots=order.lots,
            )

    def _exec_lmt_order(self, order: LmtOrder) -> Optional[Fill]:
        best: BookL0 = self._get_book_best()
        # pick the side according to the order type (Long vs Short)
        price: Optional[float] = None
        if order.action == "BUY":
            if order.price >= best.ask and best.ask_size >= order.lots:
                price = best.ask
        else:
            if order.price <= best.bid and best.bid_size >= order.lots:
                price = best.bid
        if price:
            return Fill(
                time=self.time,
                price=price,
                lots=order.lots,
            )
