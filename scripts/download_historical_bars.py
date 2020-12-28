"""
CLI script to download historical bars. Works for both active and expired future contracts.
"""

if __name__ == "__main__":

    from ib_insync import Contract, ContractDetails, Future
    from gulo.historical_data.utils.bars import download_and_store_hist_bars
    from gulo.utils.utils import start_ib
    from typing import List, Optional
    import argparse

    parser = argparse.ArgumentParser(description="Download historical bars")
    parser.add_argument("--client-id", type=int, help="Client ID to use when connecting to the gateway")
    parser.add_argument("--port", type=int, default=4002, help="Port the gateway is listening on (4001, 4002)")
    parser.add_argument("--timeout", type=int)
    parser.add_argument("--bar-size", type=str, help="5 secs, 1 secs, 1 hour...")
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
    BAR_SIZE: str = args.bar_size
    if args.bid_ask is True:
        BAR_TYPE = "BID_ASK"
    elif args.trades is True:
        BAR_TYPE = "TRADES"
    SYMBOL: str = args.symbol
    EXCHANGE: str = args.exchange
    EXPIRIES: List[str] = args.expiries
    
    ib = start_ib(client_id=CLIENT_ID, port=PORT, timeout=TIMEOUT + 1)
    
    contracts: List[ContractDetails] = ib.reqContractDetails(
        Future(
            symbol=SYMBOL,
            exchange=EXCHANGE,
            includeExpired=True,
        )
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
 
    for c in cs:
        download_and_store_hist_bars(
            client_id=CLIENT_ID,
            port=PORT,
            timeout=TIMEOUT,
            contract=c,
            bar_size=BAR_SIZE,
            bar_type=BAR_TYPE, 
        )
