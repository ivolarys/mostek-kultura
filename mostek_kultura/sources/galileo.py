"""Galileo CMS municipal sites.

Two list templates: the newer one (mostek.cz: `.event-action__item` with `data-date-start`) and the
older one (bilatremesna.cz, dolnibrusnice.cz, kuks.cz: `div.event.event-message` with `h3.event-name`,
`.action_date` "11. 9. 2026 začátek od 17:00" / "11. 9. 2026 - 13. 9. 2026", `.venues`, `p.event-perex`).
"""

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
        for item in doc.select("div.event.event-message"):
            a = item.select_one("a.event-link")
            name = item.select_one(".event-name")
            date_el = item.select_one(".action_date")
            if not a or not name or not date_el:
                continue
            parsed = parse_cz(clean(date_el.get_text()))
            if not parsed:
                continue
            start, end, all_day = parsed
            venue = item.select_one(".venues")
            if venue:
                for junk in venue.select(".sr-only, i"):
                    junk.extract()
            perex = item.select_one(".event-perex")
            img = item.select_one("img")
            events.append(self.event(
                title=clean(name.get_text()), start=start, end=end, all_day=all_day,
                url=urljoin(self.cfg.url, a["href"]),
                venue=clean(venue.get_text()) or None if venue else None,
                description=clean(perex.get_text())[:500] if perex else "",
                image=urljoin(self.cfg.url, img["src"]) if img and img.get("src") else None,
                native_id=item.get("id"),
            ))
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
