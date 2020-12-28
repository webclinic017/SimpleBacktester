import os
import pathlib

PGHOST = "localhost"
PGPORT = os.environ.get("PGPORT") or "5432"
PGUSER = os.environ.get("PGUSER") or "gulo"
PGDATABASE = "gulo"
PGPASSWORD = os.environ.get("PGPASSWORD") or ""

TICKS_SCHEMA_NAME = "ticks"
BARS_SCHEMA_DICT = {"TRADES": "bars_trades", "BID_ASK": "bars_bidask"}

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)
BACKTEST_DIR = BASE_DIR / "backtest_results"
BACKTEST_DIR.mkdir(exist_ok=True)

DELIMITER = ";"
