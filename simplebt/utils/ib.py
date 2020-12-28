from ib_insync import IB

def start_ib(client_id: int = 1, port: int = 4002, timeout: float = None) -> IB:
    ib = IB()
    if timeout:
        ib.RequestTimeout = timeout
    ib.connect(
        "127.0.0.1", port, clientId=client_id
    )  # TWS=7496, GTW=4001, # PAPER=7497
    return ib
