import os
import pathlib
import tempfile

PGHOST = "localhost"
PGPORT = os.environ.get("PGPORT") or "5432"
PGUSER = "gulo"
PGDATABASE = "gulo"
PGPASSWORD = os.environ.get("PGPASSWORD") or ""

TICKS_SCHEMA_NAME = "ticks"
BARS_SCHEMA_DICT = {"TRADES": "bars_trades", "BID_ASK": "bars_bidask"}

_TMP_DIR = tempfile.TemporaryDirectory()
BASE_DIR = pathlib.Path(_TMP_DIR.name)
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)
BACKTEST_DIR = BASE_DIR / "backtest_results"
BACKTEST_DIR.mkdir(exist_ok=True)

DELIMITER = ";"
