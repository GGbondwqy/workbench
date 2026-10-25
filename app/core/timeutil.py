# -*- coding: utf-8 -*-
"""时间工具：全项目日期统一走本地时区 ISO 格式（YYYY-MM-DD / YYYY-MM-DD HH:MM）。"""
from datetime import date, datetime, timedelta

DATE_FMT = "%Y-%m-%d"
DATETIME_FMT = "%Y-%m-%d %H:%M"


def today() -> str:
    return date.today().strftime(DATE_FMT)


def now() -> str:
    return datetime.now().strftime(DATETIME_FMT)


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def week_start(d: date | None = None) -> date:
    """本周一。"""
    d = d or date.today()
    return d - timedelta(days=d.weekday())


def date_range(start: str, end: str):
    """闭区间迭代 [start, end] 的 ISO 日期串。"""
    cur = datetime.strptime(start, DATE_FMT).date()
    stop = datetime.strptime(end, DATE_FMT).date()
    while cur <= stop:
        yield cur.strftime(DATE_FMT)
        cur += timedelta(days=1)
