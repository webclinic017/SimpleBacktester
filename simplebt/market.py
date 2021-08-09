import datetime
import random
from typing import List, Union, Optional, Tuple
import ib_insync as ibi
import pandas as pd
import trading_calendars as tc

from simplebt.events.market import MktOpenEvent, MktCloseEvent, FillEvent
from simplebt.historical_data.load.ticks import BidAskTicksLoader, TradesTicksLoader
from simplebt.orders import Order, LmtOrder, MktOrder, OrderAction
from simplebt.ticker import TickByTickBidAsk, TickByTickAllLast, Ticker
from simplebt.trade import StrategyTrade, Fill


class Market:
    def __init__(
        self,
        start_time: datetime.datetime,
        contract: ibi.Contract,
    ):
        self.time: datetime.datetime = start_time
        self.contract = contract

        # NOTE: beware this might not be accurate
        self.calendar: tc.TradingCalendar = tc.get_calendar(contract.exchange)
        self._is_mkt_open: bool = self.calendar.is_open_on_minute(pd.Timestamp(self.time))

        self._best: TickByTickBidAsk = TickByTickBidAsk(time=start_time, bid=-1, ask=-1, bid_size=0, ask_size=0)

        self._trades_loader = TradesTicksLoader(contract)
        self._bidask_loader = BidAskTicksLoader(contract)

        self._trades_with_pending_orders: List[StrategyTrade] = []

        # Events
        self._cal_event: Optional[Union[MktOpenEvent, MktCloseEvent]] = None
        self._mkt_trades: List[TickByTickAllLast] = []
        self._change_bests: List[TickByTickBidAsk] = []
        self._fill_events: List[FillEvent] = []

        self.set_time(time=self.time)  # This method may populate the collections above

    def get_book_best(self, pick_random_best: bool = False) -> TickByTickBidAsk:
        """
        :param pick_random_best: To use when the quote is used at a random time between the beginning and the end of
        a 1 sec interval. If new changeBest (bid ask) ticks are available, pick a random one.
        Otherwise return the last known BookL0: self._best
        """
        if pick_random_best and len(self._change_bests) > 0:
            best: TickByTickBidAsk = random.choice(self._change_bests)
        else:  # the BookL0 retrieved from the latest changeBest
            best = self._best
        return best

    def get_fill_events(self) -> List[FillEvent]:
        return self._fill_events

    def get_pending_ticker(self) -> Optional[Ticker]:
        ticks: List[Union[TickByTickBidAsk, TickByTickAllLast]] = []
        ticks += self._mkt_trades
        ticks += self._change_bests
        if ticks:
            return Ticker(
                contract=self.contract,
                tickByTicks=ticks,
            )

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

        self._mkt_trades = self._trades_loader.get_ticks_batch_by_time(time=time)
        self._change_bests = self._bidask_loader.get_ticks_batch_by_time(time=time)
        if len(self._change_bests) > 0:
            self._best = self._change_bests[-1]
        self._fill_events = self._process_pending_orders()  # Will just return an empty list if the mkt is closed

    def _update_cal_and_get_event(self, time: datetime.datetime) -> Optional[Union[MktOpenEvent, MktCloseEvent]]:
        is_mkt_open: bool = self.calendar.is_open_on_minute(pd.Timestamp(time))
        if is_mkt_open != self._is_mkt_open:
            # first, update the class state
            self._is_mkt_open = is_mkt_open
            # second, yield the appropriate event
            if is_mkt_open:
                return MktOpenEvent(time=time)
            else:
                return MktCloseEvent(time=time)
        return None

    def _process_pending_orders(self) -> List[FillEvent]:
        fill_events: List[FillEvent] = []
        if self._is_mkt_open:
            not_filled: List[StrategyTrade] = []
            for trade_with_pending_order in self._trades_with_pending_orders:
                trade, fill = self._process_order(trade_with_pending_order)
                if fill:
                    fill_events.append(FillEvent(time=self.time, trade=trade, fill=fill))
                # Using if instead of elif here
                # because even if there was a fill, the original order might not be completely filled yet
                if not trade.filled():
                    not_filled.append(trade_with_pending_order)  # treating everything as a Good Til Cancelled for the moment
            self._trades_with_pending_orders = not_filled
        return fill_events

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
        best: TickByTickBidAsk = self.get_book_best(pick_random_best=True)
        price: Optional[float] = None
        filled_lots: Optional[int] = None
        # pick the side according to the order type (Long vs Short)
        if order.action == OrderAction.BUY:
            # Don't have book depth. Only playing with best here
            price = best.ask
            filled_lots = min(order.lots, best.ask_size)
        elif order.action == OrderAction.SELL:
            price = best.bid
            filled_lots = min(order.lots, best.bid_size)
        else:
            raise ValueError("Unknown order Action")
        if price and filled_lots:
            return Fill(
                time=self.time,
                price=price,
                lots=filled_lots,
                order_action=order.action
            )

    def _exec_lmt_order(self, order: LmtOrder) -> Optional[Fill]:
        best: TickByTickBidAsk = self.get_book_best(pick_random_best=True)
        # pick the side according to the order type (Long vs Short)
        price: Optional[float] = None
        filled_lots: Optional[int] = None
        if order.action == OrderAction.BUY:
            if order.price >= best.ask:
                price = best.ask
                filled_lots = min(order.lots, best.ask_size)
        elif order.action == OrderAction.SELL:
            if order.price <= best.bid:
                price = best.bid
                filled_lots = min(order.lots, best.bid_size)
        else:
            raise ValueError("Unknown order Action")
        if price and filled_lots:
            return Fill(
                time=self.time,
                price=price,
                lots=filled_lots,
                order_action=order.action
            )
