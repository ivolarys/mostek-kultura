"""Vismo6 (a newer Vismo/WEBHOUSE product, distinct from the classic `kalendar-akci.asp` engine used
by `vismo`) "Wecal" calendar widget, e.g. galerie.horice.org/kalendar-udalosti: the page itself only
carries an empty Mustache template (`ul.list[data-element-type-of-object-type-block-id]`,
`<meta data-id-object>` on `<head>`) that JS fills from a GET JSON endpoint —
`/api/services/app/Object/GetEventsByDay?From=...&To=...&ObjectId=...&ElementTypeOfObjectTypeBlockId=...`
— grouped by day. The `From`/`To` window is a fixed, wide static range rather than one computed from
"today" (build.py's `flag_time`/`in_scope` trims to the real horizon afterwards anyway) so the request
URL never changes from one run to the next, keeping offline fixtures matchable without relying on the
shared `Http` fixture fallback's day-aware normalization (which only recognizes dotted `D.M.YYYY`/plain
municipal-CMS date params, not this API's ISO datetimes).

Per event: `name`/`perex`, `fromTime`/`toTime` ("HH:MM" strings, absent for an all-day event),
`isAllDay`, `codeListItems` (event types), `v-viewUrlAbsolute`, `v-id` (stable, used as `native_id`;
kept across the day-groups a multi-day event repeats in). Only `isStartDay` occurrences are taken as
the event's start; `date` on each occurrence already carries the full ISO offset.
"""

from __future__ import annotations

import logging
from datetime import datetime
from urllib.parse import urljoin

from ..dates import local
from ..model import Event
from .base import Source, clean, soup

log = logging.getLogger(__name__)

# Static window: wide enough to cover any realistic horizon without depending on "today" (see
# module docstring for why this must not be date-derived).
_FROM = "2020-01-01T00:00:00"
_TO = "2035-12-31T23:59:59"


class Vismo6Source(Source):
    def fetch(self, http) -> list[Event]:
        shell = soup(http.get_text(self.cfg.url))
        meta = shell.select_one("meta[data-id-object]")
        block = shell.select_one("[data-element-type-of-object-type-block-id]")
        if not meta or not block:
            return []
        object_id = meta["data-id-object"]
        block_id = block["data-element-type-of-object-type-block-id"]
        api = urljoin(self.cfg.url, "/api/services/app/Object/GetEventsByDay")
        url = (f"{api}?From={_FROM}&To={_TO}"
               f"&ObjectId={object_id}&ElementTypeOfObjectTypeBlockId={block_id}")
        data = http.get_json(url)
        items = (data.get("result") or {}).get("items") or []
        out: list[Event] = []
        seen: set[str] = set()
        for day in items:
            for raw in day.get("events", []):
                try:
                    ev = self._parse_event(raw)
                except Exception as e:  # noqa: BLE001
                    log.warning("%s: skipping malformed item: %s", self.name, e)
                    continue
                if ev and ev.native_id not in seen:
                    seen.add(ev.native_id)
                    out.append(ev)
        return out

    def _parse_event(self, ev: dict) -> Event | None:
        if not ev.get("isStartDay", True):
            return None
        title = clean(ev.get("name"))
        date_s = ev.get("date")
        if not title or not date_s:
            return None
        base = datetime.fromisoformat(date_s)
        all_day = bool(ev.get("isAllDay")) or not ev.get("fromTime")
        if ev.get("fromTime"):
            h, m = (int(x) for x in ev["fromTime"].split(":"))
            start = local(base.replace(hour=h, minute=m, second=0, microsecond=0))
        else:
            start = local(base)
        end = None
        if ev.get("toTime"):
            h, m = (int(x) for x in ev["toTime"].split(":"))
            end = local(base.replace(hour=h, minute=m, second=0, microsecond=0))
        cats = [c.get("name") for c in (ev.get("codeListItems") or []) if c.get("name")]
        url = ev.get("v-viewUrlAbsolute") or self.cfg.page_url
        native_id = str(ev.get("v-id") or f"{title}|{date_s}")
        return self.event(
            title=title, start=start, end=end, all_day=all_day, url=url,
            native_category=", ".join(cats) if cats else None,
            description=clean(ev.get("perex") or "")[:500], native_id=native_id,
        )
