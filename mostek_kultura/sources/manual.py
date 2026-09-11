"""Ruční zdroj: akce zadané člověkem do `manual_events.yaml` (typicky z Facebooku,
odkud se akce nedají stahovat automaticky). `fetch` http nepoužívá."""

from __future__ import annotations

import logging
from datetime import date as date_cls
from datetime import datetime
from pathlib import Path

import yaml

from ..dates import TZ
from ..model import Event
from .base import Source

log = logging.getLogger(__name__)


class ManualSource(Source):
    def fetch(self, http) -> list[Event]:
        path = self._resolve_path()
        if path is None:
            log.warning("manual: soubor '%s' nenalezen (ani v cwd, ani v kořeni projektu)", self.cfg.url)
            return []
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception as e:  # noqa: BLE001
            log.warning("manual: nejde načíst '%s': %s", path, e)
            return []
        entries = raw.get("events") or []
        if not isinstance(entries, list):
            log.warning("manual: '%s' má neplatný formát (events není seznam)", path)
            return []
        out: list[Event] = []
        for i, entry in enumerate(entries):
            event = self._parse_entry(entry, i)
            if event is not None:
                out.append(event)
        return out

    def _resolve_path(self) -> Path | None:
        raw = Path(self.cfg.url)
        if raw.is_absolute():
            return raw if raw.exists() else None
        candidates = [
            Path.cwd() / raw,
            Path(__file__).resolve().parents[2] / raw,
        ]
        for c in candidates:
            if c.exists():
                return c
        return None

    def _parse_entry(self, entry, i: int) -> Event | None:
        if not isinstance(entry, dict):
            log.warning("manual: položka #%d není mapování, přeskočeno", i)
            return None
        title = entry.get("title")
        date_str = entry.get("date")
        if not title or not date_str:
            log.warning("manual: položka #%d nemá 'title' nebo 'date', přeskočeno: %r", i, entry)
            return None
        try:
            day = date_cls.fromisoformat(str(date_str))
        except ValueError:
            log.warning("manual: položka #%d má neplatné 'date' (%r), přeskočeno", i, date_str)
            return None

        time_str = entry.get("time")
        all_day = not time_str
        try:
            if time_str:
                h, m = (int(x) for x in str(time_str).split(":"))
                start = datetime(day.year, day.month, day.day, h, m, tzinfo=TZ)
            else:
                start = datetime(day.year, day.month, day.day, tzinfo=TZ)
        except ValueError:
            log.warning("manual: položka #%d má neplatný 'time' (%r), přeskočeno", i, time_str)
            return None

        end = None
        end_str = entry.get("end")
        if end_str:
            try:
                eh, em = (int(x) for x in str(end_str).split(":"))
                end = datetime(day.year, day.month, day.day, eh, em, tzinfo=TZ)
            except ValueError:
                log.warning("manual: položka #%d má neplatné 'end' (%r), ignorováno", i, end_str)
                end = None

        category = entry.get("category")
        return self.event(
            title=str(title),
            start=start,
            end=end,
            all_day=all_day,
            place_raw=entry.get("place"),
            venue=entry.get("venue"),
            category=category,
            native_category=category,
            url=entry.get("url") or "",
            description=entry.get("description") or "",
            native_id=f"manual:{date_str}|{title}",
        )
