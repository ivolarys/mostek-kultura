"""Google Calendar Events / "Simple Calendar" WordPress plugin (simcal), e.g.
umeleckakoloniejosefov.cz/kalendar-akci: only the current calendar month is server-rendered for SEO
(`li.simcal-event` inside `td.simcal-day`) — the month-switcher buttons call `wp-admin/admin-ajax.php`
via POST (`action=simcal_default_calendar_draw_grid`), which the shared `Http` client (GET-only)
can't do, so like hospital-kuks.cz / kultura-novapaka.cz this only sees a rolling ~2-4 week window.

A multi-day event's `<li>` repeats identically in every day cell it spans, so items are dedup'd here by
the Google Calendar `eid` pulled from the "Více podrobností" link. Full ISO datetimes with UTC offset
live in the `content` attribute of `span.simcal-event-start[-date|-time]` /
`span.simcal-event-end[-date|-time]`; an event is untimed/all-day when there is no `-end-time` span
(only `-end-date`, or no end span at all for a single all-day day). `location` is normally just the
event title again (Google Calendar has no separate venue field here). The description is free text, or
sometimes just a bare link to the event's own page on the site — used as the event `url` when present,
since the "Více podrobností" link otherwise only opens the Google Calendar entry.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime

from ..dates import local
from ..model import Event
from .base import Source, clean, soup

_EID = re.compile(r"[?&]eid=([^&]+)")



log = logging.getLogger(__name__)


class SimcalCalendarSource(Source):
    def fetch(self, http) -> list[Event]:
        return self.parse(http.get_text(self.cfg.url))

    def parse(self, html: str) -> list[Event]:
        doc = soup(html)
        out: list[Event] = []
        seen: set[str] = set()
        for li in doc.select("li.simcal-event"):
            try:
                ev = self._parse_item(li)
            except Exception as e:  # noqa: BLE001
                log.warning("%s: skipping malformed item: %s", self.name, e)
                continue
            if ev is None or ev.native_id in seen:
                continue
            seen.add(ev.native_id)
            out.append(ev)
        return out

    def _parse_item(self, li) -> Event | None:
        title_el = li.select_one("span.simcal-event-title")
        start_el = li.select_one("span.simcal-event-start[content]")
        if not title_el or not start_el:
            return None
        title = clean(title_el.get_text())
        if not title:
            return None
        start = local(datetime.fromisoformat(start_el["content"]))
        end_time = li.select_one("span.simcal-event-end-time[content]")
        end_date = li.select_one("span.simcal-event-end-date[content]")
        all_day = end_time is None
        end = None
        if end_time is not None:
            end = local(datetime.fromisoformat(end_time["content"]))
        elif end_date is not None:
            end = local(datetime.fromisoformat(end_date["content"]))
        more = li.select_one('a[href*="google.com/calendar"]')
        eid_m = _EID.search(more["href"]) if more and more.get("href") else None
        native_id = eid_m.group(1) if eid_m else f"{title}|{start.isoformat()}"
        desc_el = li.select_one(".simcal-event-description")
        description, url = "", self.cfg.page_url
        if desc_el:
            a = desc_el.find("a", href=True)
            text = clean(desc_el.get_text())
            if a and clean(a.get_text()) == text and "://" in a["href"] and self._is_own(a["href"]):
                url = a["href"]
            else:
                description = text[:500]
        return self.event(
            title=title, start=start, end=end, all_day=all_day, url=url,
            description=description, native_id=native_id,
        )

    def _is_own(self, href: str) -> bool:
        from urllib.parse import urlsplit
        return urlsplit(href).netloc == urlsplit(self.cfg.url).netloc
