"""Divadlo DRAK (Hradec Králové) – public programme embedded in one HTML page.

The public page has a month tab for each currently published month.  Touring
and schools-only programmes have separate URLs and are deliberately not read;
rows visibly marked ``Pro školy`` / ``Objednat pro školy`` are also excluded
from the public feed while sold-out public rows stay present.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from urllib.parse import urljoin

from ..dates import MONTHS, TZ, infer_year
from .base import Source, clean, soup

log = logging.getLogger(__name__)

_DATE = re.compile(r"(\d{1,2})\.(\d{1,2})\.")
_TIME = re.compile(r"(?<!\d)(\d{1,2})[.:](\d{2})(?!\d)")
_TAB_MONTHS = {
    **MONTHS,
    "leden": 1, "únor": 2, "unor": 2, "březen": 3, "brezen": 3, "duben": 4,
    "květen": 5, "kveten": 5, "červen": 6, "cerven": 6, "červenec": 7,
    "cervenec": 7, "srpen": 8, "říjen": 10, "rijen": 10, "listopad": 11,
    "prosinec": 12,
}


def _clock(value: tuple[str, str]) -> tuple[int, int] | None:
    hour, minute = int(value[0]), int(value[1])
    if hour >= 24 or minute >= 60:
        return None
    return hour, minute


class DrakProgramSource(Source):
    def fetch(self, http) -> list:
        return self.parse(http.get_text(self.cfg.url))

    def parse(self, html: str) -> list:
        doc = soup(html)
        programme = doc.select_one("section#program")
        if not programme:
            raise ValueError("DRAK programme markup missing: section#program")
        sections = [s for s in programme.select(".tabcontent[id]") if self._month(s.get("id"))]
        if not sections:
            raise ValueError("DRAK programme markup missing: monthly tabcontent sections")
        out = []
        for section in sections:
            month = self._month(section["id"])
            assert month is not None
            for row in section.select("table.events tr"):
                try:
                    event = self._parse_row(row, month)
                except Exception as exc:  # noqa: BLE001
                    log.warning("%s: skipping malformed programme row: %s", self.name, exc)
                    continue
                if event:
                    out.append(event)
        return out

    @staticmethod
    def _month(value: str | None) -> int | None:
        return _TAB_MONTHS.get(clean(value).lower())

    def _parse_row(self, row, month: int):
        date_el = row.select_one(".event-date .date")
        show = row.select_one(".event-show")
        if not date_el or not show:
            return None
        row_text = clean(row.get_text(" "))
        lowered = row_text.lower()
        if "pro školy" in lowered or "pro skoly" in lowered or "objednat pro školy" in lowered or "objednat pro skoly" in lowered:
            return None
        if "zájezd" in lowered or "zajezd" in lowered or "uzavřeno" in lowered or "uzavreno" in lowered:
            return None
        dm = _DATE.search(clean(date_el.get_text()))
        if not dm:
            return None
        day, parsed_month = int(dm.group(1)), int(dm.group(2))
        if parsed_month != month:
            log.warning("%s: date month %s differs from tab month %s", self.name, parsed_month, month)
            return None
        year = infer_year(day, month)
        title_link = show.select_one("a[href]")
        name_el = show.select_one(".event-name") or title_link
        title = clean(name_el.get_text()) if name_el else ""
        if not title:
            return None
        start_el = row.select_one(".event-start")
        times = _TIME.findall(clean(start_el.get_text())) if start_el else []
        if times:
            first = _clock(times[0])
            if not first:
                return None
            start = datetime(year, month, day, *first, tzinfo=TZ)
            all_day = False
            end = None
            if len(times) > 1:
                last = _clock(times[1])
                if not last:
                    return None
                end = start.replace(hour=last[0], minute=last[1])
                if end <= start:
                    end += timedelta(days=1)
        else:
            start = datetime(year, month, day, tzinfo=TZ)
            end, all_day = None, True
        venue_el = row.select_one(".event-venue .event-venue")
        venue_name = clean(venue_el.get_text()) if venue_el else ""
        venue = f"Divadlo DRAK – {venue_name}" if venue_name else None
        image = show.select_one("img[src]")
        url = urljoin(self.cfg.url, title_link["href"]) if title_link and title_link.get("href") else self.cfg.page_url
        tags_el = row.select_one(".event-tags")
        tags = clean(tags_el.get_text(" ")).lower() if tags_el else ""
        if "/vystava/" in url:
            category = "Výstava"
        elif "workshop" in tags or "dílna" in tags or "dilna" in tags:
            category = "Workshop"
        else:
            category = "Divadlo"
        return self.event(
            title=title, start=start, end=end, all_day=all_day, url=url, venue=venue or None,
            place=self.cfg.place, place_raw=self.cfg.place,
            native_category=category,
            image=urljoin(self.cfg.url, image["src"]) if image else None,
            native_id=f"{url}|{start.isoformat()}",
        )
