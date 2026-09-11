"""Testy pro ruční zdroj (manual_events.yaml)."""

from __future__ import annotations

from mostek_kultura.config import SourceConfig
from mostek_kultura.sources.manual import ManualSource

YAML = """
events:
  - title: Koncert v zahradě
    date: 2026-09-25
    time: "19:00"
    end: "21:00"
    place: Dvůr Králové nad Labem
    venue: L'Art Café
    category: koncert
    url: https://www.facebook.com/example/
    description: Testovací akce s časem.
  - title: Celodenní jarmark
    date: 2026-10-03
    place: Trutnov
  - title: Akce bez data
    time: "18:00"
"""


def _src(url: str) -> ManualSource:
    return ManualSource(SourceConfig(name="rucne", type="manual", url=url))


def test_manual_parses_timed_and_all_day_events(tmp_path):
    path = tmp_path / "manual_events.yaml"
    path.write_text(YAML, encoding="utf-8")

    events = _src(str(path)).fetch(None)
    assert len(events) == 2  # malformed entry (missing date) skipped

    timed = next(e for e in events if e.title == "Koncert v zahradě")
    assert not timed.all_day
    assert timed.start.strftime("%Y-%m-%d %H:%M") == "2026-09-25 19:00"
    assert timed.end is not None and timed.end.strftime("%H:%M") == "21:00"
    assert timed.place_raw == "Dvůr Králové nad Labem"
    assert timed.venue == "L'Art Café"
    assert timed.category == "koncert"
    assert timed.native_category == "koncert"
    assert timed.url == "https://www.facebook.com/example/"
    assert timed.native_id == "manual:2026-09-25|Koncert v zahradě"
    assert timed.source == "rucne"

    all_day = next(e for e in events if e.title == "Celodenní jarmark")
    assert all_day.all_day
    assert all_day.end is None
    assert all_day.start.strftime("%Y-%m-%d %H:%M") == "2026-10-03 00:00"
    assert all_day.place_raw == "Trutnov"


def test_manual_missing_file_returns_empty(tmp_path):
    missing = tmp_path / "nope.yaml"
    events = _src(str(missing)).fetch(None)
    assert events == []


def test_manual_empty_events_list(tmp_path):
    path = tmp_path / "manual_events.yaml"
    path.write_text("events: []\n", encoding="utf-8")
    assert _src(str(path)).fetch(None) == []
