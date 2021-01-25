"""
CLI script to download historical ticks. Works for both active and expired future contracts.
"""

if __name__ == "__main__":
    
    from simplebt.historical_data.utils.ticks import download_and_store_hist_ticks
    from simplebt.utils.ib import start_ib
    import datetime
    from ib_insync import Contract, ContractDetails, Future
    from typing import List
    import argparse
    
    parser = argparse.ArgumentParser(description="Download historical ticks")
    parser.add_argument("--client-id", type=int, help="Client ID to use when connecting to the gateway")
    parser.add_argument("--port", type=int, default=4002, help="Port the gateway is listening on (4001, 4002)")
    parser.add_argument("--timeout", type=int)
    parser.add_argument("--symbol", type=str, help="Example ES")
    parser.add_argument("--exchange", type=str, default="", help="Example GLOBEX. Otherwise will get data from all exchanges")
    parser.add_argument("--expiries", type=str, action="extend", nargs="+", help="Expiries to download. The `extend` action stores them in a list")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--bid-ask", action="store_true")
    group.add_argument("--trades", action="store_true")

    args = parser.parse_args()

    CLIENT_ID: int = args.client_id
    PORT: int = args.port
    TIMEOUT: int = args.timeout
    if args.bid_ask is True:
        TICK_TYPE = "BID_ASK"
    elif args.trades is True:
        TICK_TYPE = "TRADES"
    else:
        raise ValueError("Specify one of --bid-ask or --trades to select the tick type to download")
    SYMBOL: str = args.symbol
    EXCHANGE: str = args.exchange
    EXPIRIES: List[str] = args.expiries

    ib = start_ib(client_id=CLIENT_ID, port=PORT, timeout=TIMEOUT)
    contracts: List[ContractDetails] = ib.reqContractDetails(
        Future(symbol=SYMBOL, exchange=EXCHANGE, includeExpired=True)
    )
    ib.disconnect()
    ib.sleep(1)

    cs: List[Contract] = [c.contract for c in contracts if c.contract is not None]
    if EXPIRIES is not None:
        cs = list(filter(lambda c: c.lastTradeDateOrContractMonth in EXPIRIES, cs))
    cs = sorted(
        cs, 
        key=lambda c: c.lastTradeDateOrContractMonth,
        reverse=False
    )
    print(",".join([c.lastTradeDateOrContractMonth for c in cs]))
    for n, c in enumerate(cs):
        print(f"Round {n}: {SYMBOL} {c.lastTradeDateOrContractMonth} {TICK_TYPE}")
        if n == 0:
            START_DATETIME = datetime.datetime.strptime(c.lastTradeDateOrContractMonth, "%Y%m%d") - datetime.timedelta(days=90)
        else:
            START_DATETIME = datetime.datetime.strptime(cs[n - 1].lastTradeDateOrContractMonth, "%Y%m%d")
        START_DATETIME = START_DATETIME.replace(tzinfo=datetime.timezone.utc)
        download_and_store_hist_ticks(
            client_id=CLIENT_ID,
            port=PORT,
            timeout=TIMEOUT,
            contract=c,
            start_datetime=START_DATETIME,
            tick_type=TICK_TYPE,
        )
