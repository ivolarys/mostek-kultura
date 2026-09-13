"""Společenský dům Jilm Jilemnice – current, server-rendered programme.

The public programme is a chronological five-page listing (12 cards per page); its archive has a
separate URL and is deliberately never followed.  Cards contain the full local date/time, venue,
category, detail URL, image and excerpt.  The linked Google Calendar ICS is not used because it
lacks those fields and retains obsolete lessons.
"""

from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urljoin

from ..dates import TZ
from ..model import Event
from .base import Source, clean, soup

_EVENT_ID = re.compile(r"\bentry-event-(\d+)\b")
_MONTHS = {
    "leden": 1, "únor": 2, "březen": 3, "duben": 4, "květen": 5, "červen": 6,
    "červenec": 7, "srpen": 8, "září": 9, "říjen": 10, "listopad": 11, "prosinec": 12,
}
_CATEGORY_MAP = {
    "koncert": "koncert",
    "přednáška": "prednaska",
    "výstava": "vystava",
    "taneční": "komunita",
    "divadelní představení": "divadlo",
    "dětský pořad": "deti",
    "workshop": "prednaska",
    "hudebně-literární pořad": "koncert",
    "talk show": "prednaska",
}


class SdJilmSource(Source):
    def fetch(self, http) -> list[Event]:
        url = self.cfg.url
        out: list[Event] = []
        seen_urls: set[str] = set()
        max_pages = int(self.cfg.extra.get("pages", 5))

        for _ in range(max_pages):
            if url in seen_urls:
                break
            seen_urls.add(url)
            doc = soup(http.get_text(url))
            out.extend(self._parse_page(doc))
            nxt = doc.select_one("#pagination-partial-wrapper a[rel='next'][href]")
            if not nxt:
                break
            url = urljoin(url, nxt["href"])
        return out

    def _parse_page(self, doc) -> list[Event]:
        out: list[Event] = []
        for card in doc.select("#items-partial-wrapper .entry-event"):
            link = card.select_one("a[href]")
            date_el = card.select_one(".meta-date.published")
            title_el = card.select_one(".event-details > .entry-title")
            if not link or not date_el or not title_el:
                continue
            start, all_day = self._parse_date(date_el)
            if not start:
                continue
            title = clean(link.get("title")) or clean(title_el.contents[0] if title_el.contents else "")
            if not title:
                continue
            image = card.select_one(".featured-image img[src]")
            venue = card.select_one(".featured-image .place")
            category = card.select_one(".featured-image .flash > .text")
            excerpt = card.select_one(".entry-excerpt")
            event_id = _EVENT_ID.search(" ".join(card.get("class", [])))
            # An event card ID names a programme entry, while one entry may recur.  Add its start
            # instant so multiple showtimes of the same programme remain separate and stable.
            native_id = f"{event_id.group(1) if event_id else link['href']}|{start.isoformat()}"
            native_category = clean(category.get_text(" ")) if category else None
            out.append(self.event(
                title=title,
                start=start,
                all_day=all_day,
                url=urljoin(self.cfg.url, link["href"]),
                venue=clean(venue.get_text(" ")) if venue else None,
                category=_CATEGORY_MAP.get((native_category or "").lower()),
                native_category=native_category,
                description=clean(excerpt.get_text(" ")) if excerpt else "",
                image=urljoin(self.cfg.url, image["src"]) if image else None,
                native_id=native_id,
            ))
        return out

    @staticmethod
    def _parse_date(date_el) -> tuple[datetime | None, bool]:
        """Read the listing's Czech nominative month parts without depending on prose parsing."""
        day = clean(date_el.select_one(".day").get_text()) if date_el.select_one(".day") else ""
        month = clean(date_el.select_one(".month").get_text()).lower() if date_el.select_one(".month") else ""
        year = clean(date_el.select_one(".year").get_text()) if date_el.select_one(".year") else ""
        hour = clean(date_el.select_one(".hour").get_text()) if date_el.select_one(".hour") else ""
        try:
            d, m, y = int(day), _MONTHS[month], int(year)
            if hour:
                h, minute = (int(part) for part in hour.split(":", maxsplit=1))
                return datetime(y, m, d, h, minute, tzinfo=TZ), False
            return datetime(y, m, d, tzinfo=TZ), True
        except (KeyError, TypeError, ValueError):
            return None, True
