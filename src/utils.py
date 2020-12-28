import datetime
import pandas as pd
from typing import Optional, Callable

def to_utc(t: datetime.datetime) -> datetime.datetime:
    if hasattr(t, "replace"):
        return t.replace(tzinfo=datetime.timezone.utc)
    else:
        raise ValueError(f"t={t} of type {type(t)} is not a valid argument")


def strptime(
    datestr: str, tzinfo: Optional[datetime.timezone] = datetime.timezone.utc
) -> datetime.datetime:
    return datetime.datetime.strptime(datestr, "%Y%m%d").replace(tzinfo=tzinfo)


def is_prev_row_diff(s: pd.Series):
    s_1 = s.shift(1).copy(deep=True)
    diff = s != s_1
    return diff


def last_valid_ix_row(x):
    """
    To apply with df.apply(first_valid_ix_row, axis=1)
    """
    if x.first_valid_index() is None:
        return None
    else:
        return x[x.first_valid_index()]


def sign(cv1: float, cv10: float) -> Callable[[float, float], bool]:
    """
    Infer the right function to compare the T-stat to its critical values given two of them, passed in descending order starting from the highest significance level (normally 1%).
    t represents the T-statistic, cv stays for critical value
    """
    if cv1 < cv10:
        return lambda t, cv: t <= cv
    elif cv1 > cv10:
        return lambda t, cv: t >= cv
    else:
        raise ValueError("a and b are equal")
