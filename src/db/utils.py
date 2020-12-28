import pandas as pd
from typing import List


def read_tables_from_info_schema(
    conn, condition: str = "", format_date: List[str] = None
):
    tables = pd.read_sql_query(
        f"SELECT * FROM information_schema.tables {condition}", conn
    )
    out = {}
    for _, t in tables.iterrows():
        df = pd.read_sql_query(
            f"SELECT * FROM {t['table_schema']}.{t['table_name']}", conn
        )
        if format_date:
            for c in format_date:
                if c in df.columns:
                    df[c] = pd.to_datetime(df[c], utc=True)
        out[t["table_name"]] = df
    return out
