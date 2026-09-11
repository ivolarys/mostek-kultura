"""Public4u (as4u.cz) municipal CMS: mudk.cz, trutnov.cz.

Listing: `/redakce/index.php?lanG=cs&subakce=events&rok=YYYY&mesic=M`, items `.akce_celek_obal`.
Two templates exist: a card template (mudk: `.typ_akce`, `.nazev_akce`, `.datum_konani`, date only) and a
table template (trutnov: `table.kratky_popis_akce` with Místo/Datum/Typ). When the listing has no
table, the detail page is fetched (it always has the table).
"""

from __future__ import annotations

import logging
from datetime import date
from urllib.parse import urljoin

from ..dates import parse_cz, today
from ..model import Event
from .base import Source, clean, soup

log = logging.getLogger(__name__)


def _table(el) -> dict[str, str]:
    out = {}
    for tr in el.select("table.kratky_popis_akce tr"):
        th, td = tr.find("th"), tr.find("td")
        if th and td:
            out[clean(th.get_text()).rstrip(":").lower()] = clean(td.get_text())
    return out


class Public4uSource(Source):
    def month_urls(self, ref: date | None = None) -> list[str]:
        ref = ref or today()
        n = int(self.cfg.extra.get("months", 3))
        urls = []
        y, m = ref.year, ref.month
        for _ in range(n):
            urls.append(f"{self.cfg.url}&rok={y}&mesic={m}")
            m += 1
            if m > 12:
                m, y = 1, y + 1
        return urls

    def fetch(self, http) -> list[Event]:
        events: list[Event] = []
        seen: set[str] = set()
        for url in self.month_urls():
            for ev in self.parse_listing(http.get_text(url)):
                if ev.url in seen:
                    continue
                seen.add(ev.url)
                if ev.native_category is None or ev.all_day and not ev.venue:
                    self.enrich(ev, http)
                events.append(ev)
        return events

    def parse_listing(self, html: str) -> list[Event]:
        doc = soup(html)
        events: list[Event] = []
        for item in doc.select(".akce_celek_obal"):
            name = item.select_one(".nazev_akce")
            a = (name.find("a") if name and name.find("a") else None) or item.find("a", href=True)
            if not name or not a:
                continue
            url = urljoin(self.cfg.url, a["href"])
            title = clean(name.get_text())
            table = _table(item)
            date_text = table.get("datum konání")
            if not date_text:
                d = item.select_one(".datum_konani")
                date_text = clean(d.get_text()) if d else ""
            parsed = parse_cz(date_text)
            if not parsed:
                continue
            start, end, all_day = parsed
            typ = table.get("typ akce")
            if not typ:
                t = item.select_one(".typ_akce")
                typ = clean(t.get_text()) if t else None
            img = item.find("img")
            events.append(self.event(
                title=title, start=start, end=end, all_day=all_day, url=url,
                venue=table.get("místo konání") or None,
                native_category=typ or None,
                image=urljoin(self.cfg.url, img["src"]) if img and img.get("src") else None,
                native_id=url,
            ))
        return events

    def enrich(self, ev: Event, http) -> None:
        """Fetch the detail page for time, venue and description."""
        try:
            doc = soup(http.get_text(ev.url))
        except Exception as e:  # noqa: BLE001
            log.warning("%s: detail %s failed: %s", self.name, ev.url, e)
            return
        table = _table(doc)
        parsed = parse_cz(table.get("datum konání", ""))
        if parsed:
            ev.start, ev.end, ev.all_day = parsed
        ev.venue = table.get("místo konání") or ev.venue
        ev.native_category = table.get("typ akce") or ev.native_category
        desc = doc.select_one(".podrobny_popis_akce")
        if desc:
            ev.description = clean(desc.get_text(" "))[:500]
