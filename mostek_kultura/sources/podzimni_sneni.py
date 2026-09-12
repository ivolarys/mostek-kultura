"""Podzimní snění festival homepage parser.

The homepage publishes the current festival date in an image alt attribute;
there is no programme listing to import, so the source yields one festival
event for the advertised date range.
"""

from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urljoin

from ..dates import MONTHS, TZ
from ..model import Event
from .base import Source, clean, soup

_DATE_RE = re.compile(
    r"(?P<start>\d{1,2})\.\s*"
    r"(?:[\u2013\u2014-]\s*(?P<end>\d{1,2})\.\s*)?"
    r"(?P<month>[A-Za-zÁČĎÉĚÍŇÓŘŠŤÚŮÝŽáčďéěíňóřšťúůýž]+)\s+"
    r"(?P<year>\d{4})"
)

_VENUE = "Tábor Jana Ámose Komenského, Běleč nad Orlicí"


class PodzimniSneniSource(Source):
    def fetch(self, http) -> list[Event]:
        return self.parse(http.get_text(self.cfg.url))

    def parse(self, html: str) -> list[Event]:
        doc = soup(html)
        date_image = doc.select_one("img.hero-date-image[alt]")
        if not date_image:
            raise ValueError("Podzimní snění date image missing: img.hero-date-image[alt]")
        date_text = clean(date_image.get("alt"))
        match = _DATE_RE.fullmatch(date_text)
        if not match:
            raise ValueError(f"Podzimní snění date malformed: {date_text!r}")

        day_start = int(match.group("start"))
        day_end = int(match.group("end") or day_start)
        month = MONTHS.get(match.group("month").lower())
        year = int(match.group("year"))
        if month is None:
            raise ValueError(f"Podzimní snění month unknown: {match.group('month')!r}")
        try:
            start = datetime(year, month, day_start, tzinfo=TZ)
            end = datetime(year, month, day_end, 23, 59, 59, tzinfo=TZ)
        except ValueError as exc:
            raise ValueError(f"Podzimní snění date invalid: {date_text!r}") from exc
        if end < start:
            raise ValueError(f"Podzimní snění date range reversed: {date_text!r}")

        # Keep the edition in the title even if the page template omits it.
        title = f"Podzimní snění {year}"
        description_tag = doc.select_one('meta[property="og:description"]')
        description = clean(description_tag.get("content")) if description_tag else ""
        hero = doc.select_one("img.hero-image[src]")
        image = urljoin(self.cfg.url, hero["src"]) if hero else None
        return [self.event(
            title=title,
            start=start,
            end=end,
            all_day=True,
            url=self.cfg.page_url,
            place_raw=self.cfg.place,
            venue=_VENUE,
            native_category="festival",
            description=description[:500],
            image=image,
            native_id=f"podzimni-sneni-{year}",
        )]
