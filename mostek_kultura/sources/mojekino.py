"""Biograf Na Špici Hořice: "mojekino"/Cinemaware-Ticketware cinema template. The `/klient-101/kino-30`
"Program" page renders an empty `#program_kina_kontajner` shell — client id, cinema id and a booking
widget `smid` sit on `<body data-klient>`/`<body data-kino>`/`#program_kina_tabs[data-smid]` — that JS
fills client-side via `GET /ajax/ajax_program_kina_rozsireny.php` with those ids plus
`sTab=&sTabID=&jazyk=` (the default, tab-less call resolves server-side to the "now showing" tab) and
`pocet_na_strane=100` (avoids the otherwise 10-per-page pagination).

Per film `div.subbox[data-film]`: poster (`a.fancybox` full image / `img` thumbnail fallback), detail
link+title (`h1 a`), perex (`.heading p`, trailing "Zobrazit více" link stripped); one
`.programKina-datum .item` per showtime date (`h2` = "12. 9.&nbsp;dnes"/"...zítra"/"...<weekday>", no
year) each holding one `a.m2[href]` booking link (link text = "HH:MM") and a `span.btn.price[data-id]`
whose id is stable across requests and used as `native_id`.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from urllib.parse import urljoin

from ..dates import TZ, infer_year
from ..model import Event
from .base import Source, clean, soup

_DATE_HEAD = re.compile(r"(\d{1,2})\.\s*(\d{1,2})\.")
_TIME = re.compile(r"(\d{1,2}):(\d{2})")

_VENUE = "Biograf Na Špici"



log = logging.getLogger(__name__)


class MojekinoSource(Source):
    def fetch(self, http) -> list[Event]:
        shell = soup(http.get_text(self.cfg.url))
        body = shell.find("body")
        tabs = shell.select_one("#program_kina_tabs")
        if body is None or tabs is None or not tabs.get("data-smid"):
            return []
        klient, kino, smid = body.get("data-klient"), body.get("data-kino"), tabs["data-smid"]
        ajax_url = urljoin(self.cfg.url, "/ajax/ajax_program_kina_rozsireny.php")
        query = (
            f"?strana=1&pocet_na_strane=100&sTab=&sTabID=&klient={klient}&kino={kino}"
            f"&jazyk=&smid={smid}&vychodzi_pohlad=&hladaj="
        )
        data = http.get_json(ajax_url + query)
        return self.parse(data.get("html", ""))

    def parse(self, html: str) -> list[Event]:
        doc = soup(html)
        out: list[Event] = []
        for box in doc.select("div.subbox[data-film]"):
            title_a = box.select_one("h1 a")
            if not title_a or not title_a.get("href"):
                continue
            title = clean(title_a.get_text())
            url = urljoin(self.cfg.url, title_a["href"])
            pic = box.select_one("a.fancybox") or box.select_one("img")
            image = None
            if pic:
                src = pic.get("href") or pic.get("src")
                image = urljoin(self.cfg.url, src) if src else None
            perex = box.select_one(".heading p")
            description = ""
            if perex:
                description = re.sub(r"Zobrazit více\s*$", "", clean(perex.get_text())).strip()[:500]
            for item in box.select(".programKina-datum .item"):
                try:
                    ev = self._parse_item(item, title, url, description, image)
                except Exception as e:  # noqa: BLE001
                    log.warning("%s: skipping malformed item: %s", self.name, e)
                    continue
                if ev:
                    out.append(ev)
        return out

    def _parse_item(self, item, title, url, description, image) -> Event | None:
        h2 = item.select_one("h2")
        link = item.select_one("a.m2")
        price = item.select_one(".price")
        if not h2 or not link:
            return None
        dm = _DATE_HEAD.match(clean(h2.get_text()))
        tm = _TIME.search(clean(link.get_text()))
        if not dm or not tm:
            return None
        day, month = int(dm.group(1)), int(dm.group(2))
        year = infer_year(day, month)
        start = datetime(year, month, day, int(tm.group(1)), int(tm.group(2)), tzinfo=TZ)
        native_id = (price.get("data-id") if price else None) or f"{title}|{start.isoformat()}"
        return self.event(
            title=title, start=start, all_day=False, url=url, venue=_VENUE,
            native_category="Film", description=description, image=image, native_id=native_id,
        )
