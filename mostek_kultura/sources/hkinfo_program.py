"""Hradec Králové ``hkinfo.cz`` monthly programme cards.

The parser deliberately reads only explicit dates in each monthly page.  Source
configuration narrows the broad city calendar with ``include_title`` or
``include_venue`` regular expressions.
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime
from urllib.parse import urljoin, urlsplit, urlunsplit

from ..dates import MONTHS, TZ, today
from ..model import Event
from .base import Source, clean, soup

_TIME = re.compile(r"(?<!\d)(\d{1,2}):(\d{2})(?!\d)")
_DAY = re.compile(r"\d{1,2}")
_MONTH = {
    **{name.lower(): number for name, number in MONTHS.items()},
    "leden": 1, "únor": 2, "unor": 2, "březen": 3, "brezen": 3,
    "duben": 4, "květen": 5, "kveten": 5, "červen": 6, "cerven": 6,
    "červenec": 7, "cervenec": 7, "srpen": 8, "říjen": 10, "rijen": 10,
    "listopad": 11, "prosinec": 12,
}
_NATIVE_BY_TYPE = {18: "Trhy a jarmarky", 19: "Festival"}
log = logging.getLogger(__name__)


def _month_shift(value: date, offset: int) -> tuple[int, int]:
    index = value.year * 12 + value.month - 1 + offset
    return index // 12, index % 12 + 1


class HkinfoProgramSource(Source):
    def fetch(self, http) -> list[Event]:
        events: list[Event] = []
        seen: set[tuple[str, date]] = set()
        for offset in range(3):
            year, month = _month_shift(today(), offset)
            url = self._month_url(year, month)
            page = http.get_text(url)
            for event in self.parse(page, year=year, month=month, page_url=url):
                key = (event.native_id or event.title, event.start.date())
                if key in seen:
                    continue
                seen.add(key)
                events.append(event)
        return events

    def _month_url(self, year: int, month: int) -> str:
        parts = urlsplit(self.cfg.url)
        return urlunsplit((parts.scheme, parts.netloc, "/cs/kalendar-akci.html", f"mesic={month}&rok={year}", ""))

    def parse(self, html: str, *, year: int, month: int, page_url: str | None = None) -> list[Event]:
        document = soup(html)
        cards = document.select(".kalendarBanner")
        if not cards:
            raise ValueError("HKinfo programme markup missing: .kalendarBanner")
        out: list[Event] = []
        title_re = self.cfg.extra.get("include_title")
        venue_re = self.cfg.extra.get("include_venue")
        for card in cards:
            try:
                event = self._parse_item(card, year, month, page_url or self.cfg.page_url)
            except Exception as exc:  # noqa: BLE001
                log.warning("%s: skipping malformed item: %s", self.name, exc)
                continue
            if not event or (title_re and not re.search(title_re, event.title, re.IGNORECASE)) or (venue_re and not re.search(venue_re, event.venue or "", re.IGNORECASE)):
                continue
            out.append(event)
        return out

    def _parse_item(self, card, year: int, month: int, page_url: str) -> Event | None:
        title_el = card.select_one(".programAH")
        day_el = card.select_one(".velikostCab")
        month_el = card.select_one(".velikostC1a")
        if not title_el or not day_el or not month_el:
            return None
        title = clean(title_el.get_text(" "))
        month_parts = [_MONTH.get(part.strip()) for part in clean(month_el.get_text(" ")).lower().split("-")]
        if not month_parts or any(value is None for value in month_parts):
            return None
        month_number = month_parts[0]
        end_month_number = month_parts[-1]
        days = [int(value) for value in _DAY.findall(clean(day_el.get_text(" ")))]
        if not title or not days:
            return None
        start_year = year
        end_year = year
        if end_month_number < month_number:
            if month <= end_month_number:
                start_year -= 1
            else:
                end_year += 1
        try:
            start_date = date(start_year, month_number, days[0])
            if len(days) > 1 and end_month_number == month_number and days[-1] < days[0]:
                return None
            end_date = date(end_year, end_month_number, days[-1]) if len(days) > 1 else None
        except ValueError:
            return None
        times = _TIME.findall(clean(card.select_one(".programDate").get_text(" ") if card.select_one(".programDate") else ""))
        start = datetime(start_date.year, start_date.month, start_date.day, *(int(x) for x in times[0]), tzinfo=TZ) if times else datetime.combine(start_date, datetime.min.time(), TZ)
        end = None
        if end_date:
            if times and len(times) > 1:
                end = datetime(end_date.year, end_date.month, end_date.day, *(int(x) for x in times[1]), tzinfo=TZ)
            else:
                end = datetime.combine(end_date, datetime.max.time().replace(microsecond=0), TZ)
        elif times and len(times) > 1:
            end = datetime(start_date.year, start_date.month, start_date.day, *(int(x) for x in times[1]), tzinfo=TZ)
        venue = None
        for heading in card.select("h3.H2banner1K1"):
            text = clean(heading.get_text(" "))
            if text.lower().startswith("místo:"):
                venue = clean(text.split(":", 1)[1]) or None
                break
        target = card.select_one(".panel-heading[data-target]")
        target_id = target.get("data-target") if target else None
        native_id = f"{target_id or title}|{start_date.isoformat()}"
        event_url = urljoin(page_url, f"#{target_id.lstrip('#')}") if target_id else page_url
        body = card.select_one(".panel-body")
        image = body.select_one("img[src]") if body else None
        native_category = self.cfg.extra.get("native_category") or _NATIVE_BY_TYPE.get(int(card.get("data-typ", "-1")))
        if not native_category:
            lowered = title.casefold()
            if "hiki joki" in lowered:
                native_category = "Festival"
            elif "quiet music" in lowered:
                native_category = "Koncert"
        return self.event(
            title=title, start=start, end=end, all_day=not times, url=event_url,
            place_raw=self.cfg.place, venue=venue, native_category=native_category,
            description=clean(body.get_text(" "))[:500] if body else "",
            image=urljoin(page_url, image.get("src")) if image and image.get("src") else None,
            native_id=native_id,
        )
