"""NPÚ monument sites (e.g. hospital-kuks.cz/cs/akce): `.events__item` cards.

Info lines in `.events__item-info p > span` (after the icon span): category, venue,
date ("12. 9. 2026", with hidden unix timestamps), time range ("10.00 – 18.00").
Only the current window is server-rendered (month tabs are JS-only).
"""

from __future__ import annotations

import re
from urllib.parse import urljoin

from ..dates import parse_cz
from ..model import Event
from .base import Source, clean, soup

_DATE = re.compile(r"\d{1,2}\.\s*\d{1,2}\.\s*\d{4}")
_TIME = re.compile(r"\d{1,2}[.:]\d{2}")


class NpuEventsSource(Source):
    def fetch(self, http) -> list[Event]:
        return self.parse(http.get_text(self.cfg.url))

    def parse(self, html: str) -> list[Event]:
        doc = soup(html)
        out: list[Event] = []
        for it in doc.select(".events__item"):
            a = it.select_one("a.events__item-title")
            if not a:
                continue
            lines = []
            for p in it.select(".events__item-info p"):
                spans = [s for s in p.find_all("span", recursive=False) if "ico" not in (s.get("class") or [])]
                if spans:
                    for hidden in spans[-1].select("span[style]"):
                        hidden.extract()
                    lines.append(clean(spans[-1].get_text()))
            date_line = next((x for x in lines if _DATE.search(x)), "")
            time_line = next((x for x in lines if _TIME.search(x) and not _DATE.search(x)), "")
            parsed = parse_cz(f"{date_line} {time_line.replace('.', ':')}")
            if not parsed:
                continue
            start, end, all_day = parsed
            others = [x for x in lines if x not in (date_line, time_line)]
            img = it.select_one("img")
            out.append(self.event(
                title=clean(a.get_text()), start=start, end=end, all_day=all_day,
                url=urljoin(self.cfg.url, a["href"]),
                native_category=others[0] if others else None,
                venue=others[1] if len(others) > 1 else None,
                image=urljoin(self.cfg.url, img["src"]) if img and img.get("src") else None,
                native_id=urljoin(self.cfg.url, a["href"]),
            ))
        return out
