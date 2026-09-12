"""MENU music programme published in the site's Tumblr RSS feed."""

from __future__ import annotations

import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit, urlunsplit

from bs4 import BeautifulSoup

from ..dates import TZ
from ..model import Event
from .base import Source, clean, soup

_DATE = re.compile(
    r"^\s*(\d{1,2})\s*\.\s*(\d{1,2})(?:\s*\.\s*(\d{4}))?\s*\.?,?"
    r"(?:\s+(\d{1,2})(?:\s*[:.]\s*(\d{2})|\s*h\b))?\s*$",
    re.IGNORECASE,
)
_GENRE = re.compile(
    r"(?:^|\s)/\s*(koncert|projekce|vernis[aá][zž]|v[yý]stava|p[řr]edn[aá][sš]ka|"
    r"workshop|performance|festival|diskuse|debata|divadlo)\s*$",
    re.IGNORECASE,
)
_VENUE_HK = re.compile(r"s\s*[ýy]\s*p\s*k\s*a", re.IGNORECASE)
_CITY_HK = re.compile(r"\bhradec\s+kr[aá]lov[eé]\b", re.IGNORECASE)
_OTHER_CITY = re.compile(r"\b(?:praha|brno|ostrava|plze[nň])\b", re.IGNORECASE)
_SKIP_TITLE = re.compile(
    r"^(?:program|menu presents|warm[ -]?up|p[řr]edprodej\b.*)$", re.IGNORECASE
)
_LEADING_TIME = re.compile(r"^\s*(\d{1,2})(?:\s*[:.]\s*(\d{2})|\s*h\b)", re.IGNORECASE)


def _canonical_url(value: str, fallback: str) -> str:
    parts = urlsplit(value or fallback)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def _published_year(text: str) -> tuple[int, int]:
    published = parsedate_to_datetime(text)
    return published.year, published.month


class MenuMusicSource(Source):
    def fetch(self, http) -> list[Event]:
        return self.parse(http.get_text(self.cfg.url))

    def parse(self, xml: str) -> list[Event]:
        feed = BeautifulSoup(xml, "xml")
        if feed.find("rss") is None or feed.find("channel") is None:
            raise ValueError("MENU response is not an RSS feed")
        items = feed.select("item")

        events: list[Event] = []
        for item in items:
            description = item.find("description")
            published = item.find("pubDate")
            if not description or not published:
                continue
            try:
                pub_year, pub_month = _published_year(clean(published.get_text(" ")))
            except (TypeError, ValueError, OverflowError):
                continue
            link = item.find("link")
            guid = item.find("guid")
            url = _canonical_url(clean(link.get_text(" ")) if link else "", self.cfg.page_url)
            native_post_id = clean(guid.get_text(" ")) if guid else url
            events.extend(self._parse_post(description.get_text(), pub_year, pub_month, url, native_post_id))
        return events

    def _parse_post(
        self, html: str, pub_year: int, pub_month: int, url: str, native_post_id: str
    ) -> list[Event]:
        body = soup(html)
        headings = body.select("h1, h2, h3")
        dated: list[tuple[object, re.Match[str]]] = []
        for heading in headings:
            match = _DATE.fullmatch(clean(heading.get_text(" ")))
            if match:
                dated.append((heading, match))

        out: list[Event] = []
        post_has_sypka = bool(_VENUE_HK.search(clean(body.get_text(" "))))
        for index, (date_heading, match) in enumerate(dated):
            next_heading = dated[index + 1][0] if index + 1 < len(dated) else None
            block: list[object] = []
            cursor = date_heading.find_next(["h1", "h2", "h3"])
            while cursor is not None and cursor is not next_heading:
                block.append(cursor)
                cursor = cursor.find_next(["h1", "h2", "h3"])

            block_texts = [clean(heading.get_text(" ")) for heading in block]
            if any(_OTHER_CITY.search(text) for text in block_texts):
                continue
            if not post_has_sypka and not any(_CITY_HK.search(text) for text in block_texts):
                continue
            title_parts = [text for text in block_texts if text and not _SKIP_TITLE.fullmatch(text)]
            title_parts = [
                text for text in title_parts
                if not _VENUE_HK.search(text) and not _CITY_HK.search(text)
            ]

            genres = [m.group(1).strip() for text in title_parts if (m := _GENRE.search(text))]
            title_parts = [_GENRE.sub("", text).strip() for text in title_parts]
            title_parts = [text for text in title_parts if text and text not in {"&", "/"}]
            if not title_parts and len(dated) == 1:
                pre_date = headings[:headings.index(date_heading)]
                title_parts = [clean(heading.get_text(" ")) for heading in pre_date]
                title_parts = [
                    text for text in title_parts
                    if text and not _SKIP_TITLE.fullmatch(text)
                    and not _VENUE_HK.search(text) and not _CITY_HK.search(text)
                ]
            if not title_parts:
                continue

            day, month = int(match.group(1)), int(match.group(2))
            year = int(match.group(3)) if match.group(3) else pub_year
            if not match.group(3) and pub_month == 12 and month == 1:
                year += 1
            block_time = next(
                (_LEADING_TIME.match(text) for text in block_texts if _LEADING_TIME.match(text)),
                None,
            )
            hour = int(match.group(4) or (block_time.group(1) if block_time else 0))
            minute = int(
                match.group(5) or (block_time.group(2) if block_time and block_time.group(2) else 0)
            )
            try:
                start = datetime(year, month, day, hour, minute, tzinfo=TZ)
            except ValueError:
                continue

            image = date_heading.find_next("img")
            if image is not None and next_heading is not None and next_heading in image.find_all_previous():
                image = None
            title = " + ".join(dict.fromkeys(title_parts))
            out.append(self.event(
                title=title, start=start, all_day=match.group(4) is None and block_time is None,
                url=url, place_raw=self.cfg.place,
                venue="Hradecká sýpka" if post_has_sypka else None,
                native_category=genres[0] if genres else None,
                image=image.get("src") if image and image.get("src") else None,
                native_id=f"{native_post_id}|{start.isoformat()}",
            ))
        return out
