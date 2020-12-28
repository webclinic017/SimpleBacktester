import abc
import psycopg2
from dataclasses import dataclass
from collections import namedtuple
from typing import Optional
from src.resources.config import PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD

TableRef = namedtuple("TableRef", "schema table")


class Db(metaclass=abc.ABCMeta):
    def __init__(self, auto_open_conn: bool = True, db_connection=None):
        if db_connection is None and auto_open_conn is True:
            db_connection = self.open_conn()
        self.conn = db_connection

    @staticmethod
    def open_conn():
        """
        Initialize the database connection.
        """
        conn = psycopg2.connect(
            host=PGHOST,
            port=PGPORT,
            user=PGUSER,
            password=PGPASSWORD,
            database=PGDATABASE,
        )
        conn.autocommit = True
        return conn


@dataclass
class QueryNoneResult:
    query: Optional[str] = None
