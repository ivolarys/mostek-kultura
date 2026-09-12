"""Dům kultury Koruna Hořice (bespoke CMS, `/UserFiles/...` uploads) `/program`: server-rendered cards
under `div.main`, one `div.body` per event — `h3.title a` (title + detail link), a date line marked by
`i.fa-calendar` ("D.M.", no year) and, when timed, a time line marked by `i.glyphicon-time` ("HH:MMh"),
a lead paragraph (`p.mb-10`) and a "Číst více,.." link. The poster `<img>` sits in the sibling column of
the enclosing `div.row`. Single page, no pagination — appears to just show a fixed rolling window of
upcoming shows.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from urllib.parse import urljoin

from ..dates import TZ, infer_year
from ..model import Event
from .base import Source, clean, soup

_DATE = re.compile(r"(\d{1,2})\.(\d{1,2})\.")
_TIME = re.compile(r"(\d{1,2}):(\d{2})")

_VENUE = "Dům kultury Koruna"



log = logging.getLogger(__name__)


class KorunaProgramSource(Source):
    def fetch(self, http) -> list[Event]:
        return self.parse(http.get_text(self.cfg.url))

    def parse(self, html: str) -> list[Event]:
        doc = soup(html)
        out: list[Event] = []
        for body in doc.select("div.main div.body"):
            try:
                ev = self._parse_item(body)
            except Exception as e:  # noqa: BLE001
                log.warning("%s: skipping malformed item: %s", self.name, e)
                continue
            if ev:
                out.append(ev)
        return out

    def _parse_item(self, body) -> Event | None:
        h3a = body.select_one("h3.title a")
        cal = body.select_one("i.fa-calendar")
        if not h3a or not h3a.get("href") or not cal:
            return None
        dm = _DATE.search(clean(cal.parent.get_text(" ")))
        if not dm:
            return None
        day, month = int(dm.group(1)), int(dm.group(2))
        year = infer_year(day, month)
        clock = body.select_one("i.glyphicon-time")
        tm = _TIME.search(clean(clock.parent.get_text(" "))) if clock else None
        if tm:
            start = datetime(year, month, day, int(tm.group(1)), int(tm.group(2)), tzinfo=TZ)
            all_day = False
        else:
            start, all_day = datetime(year, month, day, tzinfo=TZ), True
        url = urljoin(self.cfg.url, h3a["href"])
        p = body.select_one("p.mb-10")
        row = body.parent.parent if body.parent else None
        img = row.select_one("img") if row else None
        return self.event(
            title=clean(h3a.get_text()), start=start, all_day=all_day, url=url, venue=_VENUE,
            description=clean(p.get_text(" "))[:500] if p else "",
            image=urljoin(self.cfg.url, img["src"]) if img and img.get("src") else None,
            native_id=url,
        )
