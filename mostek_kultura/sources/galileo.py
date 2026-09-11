"""Galileo CMS (mostek.cz, jaromer-josefov.cz): event list with full details inline."""

from __future__ import annotations

from urllib.parse import urljoin

from ..dates import parse_cz, parse_iso_compact
from ..model import Event
from .base import Source, clean, soup


class GalileoSource(Source):
    def fetch(self, http) -> list[Event]:
        html = http.get_text(self.cfg.url)
        return self.parse(html)

    def parse(self, html: str) -> list[Event]:
        doc = soup(html)
        events: list[Event] = []
        for item in doc.select(".event-action__item"):
            link = item.select_one("a.event-action__link")
            heading = item.select_one(".event-action__heading")
            if not link or not heading:
                continue
            url = urljoin(self.cfg.url, link.get("href", ""))
            title = clean(heading.get_text())
            start_el = item.select_one(".event-action__date-start")
            parsed = None
            if start_el and start_el.get("data-date-start"):
                st = parse_iso_compact(start_el["data-date-start"])
                en = parse_iso_compact(start_el.get("data-date-end") or "")
                if st:
                    parsed = (st, en, st.hour == 0 and st.minute == 0)
            if parsed is None:
                body = item.select_one(".event-action__row-body--date-start")
                text = clean(body.get_text()) if body else ""
                if not text:
                    day = item.select_one(".event-action__date-day")
                    year = item.select_one(".event-action__date-year")
                    text = f"{clean(day.get_text()) if day else ''} {clean(year.get_text()) if year else ''}"
                parsed = parse_cz(text)
            if parsed is None:
                continue
            start, end, all_day = parsed
            venue_el = item.select_one(".event-action__row-body--venue")
            cats = [clean(x.get_text()) for x in item.select(".event-action__label")]
            img = item.select_one("img.event-action__img")
            events.append(self.event(
                title=title, start=start, end=end, all_day=all_day, url=url,
                venue=clean(venue_el.get_text()) if venue_el else None,
                native_category=", ".join(cats) if cats else None,
                image=urljoin(self.cfg.url, img["src"]) if img and img.get("src") else None,
                native_id=item.get("id"),
            ))
        return events
