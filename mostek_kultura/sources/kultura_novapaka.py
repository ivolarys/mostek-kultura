"""Kultura Nová Paka (kultura-novapaka.cz): regional culture portal (MKS + partner venues).

The front page (iso-8859-2 encoded) server-renders upcoming events as `div.program <category>` blocks
(e.g. `program koncert  ` – note the trailing double space, a spare BEM-modifier slot that is usually
empty): `.datum span` holds "D.&nbsp;<month name>&nbsp;YYYY od&nbsp;H<sup>MM</sup>[ do&nbsp;H<sup>MM</sup>]",
`h2 a` the title/link, an `img` inside the `a` before it, and a free-form `<p>` with a lead paragraph
followed by `<strong>Kde</strong>: venue` (and `Vstupné`/`Pořadatel`) lines separated by `<br>`. There is
no date-range query or pagination; the page only ever shows a rolling ~2-3 week window (like
hospital-kuks.cz), which is what gets fetched.
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime, timedelta
from urllib.parse import urljoin

from ..dates import MONTHS, TZ
from ..model import Event
from .base import Source, clean, soup

log = logging.getLogger(__name__)

_DATE_HEAD = re.compile(
    r"(\d{1,2})\.\s*([a-zěščřžýáíéúůň]+)\s*(\d{4})", re.IGNORECASE
)
_HOUR = re.compile(r"(?:od|do)\s*(\d{1,2})")


class KulturaNovaPakaSource(Source):
    def fetch(self, http) -> list[Event]:
        html = http.get_text(self.cfg.url, encoding="iso-8859-2")
        return self.parse(html)

    def parse(self, html: str) -> list[Event]:
        doc = soup(html)
        out: list[Event] = []
        for div in doc.find_all("div", class_=True):
            classes = div.get("class") or []
            if not classes or classes[0] != "program":
                continue
            try:
                ev = self._parse_item(div, classes)
            except Exception as e:  # noqa: BLE001
                log.warning("%s: skipping malformed item: %s", self.name, e)
                continue
            if ev:
                out.append(ev)
        return out

    def _parse_item(self, div, classes: list[str]) -> Event | None:
        link = div.select_one("h2 a")
        date_el = div.select_one(".datum")
        if not link or not date_el:
            return None
        parsed = _parse_datum(date_el)
        if not parsed:
            return None
        start, end, all_day = parsed
        url = urljoin(self.cfg.url, link["href"])
        p = div.find("p")
        venue = _field(p, "Kde") if p else None
        img = div.select_one("img")
        category = next((c for c in classes[1:] if c.strip()), None)
        return self.event(
            title=clean(link.get_text()), start=start, end=end, all_day=all_day, url=url,
            venue=venue, native_category=category,
            description=_lead(p)[:500] if p else "",
            image=urljoin(self.cfg.url, img["src"]) if img and img.get("src") else None,
            native_id=url,
        )


def _parse_datum(date_el) -> tuple[datetime, datetime | None, bool] | None:
    """'11. září 2026 od 20:00' / '12. září 2026 od 19:00 do 1:00' (minutes are in <sup>)."""
    minutes = [clean(s.get_text()) for s in date_el.find_all("sup")]
    for s in date_el.find_all("sup"):
        s.extract()
    text = clean(date_el.get_text(" "))
    m = _DATE_HEAD.match(text)
    if not m:
        return None
    day, month_name, year = int(m.group(1)), m.group(2).lower(), int(m.group(3))
    month = MONTHS.get(month_name)
    if not month:
        return None
    try:
        d = date(year, month, day)
    except ValueError:
        return None
    hours = [int(h) for h in _HOUR.findall(text)]
    if not hours:
        return datetime(d.year, d.month, d.day, tzinfo=TZ), None, True
    start_min = int(minutes[0]) if minutes else 0
    start = datetime(d.year, d.month, d.day, hours[0], start_min, tzinfo=TZ)
    end = None
    if len(hours) > 1:
        end_min = int(minutes[1]) if len(minutes) > 1 else 0
        end = datetime(d.year, d.month, d.day, hours[1], end_min, tzinfo=TZ)
        if end <= start:
            end += timedelta(days=1)
    return start, end, False


def _field(p, label: str) -> str | None:
    for strong in p.find_all("strong"):
        if clean(strong.get_text()).rstrip(":") != label:
            continue
        parts = []
        for sib in strong.next_siblings:
            if getattr(sib, "name", None) in ("strong", "br"):
                break
            parts.append(sib.get_text() if hasattr(sib, "get_text") else str(sib))
        value = clean("".join(parts)).lstrip(": ").strip()
        return value or None
    return None


def _lead(p) -> str:
    parts = []
    for c in p.children:
        if getattr(c, "name", None) == "strong":
            break
        parts.append(c.get_text() if hasattr(c, "get_text") else str(c))
    text = clean("".join(parts))
    return re.sub(r"…?\s*čtěte celý text\s*$", "", text).strip()
