"""Valdštejnská lodžie (valdstejnskalodzie.cz/program): whole-season program on one page.

Items `.c-program__item[data-in-month=MMYYYY]` with `.c-program__day-number` ("13."),
`.c-program__time` ("15" + <sup>30</sup>), `h5 a` title/link, first `p` as lead, `img.c-program__image`.
"""

from __future__ import annotations

import re
from datetime import datetime

from ..dates import TZ
from ..model import Event
from .base import Source, clean, soup


class LodzieSource(Source):
    def fetch(self, http) -> list[Event]:
        return self.parse(http.get_text(self.cfg.url))

    def parse(self, html: str) -> list[Event]:
        doc = soup(html)
        out: list[Event] = []
        for it in doc.select(".c-program__item[data-in-month]"):
            a = it.select_one("h5 a")
            day = it.select_one(".c-program__day-number")
            m = re.fullmatch(r"(\d{2})(\d{4})", it.get("data-in-month", ""))
            if not a or not day or not m:
                continue
            dm = re.search(r"\d{1,2}", day.get_text())
            if not dm:
                continue
            month, year, d = int(m.group(1)), int(m.group(2)), int(dm.group())
            time_el = it.select_one(".c-program__time")
            hour = minute = None
            if time_el:
                sup = time_el.select_one("sup")
                mins = re.search(r"\d{1,2}", sup.get_text()) if sup else None
                if sup:
                    sup.extract()
                hm = re.search(r"\d{1,2}", time_el.get_text())
                if hm:
                    hour, minute = int(hm.group()), int(mins.group()) if mins else 0
            try:
                start = datetime(year, month, d, hour or 0, minute or 0, tzinfo=TZ)
            except ValueError:
                continue
            text = it.select_one(".c-program__text")
            lead = ""
            if text:
                ps = [p for p in text.find_all("p", recursive=False)]
                lead = clean(ps[0].get_text()) if ps else ""
            img = it.select_one("img.c-program__image")
            out.append(self.event(
                title=clean(a.get_text()), start=start, all_day=hour is None, url=a["href"],
                venue=self.cfg.extra.get("venue"), description=lead[:500],
                image=img["src"] if img and img.get("src") else None, native_id=a["href"],
            ))
        return out
