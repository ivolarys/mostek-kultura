"""Klášter Hostinné (bespoke ERmedia CMS) homepage `Aktuality` feed: `#ArticleSection > div.item`
cards shared by the museum/library/gallery ("Muzeum"/"Knihovna"/"Galerie"). It's a plain publish-date
news list mixing recaps and previews, but the site itself flags already-happened items with
`span.archiveItem` (title "událost již proběhla") in the date header — the only reliable signal here —
so only items without that class are kept. No specific time is given, only a date, so events are
all-day.
"""

from __future__ import annotations

import logging
from urllib.parse import urljoin

from ..dates import parse_cz
from ..model import Event
from .base import Source, clean, soup

log = logging.getLogger(__name__)


class KlasterHostinneSource(Source):
    def fetch(self, http) -> list[Event]:
        return self.parse(http.get_text(self.cfg.url))

    def parse(self, html: str) -> list[Event]:
        doc = soup(html)
        out: list[Event] = []
        for item in doc.select("#ArticleSection > div.item"):
            try:
                ev = self._parse_item(item)
            except Exception as e:  # noqa: BLE001
                log.warning("%s: skipping malformed item: %s", self.name, e)
                continue
            if ev:
                out.append(ev)
        return out

    def _parse_item(self, item) -> Event | None:
        span = item.select_one("div.head span")
        h2a = item.select_one("div.content h2 a")
        if not span or not h2a or not h2a.get("href"):
            return None
        if "archiveItem" in (span.get("class") or []):
            return None
        lines = [clean(x) for x in span.get_text("\n").split("\n") if clean(x)]
        if len(lines) < 2:
            return None
        category, date_text = lines[0], lines[1]
        parsed = parse_cz(date_text)
        if not parsed:
            return None
        start, end, all_day = parsed
        url = urljoin(self.cfg.url, h2a["href"])
        content = item.select_one("div.content")
        desc = ""
        if content:
            for tag in content.find_all(["h2", "a"]):
                tag.extract()
            desc = clean(content.get_text(" "))
        img = item.select_one("div.photo img")
        return self.event(
            title=clean(h2a.get_text()), start=start, end=end, all_day=all_day, url=url,
            native_category=category, description=desc[:500],
            image=urljoin(self.cfg.url, img["src"]) if img and img.get("src") else None,
            native_id=url,
        )
