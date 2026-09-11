"""Antee CMS calendar RSS (e.g. lazne-belohrad.cz/kalendar-akci?action=atom).

Non-standard elements: <dueDate>17. 09. 2026 20:00</dueDate>, <endDate>, <category>Koncert, Pořadatel - X</category>.
"""

from __future__ import annotations

from datetime import timedelta

from bs4 import BeautifulSoup

from ..dates import parse_cz
from ..model import Event
from .base import Source, clean


class AnteeRssSource(Source):
    def fetch(self, http) -> list[Event]:
        return self.parse(http.get_text(self.cfg.url))

    def parse(self, xml: str) -> list[Event]:
        doc = BeautifulSoup(xml, "xml")
        events: list[Event] = []
        for item in doc.find_all("item"):
            title = clean(item.title.get_text() if item.title else "")
            due = item.find("dueDate")
            if not title or not due:
                continue
            parsed = parse_cz(clean(due.get_text()))
            if not parsed:
                continue
            start, end, all_day = parsed
            end_el = item.find("endDate")
            if end_el:
                pe = parse_cz(clean(end_el.get_text()))
                if pe:
                    end = pe[0]
            if end and end <= start:
                end = None
            cats = []
            organizer = None
            cat_el = item.find("category")
            for part in (clean(cat_el.get_text()) if cat_el else "").split(","):
                part = part.strip()
                if part.lower().startswith("pořadatel"):
                    organizer = part.split("-", 1)[-1].strip()
                elif part:
                    cats.append(part)
            link = clean(item.link.get_text() if item.link else "")
            guid = clean(item.guid.get_text() if item.guid else "") or link
            url = guid.split("?")[0] if guid else link
            enc = item.find("enclosure")
            desc = clean(item.description.get_text() if item.description else "")
            events.append(self.event(
                title=title, start=start, end=end, all_day=all_day, url=url,
                native_category=", ".join(cats) if cats else None,
                venue=organizer,
                description=desc[:500],
                image=enc.get("url") if enc else None,
                native_id=guid,
            ))
        # multi-day defaults: exhibitions with end >= 2 days get flagged later in normalize
        for e in events:
            if e.end and e.end - e.start > timedelta(days=60):
                e.end = None
        return events
