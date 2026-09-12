"""Náplavka Hradec Králové program cards at ``/program``.

Cards carry an explicit dated event URL, time, native category, title and poster.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from urllib.parse import urljoin

from ..dates import TZ
from ..model import Event
from .base import Source, clean, soup

_DATE_URL = re.compile(r"/udalost/(\d{4})-(\d{1,2})-(\d{1,2})(?:-|/)")
_TIME = re.compile(r"(?<!\d)(\d{1,2}):(\d{2})(?!\d)")
_VENUE = "Náplavka kulturní klub"
log = logging.getLogger(__name__)


class NaplavkaProgramSource(Source):
    def fetch(self, http) -> list[Event]:
        return self.parse(http.get_text(self.cfg.url))

    def parse(self, html: str) -> list[Event]:
        out: list[Event] = []
        cards = soup(html).select("a.program-item[href]")
        if not cards:
            raise ValueError("Náplavka programme markup missing: a.program-item[href]")
        for card in cards:
            try:
                event = self._parse_item(card)
            except Exception as exc:  # noqa: BLE001
                log.warning("%s: skipping malformed item: %s", self.name, exc)
                continue
            if event:
                out.append(event)
        return out

    def _parse_item(self, card) -> Event | None:
        url = card.get("href", "")
        match = _DATE_URL.search(url)
        title_el = card.select_one(".program-item__desc b")
        if not match or not title_el:
            return None
        year, month, day = (int(value) for value in match.groups())
        times = _TIME.findall(clean(card.select_one(".day-time").get_text(" ") if card.select_one(".day-time") else ""))
        start = datetime(year, month, day, *(int(x) for x in times[0]), tzinfo=TZ) if times else datetime(year, month, day, tzinfo=TZ)
        category_el = card.select_one(".event-type-label")
        image = card.select_one(".program-item__art img")
        return self.event(
            title=clean(title_el.get_text(" ")), start=start, all_day=not times,
            url=urljoin(self.cfg.url, url), place_raw=self.cfg.place, venue=_VENUE,
            native_category=clean(category_el.get_text(" ")) if category_el else None,
            image=urljoin(self.cfg.url, image.get("src")) if image and image.get("src") else None,
            native_id=url,
        )
