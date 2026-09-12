"""UFFO – Společenské centrum Trutnov (uffo.cz/program): whole calendar via the site's ICS feed,
enriched with URL/category/image/description from the current month's listing page.

uffo.cz runs a stateful ASP.NET "Business Site" e-shop engine: the `/program/` page's month
dropdown, the "Dnes"/"Zítra"/"O víkendu" tabs and paging all go through signed AJAX postbacks, so a
plain GET always returns just the current calendar month (`div.productHolder[showdate]` = e.g.
"so 12" – weekday + day of month, no month/year); query-string guesses (`?month=`, `?rok=`, ...) get
redirected straight back to the bare `/program/`. Detail pages (`/<slug>-p<id>/`) carry only Product
JSON-LD (price/image/description, for the ticket shop) – there is no Event JSON-LD anywhere on the
site, on the list page or on detail pages.

The actual clean source of dates is the "Přidat do kalendáře" ICS feed the page links to
(`/uffoCompleteCalendar.ashx/?c=apple` 302s to `/data/user-content/calendar/completeCalendar.ics`):
a flat, unfolded `VEVENT` list (`UID`/`DTSTART;TZID=Europe/Prague`/`DTEND;TZID=Europe/Prague`/
`SUMMARY`/`LOCATION`, `DESCRIPTION` always empty) that reaches several months ahead (~120 events into
next year – far past the 60-day horizon) and whose `UID`s are stable across repeated fetches.
`LOCATION` is `UFFO`, `Kino Vesmír` or blank.

Since the ICS has no URL/category/image, each event is matched – by normalized title + day-of-month
+ `HH:MM`, so repeat screenings/showtimes of the same title don't collide, and only within the
current month to avoid matching e.g. a September and an October event that happen to share a title
and time – against the listing's `div.ProductView` cards: `h2 a` title/link, `.dcTimeWrap` time,
`.icon.productFlag.cs_typeIco[title]` native category (concerts/theatre; absent for Kino Vesmír
films, which get a plain "Film" category), `img[data-src]` (lazy-loaded, `src` is a data: URI
placeholder), `p.description`. Events outside the visible month simply keep no url/category/image;
`url` falls back to the programme page itself.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from urllib.parse import urljoin

from ..dates import TZ, today
from ..model import Event
from ..normalize import norm_title
from .base import Source, clean, soup

log = logging.getLogger(__name__)

ICS_URL = "https://uffo.cz/data/user-content/calendar/completeCalendar.ics"

_VEVENT = re.compile(r"BEGIN:VEVENT(.*?)END:VEVENT", re.DOTALL)
_FIELD = re.compile(r"^([A-Z]+)(?:;[^:\n]*)?:(.*)$", re.MULTILINE)
_DT = re.compile(r"^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})$")

_VENUE_MAP = {"uffo": "UFFO Trutnov", "kino vesmír": "Kino Vesmír"}


def _parse_dt(text: str) -> datetime | None:
    m = _DT.match(text.strip())
    if not m:
        return None
    y, mo, d, h, mi, s = (int(x) for x in m.groups())
    return datetime(y, mo, d, h, mi, s, tzinfo=TZ)


class UffoSource(Source):
    def fetch(self, http) -> list[Event]:
        ics_url = self.cfg.extra.get("ics_url", ICS_URL)
        items = self._parse_ics(http.get_text(ics_url))
        lookup: dict[tuple[str, int, str], dict] = {}
        try:
            lookup = self._parse_listing(http.get_text(self.cfg.url))
        except Exception as e:  # noqa: BLE001
            log.warning("%s: listing %s failed, using ICS only: %s", self.name, self.cfg.url, e)
        ref = today()
        out: list[Event] = []
        for item in items:
            try:
                out.append(self._build(item, lookup, ref))
            except Exception as e:  # noqa: BLE001
                log.warning("%s: skipping malformed item: %s", self.name, e)
        return out

    def _parse_ics(self, text: str) -> list[dict]:
        out = []
        for block in _VEVENT.findall(text):
            fields = {k: v.strip() for k, v in _FIELD.findall(block)}
            start = _parse_dt(fields.get("DTSTART", ""))
            title = clean(fields.get("SUMMARY"))
            if not title or not start:
                continue
            out.append({
                "uid": fields.get("UID") or f"{title}|{fields.get('DTSTART', '')}",
                "title": title,
                "start": start,
                "end": _parse_dt(fields.get("DTEND", "")),
                "location": clean(fields.get("LOCATION")),
            })
        return out

    def _parse_listing(self, html: str) -> dict[tuple[str, int, str], dict]:
        doc = soup(html)
        out: dict[tuple[str, int, str], dict] = {}
        for holder in doc.select("div.productHolder[showdate]"):
            dm = re.search(r"(\d{1,2})$", holder.get("showdate", ""))
            if not dm:
                continue
            day = int(dm.group(1))
            for card in holder.select("div.ProductView"):
                a = card.select_one("h2 a")
                time_el = card.select_one(".dcTimeWrap")
                if not a or not a.get("href") or not time_el:
                    continue
                tm = re.search(r"\d{1,2}:\d{2}", time_el.get_text())
                if not tm:
                    continue
                type_icon = card.select_one(".icon.productFlag.cs_typeIco")
                if type_icon:
                    category = clean(type_icon.get("title") or type_icon.get_text())
                elif card.select_one(".icon.productFlag.cs_vesmirPlace"):
                    category = "Film"
                else:
                    category = None
                desc = card.select_one("p.description")
                img = card.select_one("img")
                src = (img.get("data-src") or img.get("src")) if img else None
                key = (norm_title(clean(a.get_text())), day, tm.group())
                out[key] = {
                    "url": self._abs(a["href"]),
                    "category": category,
                    "description": clean(desc.get_text(" ")) if desc else "",
                    "image": self._abs(src) if src and not src.startswith("data:") else None,
                }
        return out

    def _abs(self, href: str | None) -> str | None:
        return urljoin(self.cfg.url, href) if href else None

    def _build(self, item: dict, lookup: dict, ref) -> Event:
        start, end = item["start"], item["end"]
        if end and end <= start:
            end = None
        loc = item["location"].lower()
        venue = _VENUE_MAP.get(loc, item["location"] or "UFFO Trutnov")
        info: dict = {}
        if start.year == ref.year and start.month == ref.month:
            key = (norm_title(item["title"]), start.day, start.strftime("%H:%M"))
            info = lookup.get(key, {})
        return self.event(
            title=item["title"], start=start, end=end, all_day=False,
            url=info.get("url") or self.cfg.page_url,
            venue=venue, native_category=info.get("category"),
            description=(info.get("description") or "")[:500],
            image=info.get("image"), native_id=item["uid"],
        )
