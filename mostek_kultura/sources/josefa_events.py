"""Domov sv. Josefa / Areál sv. Josefa Žireč: `article.b-article` cards with
`.b-article__event-date` (date span + venue span), `h3.b-article__name`, `p.b-article__desc`,
link `a.link-extend__link`. Date only (no time)."""

from __future__ import annotations

from urllib.parse import urljoin

from ..dates import parse_cz
from ..model import Event
from .base import Source, clean, soup


class JosefaEventsSource(Source):
    def fetch(self, http) -> list[Event]:
        return self.parse(http.get_text(self.cfg.url))

    def parse(self, html: str) -> list[Event]:
        doc = soup(html)
        out: list[Event] = []
        seen: set[str] = set()
        for art in doc.select("article.b-article"):
            date_el = art.select_one(".b-article__event-date")
            name = art.select_one(".b-article__name")
            if not date_el or not name:
                continue
            spans = [clean(s.get_text()) for s in date_el.find_all("span")]
            parsed = parse_cz(spans[0] if spans else "")
            if not parsed:
                continue
            start, end, all_day = parsed
            a = art.select_one("a.link-extend__link") or art.find("a", href=True)
            url = urljoin(self.cfg.url, a["href"]) if a else self.cfg.url
            key = f"{start.date()}|{clean(name.get_text())}"
            if key in seen:
                continue
            seen.add(key)
            desc = art.select_one(".b-article__desc")
            img = art.select_one("img")
            out.append(self.event(
                title=clean(name.get_text()), start=start, end=end, all_day=all_day, url=url,
                venue=spans[1] if len(spans) > 1 else None,
                description=clean(desc.get_text(" "))[:500] if desc else "",
                image=urljoin(self.cfg.url, img["src"]) if img and img.get("src") else None,
                native_id=key,
            ))
        return out
