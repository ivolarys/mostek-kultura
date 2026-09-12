"""Bělohradská sýpka (Webnode) `/program/`: each event is a pair of sibling `div.b.b-text` blocks
inside `div.mt-i-c.cf.mt-border.line-color` — the first holds date/time (`h3`, Czech text; `parse_cz`
handles both a normal "pátek 11. 9. 2026 18:00" and the open-ended "od čtvrtka 9. 7. 2026" prefix used
for standing offers like the café or an ongoing exhibition), venue (`p`) and a "více informací" link;
the second holds the title (`h3`) and free-text description (sibling `div`/`p` tags). Some detail links
are reused across dates for a recurring slot (e.g. the weekly pub quiz), so `native_id` combines the
link with the start time rather than using the link alone.
"""

from __future__ import annotations

import logging
from urllib.parse import urljoin

from ..dates import parse_cz
from ..model import Event
from .base import Source, clean, soup

log = logging.getLogger(__name__)


class WebnodeProgramSource(Source):
    def fetch(self, http) -> list[Event]:
        return self.parse(http.get_text(self.cfg.url))

    def parse(self, html: str) -> list[Event]:
        doc = soup(html)
        out: list[Event] = []
        for block in doc.select("div.mt-i-c.cf.mt-border.line-color"):
            try:
                ev = self._parse_item(block)
            except Exception as e:  # noqa: BLE001
                log.warning("%s: skipping malformed item: %s", self.name, e)
                continue
            if ev:
                out.append(ev)
        return out

    def _parse_item(self, block) -> Event | None:
        parts = block.select(":scope > div.b.b-text")
        if len(parts) < 2:
            return None
        date_c = parts[0].select_one("div.b-c")
        title_c = parts[1].select_one("div.b-c")
        if not date_c or not title_c:
            return None
        date_h3, title_h3 = date_c.find("h3"), title_c.find("h3")
        if not date_h3 or not title_h3:
            return None
        parsed = parse_cz(clean(date_h3.get_text()))
        if not parsed:
            return None
        start, end, all_day = parsed
        venue_p = date_c.find("p", recursive=False)
        venue = clean(venue_p.get_text()) or None if venue_p else None
        a = date_c.find("a", href=True)
        url = urljoin(self.cfg.url, a["href"]) if a else self.cfg.page_url
        title = clean(title_h3.get_text())
        desc = " ".join(clean(c.get_text(" ")) for c in title_c.find_all(["div", "p"], recursive=False))
        return self.event(
            title=title, start=start, end=end, all_day=all_day, url=url, venue=venue,
            description=desc[:500], native_id=f"{url}|{start.isoformat()}",
        )
