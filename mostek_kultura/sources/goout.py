"""GoOut public entities API.

Geo filters on /schedules are ignored by the API, so we search venues by town name
(`/venues?query=`), keep those inside `bbox`, then fetch `/schedules?venueIds[]=`.
"""

from __future__ import annotations

import logging
from datetime import datetime
from urllib.parse import quote

from ..dates import local
from ..model import Event
from .base import Source

log = logging.getLogger(__name__)


class GoOutSource(Source):
    def fetch(self, http) -> list[Event]:
        base = self.cfg.url.rstrip("/")
        bbox = self.cfg.extra.get("bbox")
        venues: dict[int, dict] = {}
        for q in self.cfg.extra.get("venue_queries", []):
            data = http.get_json(f"{base}/venues?languages[]=cs&limit=48&query={quote(q)}")
            for v in data.get("venues", []):
                a = v.get("attributes", {})
                lat, lon = a.get("latitude"), a.get("longitude")
                if bbox and not (lat and lon and bbox[0] <= lat <= bbox[2] and bbox[1] <= lon <= bbox[3]):
                    continue
                venues[v["id"]] = v
        if not venues:
            return []
        events: list[Event] = []
        ids = list(venues)
        for i in range(0, len(ids), 20):
            chunk = "&".join(f"venueIds[]={vid}" for vid in ids[i:i + 20])
            url = f"{base}/schedules?languages[]=cs&limit=48&source=goout&include=events,venues&{chunk}"
            scroll = None
            while True:
                data = http.get_json(url + (f"&scrollId={scroll}" if scroll else ""))
                events.extend(self.parse(data, venues))
                scroll = (data.get("meta") or {}).get("nextScrollId")
                if not scroll or not data.get("schedules"):
                    break
        return events

    def parse(self, data: dict, venues: dict[int, dict] | None = None) -> list[Event]:
        inc = data.get("included", {})
        ev_map = {e["id"]: e for e in inc.get("events", [])}
        ven_map = {v["id"]: v for v in inc.get("venues", [])}
        if venues:
            ven_map = {**venues, **ven_map}
        out: list[Event] = []
        for s in data.get("schedules", []):
            a = s.get("attributes", {})
            if a.get("isPermanent") or a.get("state") not in (None, "approved"):
                continue
            rel = s.get("relationships", {})
            ev = ev_map.get((rel.get("event") or {}).get("id"))
            ven = ven_map.get((rel.get("venue") or {}).get("id"))
            if not ev:
                continue
            loc = (ev.get("locales") or {}).get("cs") or {}
            title = loc.get("name") or ""
            if not title:
                continue
            start = local(datetime.fromisoformat(a["startAt"]))
            end = local(datetime.fromisoformat(a["endAt"])) if a.get("endAt") else None
            ea = ev.get("attributes", {})
            cats = [ea.get("mainCategory")] + list(ea.get("categories") or [])
            vloc = ((ven or {}).get("locales") or {}).get("cs") or {}
            vatt = (ven or {}).get("attributes") or {}
            out.append(self.event(
                title=title, start=start, end=end, all_day=not a.get("hasTime", True),
                url=(s.get("locales", {}).get("cs") or {}).get("siteUrl") or s.get("url", ""),
                venue=vloc.get("name"),
                place_raw=vatt.get("city"),
                native_category=", ".join(c for c in cats if c) or None,
                description=(loc.get("description") or "")[:500],
                native_id=f"schedule:{s['id']}",
            ))
        return out
