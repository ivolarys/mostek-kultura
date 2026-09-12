"""Bajkazyl Hradec Králové events from its public Netlify API."""

from __future__ import annotations

import re
import unicodedata
from datetime import UTC, datetime
from html import unescape
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from ..dates import local
from ..model import Event
from .base import Source, clean

_META_MARKER = re.compile(r"\[(?:TITLE|SUBTITLE|DESCRIPTION|IMAGES|YOUTUBE|BANDCAMP)\]", re.IGNORECASE)
_CANCELLED = re.compile(r"\b(?:zru[šs]eno|cancel+ed)\b", re.IGNORECASE)


def _slug_part(title: str) -> str:
    """Match the slug format used by Bajkazyl's event detail pages."""
    normalized = unicodedata.normalize("NFD", title.lower())
    ascii_title = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"^-+|-+$", "", re.sub(r"[^a-z0-9]+", "-", ascii_title))


def _safe_image(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    return candidate if urlparse(candidate).scheme in {"http", "https"} else None


def _clean_description(value: object) -> str:
    if not isinstance(value, str):
        return ""
    text = BeautifulSoup(value, "lxml").get_text(" ") if "<" in value else unescape(value)
    return clean(_META_MARKER.sub(" ", text))


class BajkazylProgramSource(Source):
    def fetch(self, http) -> list[Event]:
        return self.parse(http.get_json(self.cfg.url))

    def parse(self, payload: object) -> list[Event]:
        if not isinstance(payload, list):
            raise ValueError("Bajkazyl API payload must be a list")  # noqa: TRY004

        events: list[Event] = []
        for item in payload:
            if not isinstance(item, dict) or self._is_cancelled(item):
                continue
            try:
                event = self._parse_item(item)
            except (TypeError, ValueError):
                continue
            if event:
                events.append(event)
        return events

    def _is_cancelled(self, item: dict) -> bool:
        if item.get("cancelled") is True or item.get("isCancelled") is True:
            return True
        status = item.get("status")
        if isinstance(status, str) and status.casefold() in {"cancelled", "canceled", "zruseno", "zrušeno"}:
            return True
        return bool(_CANCELLED.search(item.get("title", ""))) if isinstance(item.get("title"), str) else False

    def _parse_item(self, item: dict) -> Event | None:
        original_title = item.get("title")
        title = item.get("mainTitle") or original_title
        native_id = item.get("id")
        start_raw = item.get("start")
        if not isinstance(original_title, str) or not original_title.strip():
            return None
        if not isinstance(title, str) or not title.strip() or not isinstance(native_id, str) or not native_id:
            return None
        if not isinstance(start_raw, str):
            return None

        start_utc = datetime.fromisoformat(start_raw)
        if start_utc.tzinfo is None:
            return None
        start = local(start_utc)
        end = None
        end_raw = item.get("end")
        if isinstance(end_raw, str) and end_raw:
            parsed_end = datetime.fromisoformat(end_raw)
            if parsed_end.tzinfo is not None:
                end = local(parsed_end)
                if end < start:
                    end = None

        slug = _slug_part(original_title)
        if not slug:
            return None
        utc_stamp = start_utc.astimezone(UTC)
        event_url = f"https://bajkazylhk.cz/akce/{slug}-{utc_stamp:%Y%m%d-%H%M}"
        images = item.get("images")
        image = next(filter(None, (_safe_image(value) for value in images)), None) if isinstance(images, list) else None
        description = _clean_description(item.get("parsedDescription"))
        if not description:
            description = _clean_description(item.get("description"))
        location = clean(item.get("location")) if isinstance(item.get("location"), str) else ""

        return self.event(
            title=clean(title), start=start, end=end, all_day=False,
            url=event_url, place_raw=self.cfg.place,
            venue=location or "Bajkazyl Hradec Králové", description=description[:500],
            image=image, native_id=native_id,
        )
