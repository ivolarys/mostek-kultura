"""Galerie EPO1 Trutnov (epo1.cz/doprovodny-program): a Webflow site whose accompanying-programme
calendar is not a CMS collection list but a small hand/CMS-generated JS array embedded directly in the
page (`<script id="epo1-calendar-engine">var EVENTS=[...]`) — plain JSON once the `var EVENTS=` prefix
and trailing `;` are stripped. Fields: `date` (ISO `YYYY-MM-DD`), `time` ("18:00" or a "16:00–18:00"
range, en dash), `place`, `type` (native category), `desc`, `slug` (stable id) and `url` — either an
absolute ticketing link (goout.net) or, for purely informational entries, a site-relative path plus an
`img` thumbnail.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from urllib.parse import urljoin

from ..dates import TZ
from ..model import Event
from .base import Source, clean

_EVENTS_RE = re.compile(r"var\s+EVENTS\s*=\s*(\[.*?\]);", re.DOTALL)
_TIME = re.compile(r"(\d{1,2}):(\d{2})")



log = logging.getLogger(__name__)


class Epo1CalendarSource(Source):
    def fetch(self, http) -> list[Event]:
        html = http.get_text(self.cfg.url)
        m = _EVENTS_RE.search(html)
        if not m:
            return []
        try:
            items = json.loads(m.group(1))
        except json.JSONDecodeError:
            return []
        out: list[Event] = []
        for it in items:
            try:
                ev = self._parse_item(it)
            except Exception as e:  # noqa: BLE001
                log.warning("%s: skipping malformed item: %s", self.name, e)
                continue
            if ev:
                out.append(ev)
        return out

    def _parse_item(self, it: dict) -> Event | None:
        name = clean(it.get("name"))
        date_s = it.get("date")
        if not name or not date_s:
            return None
        y, mo, d = (int(x) for x in date_s.split("-"))
        times = _TIME.findall(it.get("time") or "")
        if times:
            start = datetime(y, mo, d, int(times[0][0]), int(times[0][1]), tzinfo=TZ)
            end = datetime(y, mo, d, int(times[1][0]), int(times[1][1]), tzinfo=TZ) if len(times) > 1 else None
            all_day = False
        else:
            start, end, all_day = datetime(y, mo, d, tzinfo=TZ), None, True
        href = it.get("url") or ""
        url = urljoin(self.cfg.url, href) if href.startswith("/") else (href or self.cfg.page_url)
        return self.event(
            title=name, start=start, end=end, all_day=all_day, url=url,
            venue=it.get("place"), native_category=it.get("type"),
            description=clean(it.get("desc"))[:500], image=it.get("img"),
            native_id=it.get("slug") or f"{name}|{date_s}",
        )
