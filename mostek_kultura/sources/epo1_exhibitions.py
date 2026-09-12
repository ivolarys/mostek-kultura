"""Current exhibitions from the EPO1 Webflow ``.show-card`` listing."""

from __future__ import annotations

import logging
import re
from urllib.parse import urljoin, urlsplit, urlunsplit

from ..dates import parse_cz
from ..model import Event
from .base import Source, clean, soup

log = logging.getLogger(__name__)
_DATE = re.compile(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})?")


class Epo1ExhibitionsSource(Source):
    """Parse only current ``show-card`` cards, leaving archive/search data alone."""

    def fetch(self, http) -> list[Event]:
        return self.parse(http.get_text(self.cfg.url))

    def parse(self, html: str) -> list[Event]:
        out: list[Event] = []
        for card in soup(html).select(".show-card"):
            try:
                event = self._parse_card(card)
            except (TypeError, ValueError) as exc:
                log.warning("%s: skipping malformed exhibition: %s", self.name, exc)
                continue
            if event:
                out.append(event)
        return out

    def _parse_card(self, card) -> Event | None:
        title_el = card.select_one("h3")
        if not title_el:
            return None
        title = clean(title_el.get_text(" "))
        if not title:
            return None
        artist_el = card.select_one(".show-card_artist")
        artist = clean(artist_el.get_text(" ")) if artist_el else ""
        if artist:
            title = f"{title} — {artist}"

        meta = card.select_one(".show-card_meta")
        meta_spans = meta.select("span") if meta else []
        hall = clean(meta_spans[0].get_text(" ")) if meta_spans else ""
        date_text = clean(meta_spans[1].get_text(" ")) if len(meta_spans) > 1 else clean(meta.get_text(" ")) if meta else ""
        parsed = self._parse_range(date_text)
        if not parsed:
            return None
        start, end, all_day = parsed

        href = clean(card.get("href"))
        if not href:
            return None
        url = urljoin(self.cfg.page_url, href)
        # Webflow's staging host is used by a few old links in the published cards.
        # The corresponding public pages are on the canonical host.
        parts = urlsplit(url)
        if parts.netloc == "epo1.webflow.io":
            url = urlunsplit((parts.scheme, "www.epo1.cz", parts.path, parts.query, parts.fragment))
        desc_el = card.select_one(".show-card_desc, .desc")
        desc = clean(desc_el.get_text(" ")) if desc_el else ""
        if hall:
            desc = f"{hall}. {desc}" if desc else hall
        return self.event(
            title=title, start=start, end=end, all_day=all_day, url=url,
            venue="EPO1, Trutnov", native_category="Výstava", description=desc[:500],
            native_id=url,
        )

    @staticmethod
    def _parse_range(text: str):
        """Parse a card's date range through the shared Czech date helper."""
        dates = list(_DATE.finditer(text))
        if len(dates) < 2:
            return None
        first, second = dates[0], dates[1]
        y1 = int(first.group(3)) if first.group(3) else None
        y2 = int(second.group(3)) if second.group(3) else None
        if y1 is None:
            y1 = y2
            if y1 is None:
                return None
            # A yearless cross-year range such as 22. 12. — 4. 1. 2027 starts in 2026.
            if (int(first.group(2)), int(first.group(1))) > (int(second.group(2)), int(second.group(1))):
                y1 -= 1
        if y2 is None:
            y2 = y1
            if (int(first.group(2)), int(first.group(1))) > (int(second.group(2)), int(second.group(1))):
                y2 += 1
        normalized = f"{first.group(1)}. {first.group(2)}. {y1} — {second.group(1)}. {second.group(2)}. {y2}"
        parsed = parse_cz(normalized)
        if not parsed or parsed[1] is None or parsed[1] < parsed[0]:
            return None
        return parsed
