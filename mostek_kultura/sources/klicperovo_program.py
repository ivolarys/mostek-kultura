"""Klicperovo divadlo (Hradec Králové) – server-rendered monthly programme.

The public programme uses one URL per month (``/program/YYYY-MM``).  Each
``.program-day`` contains a real ISO date and its ``.program-card`` entries;
the same markup also contains hidden touring performances, which must not be
reported as Hradec Králové events.  The site exposes the current and upcoming
months directly, so this source asks only for the current month plus the two
following months (configurable with ``months``).
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime
from urllib.parse import urljoin

from ..dates import TZ, today
from .base import Source, clean, soup

log = logging.getLogger(__name__)

_TIME = re.compile(r"(?<!\d)(\d{1,2}):(\d{2})(?!\d)")
_VENUES = {
    "hlavni-scena": "Klicperovo divadlo, Dlouhá 99/9",
    # Studio Beseda is a separate Mýtská-street venue, not the main theatre building.
    "studio-beseda": "Studio Beseda, Mýtská 126",
    "foyer-hlavni-sceny": "Foyer hlavní scény, Dlouhá 99/9",
    "sal-soni-cervene-fhk": "Sál Soni Červené, Filharmonie Hradec Králové",
}
_NON_LOCAL_VENUES = {"ct-art"}
_TAG_CATEGORIES = {
    "koncert": "Koncert",
    "výstava": "Výstava",
    "vystava": "Výstava",
    "beseda": "Beseda",
    "workshop": "Workshop",
}


def _add_months(value: date, months: int) -> tuple[int, int]:
    number = value.year * 12 + value.month - 1 + months
    return divmod(number, 12)[0], divmod(number, 12)[1] + 1


def _category(tags: str, copy_text: str) -> str:
    """Keep the theatre's explicit genre tags ahead of the normal theatre default."""
    for tag in (clean(value).lower() for value in tags.split("||")):
        if tag in _TAG_CATEGORIES:
            return _TAG_CATEGORIES[tag]
    # The current card does not expose a genre tag, but names the guest orchestra explicitly.
    if "orchestr swing melody" in copy_text.lower():
        return "Koncert"
    return "Divadlo"


class KlicperovoProgramSource(Source):
    def month_urls(self, ref: date | None = None) -> list[str]:
        """Current published month and at most two following monthly programmes."""
        ref = ref or today()
        count = max(1, int(self.cfg.extra.get("months", 3)))
        root = self.cfg.url.rstrip("/")
        urls = [self.cfg.url]
        for offset in range(1, count):
            year, month = _add_months(ref, offset)
            urls.append(f"{root}/{year}-{month:02d}")
        return urls

    def fetch(self, http) -> list:
        events, seen = [], set()
        for url in self.month_urls():
            for event in self.parse(http.get_text(url), url):
                if event.native_id in seen:
                    continue
                seen.add(event.native_id)
                events.append(event)
        return events

    def parse(self, html: str, page_url: str | None = None) -> list:
        doc = soup(html)
        section = doc.select_one("section.program-section[data-programme]")
        if not section:
            raise ValueError("Klicperovo programme markup missing: program-section[data-programme]")
        out = []
        for day in section.select(".program-day[data-program-day]"):
            date_el = day.select_one(".program-day-head time[datetime]")
            if not date_el:
                continue
            try:
                performance_day = date.fromisoformat(date_el["datetime"])
            except ValueError:
                continue
            for card in day.select("article.program-card[data-program-item]"):
                event = self._parse_card(card, performance_day, page_url or self.cfg.url)
                if event:
                    out.append(event)
        return out

    def _parse_card(self, card, performance_day: date, page_url: str):
        venue_key = clean(card.get("data-venue")).lower()
        tags = clean(card.get("data-tags")).lower()
        # Tours are rendered into the monthly HTML but are hidden from the local programme.
        if card.get("data-tour") == "1" or venue_key == "zajezd":
            return None
        # The theatre's page also advertises its TV broadcasts; they have no local venue.
        if venue_key in _NON_LOCAL_VENUES:
            return None
        if "pro školy" in tags or "pro skoly" in tags:
            return None
        card_text = clean(card.get_text(" ")).lower()
        if "uzavřené představení" in card_text or "uzavrene predstaveni" in card_text:
            return None
        if "zrušené představení" in card_text or "zrusene predstaveni" in card_text:
            return None
        action_el = card.select_one(".program-action")
        actions = clean(action_el.get_text(" ")).lower() if action_el else ""
        if ("objednat pro škol" in actions or "poptat místa pro škol" in actions) and not card.select_one(".ticket-cta"):
            return None
        venue = _VENUES.get(venue_key)
        if not venue:
            log.warning("%s: unknown local Klicperovo venue %r", self.name, venue_key)
            return None
        link = card.select_one("a.program-title-link[href]")
        time_el = card.select_one(".program-time strong")
        if not link or not time_el:
            return None
        match = _TIME.search(clean(time_el.get_text()))
        if not match:
            return None
        start = datetime(
            performance_day.year, performance_day.month, performance_day.day,
            int(match.group(1)), int(match.group(2)), tzinfo=TZ,
        )
        end = None
        end_el = card.select_one(".program-time small")
        end_match = _TIME.search(clean(end_el.get_text())) if end_el else None
        if end_match:
            candidate = start.replace(hour=int(end_match.group(1)), minute=int(end_match.group(2)))
            if candidate > start:
                end = candidate
        image = card.select_one("a.program-image img[src]")
        copy = card.select_one(".program-copy")
        description = clean(copy.get_text(" ")) if copy else ""
        url = urljoin(page_url, link["href"])
        return self.event(
            title=clean(link.get_text()), start=start, end=end, all_day=False,
            url=url, venue=venue, place=self.cfg.place, place_raw=self.cfg.place,
            native_category=_category(tags, description),
            description=description[:500],
            image=urljoin(page_url, image["src"]) if image else None,
            native_id=f"{url}|{start.isoformat()}",
        )
