"""Parsing of Czech date/time strings and timezone helpers."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Prague")

_DATE = re.compile(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})?")
_TIME = re.compile(r"(?<!\d)(\d{1,2})[:.](\d{2})(?!\d)")
_ISO = re.compile(r"(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})")

MONTHS = {
    "ledna": 1, "února": 2, "unora": 2, "března": 3, "brezna": 3, "dubna": 4, "května": 5,
    "kvetna": 5, "června": 6, "cervna": 6, "července": 7, "cervence": 7, "srpna": 8, "září": 9,
    "zari": 9, "října": 10, "rijna": 10, "listopadu": 11, "prosince": 12,
}
_DATE_WORDS = re.compile(r"(\d{1,2})\.\s*([a-zěščřžýáíéúůň]+)\s*(\d{4})?", re.IGNORECASE)


def now() -> datetime:
    return datetime.now(TZ)


def today() -> date:
    return now().date()


def local(dt: datetime) -> datetime:
    """Make datetime timezone-aware in Europe/Prague (assume local if naive)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=TZ)
    return dt.astimezone(TZ)


def infer_year(day: int, month: int, ref: date | None = None) -> int:
    """Pick the year so that the date is not older than ~30 days before `ref`."""
    ref = ref or today()
    try:
        candidate = date(ref.year, month, day)
    except ValueError:
        return ref.year
    if candidate < ref - timedelta(days=30):
        return ref.year + 1
    return ref.year


def parse_iso_compact(text: str) -> datetime | None:
    """Parse '20260912T130000' (Galileo data-date-start)."""
    m = _ISO.search(text or "")
    if not m:
        return None
    y, mo, d, h, mi, s = (int(x) for x in m.groups())
    return datetime(y, mo, d, h, mi, s, tzinfo=TZ)


def parse_cz(text: str, ref: date | None = None) -> tuple[datetime, datetime | None, bool] | None:
    """Parse a Czech date/time expression into (start, end, all_day).

    Handles: '12. 9. 2026 13:00', '12.9.2026', '11.9.2026 od 17:00 hodin',
    '12.9.2026 až 13.9.2026', '12.9.2026 od 10:00 do 17:00 hodin',
    '17. 09. 2026 20:00', 'ne 13. 09. 15:30' (no year), '11.9.' + '20:00h',
    'sobota: 12. září 2026'.
    """
    if not text:
        return None
    text = text.strip()
    dates: list[tuple[int, int, int]] = []
    for m in _DATE.finditer(text):
        d, mo, y = int(m.group(1)), int(m.group(2)), m.group(3)
        year = int(y) if y else infer_year(d, mo, ref)
        dates.append((d, mo, year))
    if not dates:
        for m in _DATE_WORDS.finditer(text):
            mo = MONTHS.get(m.group(2).lower())
            if not mo:
                continue
            d, y = int(m.group(1)), m.group(3)
            year = int(y) if y else infer_year(d, mo, ref)
            dates.append((d, mo, year))
    if not dates:
        return None
    # times: strip the date portions first so "12.9." isn't read as a time
    stripped = _DATE.sub(" ", text)
    times = [(int(h), int(mi)) for h, mi in _TIME.findall(stripped) if int(h) < 24 and int(mi) < 60]

    d, mo, y = dates[0]
    try:
        start_date = date(y, mo, d)
    except ValueError:
        return None
    end_date = None
    if len(dates) > 1:
        d2, mo2, y2 = dates[-1]
        try:
            end_date = date(y2, mo2, d2)
        except ValueError:
            end_date = None

    if times:
        start = datetime(start_date.year, start_date.month, start_date.day, *times[0], tzinfo=TZ)
        end = None
        if len(times) > 1:
            ed = end_date or start_date
            end = datetime(ed.year, ed.month, ed.day, *times[1], tzinfo=TZ)
            if end <= start and end_date is None:
                end += timedelta(days=1)
        elif end_date:
            end = datetime(end_date.year, end_date.month, end_date.day, 23, 59, tzinfo=TZ)
        return start, end, False
    start = datetime(start_date.year, start_date.month, start_date.day, tzinfo=TZ)
    end = datetime(end_date.year, end_date.month, end_date.day, 23, 59, tzinfo=TZ) if end_date else None
    return start, end, True
