# TODO: update
import numpy as np
from ib_insync import IB, Future, Order, Ticker, Trade
from typing import List, Tuple, Union


class FindSales:
    def __init__(self):
        self.sales_tick_type: int = 4

    @staticmethod
    def ticks_exist(ticker: Ticker) -> bool:
        return ticker.ticks is not None

    def build_array(self, ticker: Ticker) -> np.array:
        ticks = None
        if self.ticks_exist(ticker):
            ticks = np.array(
                [
                    (t.price, t.size)
                    for t in ticker.ticks
                    if t.tickType == self.sales_tick_type
                ]
            )
        return ticks

    def return_prices_and_sizes(self, ticker: Ticker) -> Tuple[np.array, np.array]:
        prices, sizes = np.empty(0), np.empty(0)
        ticks = self.build_array(ticker)
        if len(ticks) > 0:
            prices = ticks[:, 0]
            sizes = ticks[:, 1]
        return prices, sizes


class NextSignal:
    def __init__(self, size_trigger: float):
        self.size_trigger = size_trigger

    def signal(self, bid: float, ask: float, prices: np.array, sizes: np.array) -> int:
        signal = 0
        mask = np.where(sizes > self.size_trigger)
        if len(mask) > 0:
            prices = prices[mask]
            # set 1 where the transaction happened >= ask and -1 where happened close to the bid. 0 elsewhere
            prices = np.where(prices >= ask, 1, np.where(prices <= bid, -1, 0))
            # multiply the directional signal by the size and sum to offset transactions yielding contrasting indicators
            signal = np.sum(prices * sizes[mask])
            # if the final result is > than the min size trigger, yield the signal, stay flat otherwise
            # signal / abs(signal) is used to bring back the signal to the usual +/-1 size
            if abs(signal) >= self.size_trigger:
                signal = int(signal / abs(signal))
        return signal


class IbTrader:
    def __init__(self, ib: IB, es: Future, mes: Future):
        self.ib = ib
        self.contract = es
        self.es = es
        self.mes = mes

        self.lots = 1
        self.trade: Union[Trade, None] = None
        self.sl_order: Union[Trade, None] = None
        self.tp_order: Union[Trade, None] = None
        self.ib_actions = {1: "BUY", -1: "SELL"}

    def order(self, ticker, signal):
        """
        Create orders from signal. Could become a @staticmethod without the assert and ib_actions but
        with self you can have the tp/sl params instantiated with the class
        """
        action = self.ib_actions[signal]
        if action == "BUY":
            reverse = "SELL"
            lmt = ticker.ask
            cancel_f = (
                lambda order, ticker: True
                if order.order.lmtPrice < ticker.ask - 0.25  # Small buffer
                else False
            )
            take_profit = lmt + self.tp
        elif action == "SELL":
            reverse = "BUY"
            lmt = ticker.bid
            cancel_f = (
                lambda order, ticker: True
                if order.order.lmtPrice > ticker.bid + 0.25  # Small buffer
                else False
            )
            take_profit = lmt - self.tp
        order = Order(
            action=action,
            orderType="LMT",
            totalQuantity=self.lots,
            lmtPrice=lmt,
            outsideRth=True,
        )
        stop_loss_order = Order(
            action=reverse,
            orderType="TRAIL",
            totalQuantity=self.lots,
            # TrailStopPRice causes troubles
            auxPrice=self.sl,
            outsideRth=True,
        )
        take_profit_order = Order(
            action=reverse,
            orderType="LMT",
            totalQuantity=self.lots,
            lmtPrice=take_profit,
            outsideRth=True,
        )
        return order, stop_loss_order, take_profit_order, cancel_f

    def emergency_exit(self, asset, signal):
        """
        Blocking
        """
        if self.tp_order.order:
            self.ib.cancelOrder(self.tp_order.order)
        if self.sl_order.order:
            self.ib.cancelOrder(self.sl_order.order)
        action = self.ib_actions[signal]
        emergency_exit = self.ib.placeOrder(
            asset,
            Order(
                action=action, orderType="MKT", totalQuantity=self.lots, outsideRth=True
            ),
        )
        # blocking
        while not emergency_exit.isDone():
            self.ib.waitOnUpdate()
        self.trade = None
        self.sl_order = None
        self.tp_order = None

    @staticmethod
    def healthcheck_trades(trades: Union[Trade, List[Trade]]) -> bool:
        if isinstance(trades, Trade):
            trades = [trades]
        for trade in trades:
            if trade.orderStatus.status == "Cancelled":
                return False
        return True

    def cancel_order(self, order):
        cancel = self.ib.cancelOrder(order)
        while not cancel.isDone():
            self.ib.waitOnUpdate()
        self.trade = None
        self.sl_order = None
        self.tp_order = None

    def adverse_signal(self, signal: int) -> bool:
        assertion: bool = False
        if signal != 0 and self.trade is not None:
            assertion = self.ib_actions[signal] != self.trade.order.action
        return assertion

    def run(self, ib):
        # subscribe to real time mkt data
        ticker_es = self.ib.reqMktData(
            self.es, genericTickList="233"
        )  # https://interactivebrokers.github.io/tws-api/tick_types.html
        # ticker_mes = self.ib.reqMktData(self.mes)
        while 1:
            ib.waitOnUpdate()

            prices, sizes = FindSales().return_prices_and_sizes(ticker_es)
            # evaluate the transactions (if any) and eventually output a signal (or None)
            signal: int = 0
            if np.sum(np.isnan(prices)) == 0:
                signal = NextSignal(size_trigger=100).signal(
                    ticker_es.bid, ticker_es.ask, prices, sizes
                )

            if not self.trade and signal != 0:  # you can start a new open_trade
                order, stop_loss_order, take_profit_order, cancel_f = self.order(
                    ticker_es, signal
                )
                self.trade = self.ib.placeOrder(self.es, order)
                # note, stop_loss and take_profit won't be opened until the open_trade.isDone
                # this won't happen until the next loop iteration at least
                # but I should be able to check if the order is good immediately
                if not self.healthcheck_trades(self.trade):
                    self.trade = None
                # logger.debug("---------------TRADE--------------------------")
                # logger.debug(f"{ticker_es.bid} / {ticker_es.ask}")
                # logger.debug(f"{prices} / {sizes}")
                # logger.debug(f"{self.open_trade.order}")
                # logger.debug("----------------------------------------------")

            elif self.trade:  # gotta handle the open open_trade
                adverse_signal = self.adverse_signal(signal)
                order_slipped = cancel_f(self.trade, ticker_es)
                # first of all check that the last signal agrees with your position
                if not self.trade.isDone():
                    if order_slipped or adverse_signal:
                        self.cancel_order(self.trade.order)  # blocking
                        # logger.debug(f"Cancel F: {order_slipped}")
                        # logger.debug(f"Adverse Signal: {adverse_signal}")
                        # logger.debug(f"{ticker_es.bid} / {ticker_es.ask}")
                        # logger.debug("Order canceled")
                        # logger.debug("----------------------------------------------")

                # if we get a adverse signal we have to close immediately
                elif (
                    adverse_signal
                ):  # note that is used when the open_trade isn't done as well
                    self.emergency_exit(self.es, signal)  # blocking
                    # logger.debug(f"{ticker_es.bid} / {ticker_es.ask}")
                    # logger.debug("Adverse signal. Exit open_trade")
                    # logger.debug("----------------------------------------------")

                # otherwise, if the open_trade went through and all is fine, you can place the two auxiliary orders
                elif not self.sl_order:
                    self.sl_order = self.ib.placeOrder(self.es, stop_loss_order)
                    self.tp_order = self.ib.placeOrder(self.es, take_profit_order)
                    # logger.debug("Order filled, opened stop_loss and take_profit")
                    # logger.debug(f"{self.open_trade.orderStatus}")
                    # logger.debug(f"{self.sl_order.order}")
                    # logger.debug(f"{self.tp_order.order}")
                    # logger.debug("----------------------------------------------")

                elif not self.healthcheck_trades([self.sl_order, self.tp_order]):
                    self.emergency_exit(self.es, stop_loss_order.action)
                    # logger.debug("Take profit or Stop loss failed: Emergency exit.")
                    # logger.debug("----------------------------------------------")

                elif self.sl_order.isDone():
                    # logger.debug(f"{ticker_es.bid} / {ticker_es.ask}")
                    # logger.debug("Hit stop loss")
                    # logger.debug(f"{self.sl_order}")
                    # logger.debug("----------------------------------------------")
                    self.cancel_order(self.tp_order.order)

                elif self.tp_order.isDone():
                    # logger.debug(f"{ticker_es.bid} / {ticker_es.ask}")
                    # logger.debug("Hit take profit")
                    # logger.debug(f"{self.tp_order}")
                    # logger.debug("----------------------------------------------")
                    self.cancel_order(self.sl_order.order)


if __name__ == "__main__":
    import logging
    import sys

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler(sys.stdout))
    logger.addHandler(logging.FileHandler("trades.log"))

    # ib = IB()
    # ib.connect("127.0.0.1", 4002, clientId=1)  # TWS=7496, PAPER=7497, GTW=4001
    # ib.reqMarketDataType(1)

    # ES = ib.reqContractDetails(Future(symbol="ES", exchange="GLOBEX"))[0].contract
    # MES = ib.reqContractDetails(Future(symbol="MES", exchange="GLOBEX"))[0].contract

    # ds = IbTrader(ib=ib, es=ES, mes=MES)
    # ds.run()
