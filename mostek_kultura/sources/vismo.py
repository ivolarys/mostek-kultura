"""Vismo (WEBHOUSE) municipal CMS calendar: mujicin.cz, munovapaka.cz.

Listing at `kalendar-akci.asp?hledani=1&kdy=-1&datum_od=D.M.YYYY&datum_do=D.M.YYYY&pocet=100&submit=Vyhledat`
(no `id_org` needed, it is resolved server-side from the domain) returns "Jednodenní akce" and
"Vícedenní akce" sections as `<li>` items inside `#kalendarAkci .dok ul.ui`: title in `strong a` (an
`<img>` may sit inside the same `<a>`), date/time/venue in `.n5-akce-datum`
("17.9.2026 18:00, Klenotnice muzea", ranges as "D.M.YYYY H:MM - D.M.YYYY H:MM, venue"; `parse_cz`
handles both), free text in `.n5-akce-popis`, category in `.n5-akce-typ a`. The listing already has
time and venue, so no detail fetch is needed. A date-range query naturally excludes the "Dlouhodobé
akce" (undated permanent exhibits) section, which only appears on the unfiltered default page.
Long result sets are paginated (`.strvpred a.aktivni` -> next page); `pocet=100` avoids this in
practice but pagination is still followed defensively.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from urllib.parse import urljoin

from ..dates import parse_cz, today
from ..model import Event
from .base import Source, clean, soup

log = logging.getLogger(__name__)

_MAX_PAGES = 10


class VismoSource(Source):
    def fetch(self, http) -> list[Event]:
        days = int(self.cfg.extra.get("days", 60))
        start, end = today(), today() + timedelta(days=days)
        url = (
            f"{self.cfg.url}?hledani=1&kdy=-1&datum_od={start:%d.%m.%Y}"
            f"&datum_do={end:%d.%m.%Y}&pocet=100&submit=Vyhledat"
        )
        events: list[Event] = []
        seen: set[str] = set()
        for _ in range(_MAX_PAGES):
            try:
                doc = soup(http.get_text(url))
            except Exception as e:  # noqa: BLE001
                log.warning("%s: %s failed: %s", self.name, url, e)
                break
            for ev in self.parse_page(doc):
                if ev.native_id in seen:
                    continue
                seen.add(ev.native_id)
                events.append(ev)
            nxt = doc.select_one(".strvpred a.aktivni")
            if not nxt or not nxt.get("href"):
                break
            url = urljoin(self.cfg.url, nxt["href"])
        return events

    def parse_page(self, doc) -> list[Event]:
        out: list[Event] = []
        for li in doc.select("#kalendarAkci .dok ul.ui > li"):
            try:
                ev = self._parse_item(li)
            except Exception as e:  # noqa: BLE001
                log.warning("%s: skipping malformed item: %s", self.name, e)
                continue
            if ev:
                out.append(ev)
        return out

    def _parse_item(self, li) -> Event | None:
        a = li.select_one("strong a") or li.find("a", href=True)
        date_el = li.select_one(".n5-akce-datum")
        if not a or not date_el:
            return None
        title = clean(a.get_text())
        date_text = clean(date_el.get_text())
        parsed = parse_cz(date_text)
        if not title or not parsed:
            return None
        start, end, all_day = parsed
        venue = date_text.split(",", 1)[1].strip() if "," in date_text else None
        desc_el = li.select_one(".n5-akce-popis")
        cat_el = li.select_one(".n5-akce-typ a")
        img = a.find("img")
        url = urljoin(self.cfg.url, a["href"])
        return self.event(
            title=title, start=start, end=end, all_day=all_day, url=url,
            venue=venue or None,
            native_category=clean(cat_el.get_text()) if cat_el else None,
            description=clean(desc_el.get_text(" "))[:500] if desc_el else "",
            image=urljoin(self.cfg.url, img["src"]) if img and img.get("src") else None,
            native_id=url,
        )
