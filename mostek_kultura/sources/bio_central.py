"""Bio Central Hradec Králové programme from its server-rendered Event JSON-LD blocks."""

from __future__ import annotations

import html
import json
import logging
from datetime import datetime
from urllib.parse import urljoin

from ..dates import local
from ..model import Event
from .base import Source, clean, soup

log = logging.getLogger(__name__)


class BioCentralSource(Source):
    def fetch(self, http) -> list[Event]:
        initial = http.get_text(self.cfg.url)
        whole_url = urljoin(self.cfg.url, "/api_program")
        whole = http.post_text(whole_url, {
            "cinema[]": "6", "hall[]": ["7", "8", "20"], "ef": 0, "m": "", "wp": 1,
            "filterType": "default", "ao": 0, "d": 0, "_locale": "cs",
        })
        out: list[Event] = []
        seen: set[str] = set()
        for label, html_text in (("listing", initial), ("whole programme", whole)):
            events = self._parse_document(html_text, label)
            for event in events:
                if event.native_id not in seen:
                    out.append(event)
                    seen.add(event.native_id)
        return out

    def _parse_document(self, html_text: str, label: str) -> list[Event]:
        doc = soup(html_text)
        scripts = doc.find_all("script", type="application/ld+json")
        if not scripts:
            raise ValueError(f"Bio Central {label} response has no Event JSON-LD programme")
        out: list[Event] = []
        for script in scripts:
            try:
                item = json.loads(script.string or script.get_text())
                event = self._parse(item)
            except (json.JSONDecodeError, TypeError, ValueError) as exc:
                log.warning("%s: skipping malformed JSON-LD event: %s", self.name, exc)
                continue
            if event:
                out.append(event)
        if not out:
            raise ValueError(f"Bio Central {label} response has no valid Hradec Králové Event JSON-LD")
        return out

    def _parse(self, item: dict) -> Event | None:
        if not isinstance(item, dict) or item.get("@type") != "Event":
            return None
        title = clean(html.unescape(item.get("name", "")))
        start_s = item.get("startDate")
        if not title or not isinstance(start_s, str):
            return None
        start = local(datetime.fromisoformat(start_s))
        end_s = item.get("endDate")
        end = local(datetime.fromisoformat(end_s)) if isinstance(end_s, str) else None
        location = item.get("location")
        if not isinstance(location, dict):
            return None
        venue = clean(location.get("name"))
        address = location.get("address")
        locality = clean(address.get("addressLocality")) if isinstance(address, dict) else ""
        if "hradec kr" not in locality.lower():
            return None
        url = item.get("url") or self.cfg.page_url
        if not isinstance(url, str):
            return None
        native_id = url.rsplit("projection=", 1)[-1] if "projection=" in url else f"{title}|{start.isoformat()}"
        return self.event(
            title=title, start=start, end=end, all_day=False, url=url, venue=venue or "Bio Central",
            native_category="Film", description=clean(html.unescape(item.get("description", "")))[:500],
            image=item.get("image"), native_id=native_id, place_raw=self.cfg.place,
        )
