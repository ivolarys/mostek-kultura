"""Drupal event calendar as used by mestovrchlabi.cz/kalendar-akci.

Listing: `?page=N` (12 teasers per page, `.node--type-event` with `<time datetime>`, event type, title link).
Detail: address (`field--name-field-address`), end time (`...event-date2` "14:00 – 18:00"), body.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from urllib.parse import urljoin

from ..dates import local
from ..model import Event
from .base import Source, clean, soup

log = logging.getLogger(__name__)
_TIME_RANGE = re.compile(r"(\d{1,2}):(\d{2})\s*[–-]\s*(\d{1,2}):(\d{2})")


class DrupalEventsSource(Source):
    def fetch(self, http) -> list[Event]:
        events: list[Event] = []
        seen: set[str] = set()
        skip_detail = {t.lower() for t in self.cfg.extra.get("skip_detail_types", [])}
        for page in range(int(self.cfg.extra.get("pages", 4))):
            url = self.cfg.url if page == 0 else f"{self.cfg.url}?page={page}"
            items = self.parse_listing(http.get_text(url))
            if not items:
                break
            for ev in items:
                if ev.url in seen:
                    continue
                seen.add(ev.url)
                if (ev.native_category or "").lower() not in skip_detail:
                    self.enrich(ev, http)
                events.append(ev)
        return events

    def parse_listing(self, html: str) -> list[Event]:
        doc = soup(html)
        out: list[Event] = []
        for it in doc.select(".view-display-id-block_1 .node--type-event, .view-content .node--type-event"):
            a = it.select_one(".text-event-teaser-title a") or it.select_one(".field--name-node-title a")
            t = it.select_one("time[datetime]")
            if not a or not t:
                continue
            try:
                start = local(datetime.fromisoformat(t["datetime"]))
            except ValueError:
                continue
            typ = it.select_one(".field--name-field-event-type")
            img = it.select_one("img")
            url = urljoin(self.cfg.url, a["href"])
            out.append(self.event(
                title=clean(a.get_text()), start=start, all_day=start.hour == 0 and start.minute == 0,
                url=url, native_category=clean(typ.get_text()) if typ else None,
                image=urljoin(self.cfg.url, img["src"]) if img and img.get("src") else None,
                native_id=url,
            ))
        return out

    def enrich(self, ev: Event, http) -> None:
        try:
            doc = soup(http.get_text(ev.url))
        except Exception as e:  # noqa: BLE001
            log.warning("%s: detail %s failed: %s", self.name, ev.url, e)
            return
        node = doc.select_one(".node--type-event.node--view-mode-full") or doc
        addr = node.select_one(".field--name-field-address")
        if addr:
            ev.venue = re.sub(r"^Kde\s+", "", clean(addr.get_text(" "))) or None
        rng = node.select_one(".field--name-display-field-copynode-event-date2")
        m = _TIME_RANGE.search(clean(rng.get_text()) if rng else "")
        if m:
            h, mi = int(m.group(3)), int(m.group(4))
            ev.end = ev.start.replace(hour=h, minute=mi)
            if ev.end <= ev.start:
                ev.end = None
        body = node.select_one(".field--name-body")
        if body:
            ev.description = clean(body.get_text(" "))[:500]
