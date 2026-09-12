import re
from datetime import date
from pathlib import Path

import pytest

from mostek_kultura.config import SourceConfig
from mostek_kultura.http import FixtureHttp
from mostek_kultura.normalize import apply_source_filters
from mostek_kultura.sources.hkinfo_program import HkinfoProgramSource
from mostek_kultura.sources.naplavka_program import NaplavkaProgramSource

ROOT = Path(__file__).parent / "fixtures"


def test_naplavka_program_fixture():
    cfg = SourceConfig("naplavka-hk", "naplavka_program", url="https://naplavkahk.cz/program")
    events = NaplavkaProgramSource(cfg).parse((ROOT / "hradec-naplavka/program.html").read_text())
    assert len(events) == 1
    event = events[0]
    assert event.start.strftime("%Y-%m-%d %H:%M") == "2026-09-12 16:00"
    assert event.venue == "Náplavka kulturní klub" and event.native_id.endswith("nabrezi-jede")
    assert event.image == "https://naplavkahk.cz/media/poster.jpg"


def test_hkinfo_filters_and_explicit_ranges():
    html = (ROOT / "hradec-hkinfo/program.html").read_text()
    cfg = SourceConfig("sauna-nuuk", "hkinfo_program", url="https://www.hkinfo.cz/cs/program", extra={"include_venue": r"(?i)nuuk"})
    events = HkinfoProgramSource(cfg).parse(html, year=2026, month=9, page_url="https://www.hkinfo.cz/cs/kalendar-akci.html?mesic=9&rok=2026")
    assert len(events) == 1
    assert events[0].start.date() == date(2026, 9, 25)
    assert events[0].end.date() == date(2026, 9, 27) and events[0].all_day
    assert events[0].native_category == "Festival"

    cfg = SourceConfig("nablesi", "hkinfo_program", url="https://www.hkinfo.cz/cs/program", extra={"include_title": r"^nábleší", "native_category": "Trhy a jarmarky"})
    events = HkinfoProgramSource(cfg).parse(html, year=2026, month=9, page_url="test")
    assert len(events) == 1 and events[0].start.strftime("%H:%M") == "09:00"
    assert events[0].native_category == "Trhy a jarmarky"


def test_record_fixtures_fetch_all_hradec_sources(monkeypatch):
    monkeypatch.setenv("MOSTEK_NOW", "2026-09-11T12:00:00+02:00")
    nap_cfg = SourceConfig("naplavka-hk", "naplavka_program", url="https://naplavkahk.cz/program", place="Hradec Králové")
    nap_events = NaplavkaProgramSource(nap_cfg).fetch(FixtureHttp(ROOT / "naplavka-hk"))
    assert len(nap_events) == 3 and all(event.place_raw == "Hradec Králové" for event in nap_events)
    assert nap_events[0].venue == "Náplavka kulturní klub"

    for name, extra, expected in (
        ("nablesi", {"include_title": r"(?i)^nábleší", "native_category": "Trhy a jarmarky"}, "Nábleší 2026"),
        ("sauna-nuuk", {"include_venue": r"(?i)nuuk"}, "Hiki Joki - festival potu, ohně a lučního lazebnictví"),
    ):
        cfg = SourceConfig(name, "hkinfo_program", url="https://www.hkinfo.cz/cs/program", place="Hradec Králové", extra=extra)
        events = HkinfoProgramSource(cfg).fetch(FixtureHttp(ROOT / name))
        assert events and events[0].title == expected
        assert all(event.place_raw == "Hradec Králové" for event in events)
        if name == "nablesi":
            assert len(events) == 3
            assert [event.start.date() for event in events] == [date(2026, 9, 27), date(2026, 10, 25), date(2026, 11, 29)]
            assert all("|2026-" in (event.native_id or "") for event in events)
        else:
            assert len(events) == 1 and events[0].url.endswith("#textdet3661")
        assert all(event.image and event.image.startswith("https://") for event in events)


def test_hradec_vyber_fixture_keeps_only_selected_venues(monkeypatch, cfg):
    monkeypatch.setenv("MOSTEK_NOW", "2026-09-11T12:00:00+02:00")
    source_cfg = next(source for source in cfg.sources if source.name == "hradec-vyber")
    raw_cfg = SourceConfig(
        source_cfg.name,
        source_cfg.type,
        url=source_cfg.url,
        place=source_cfg.place,
        extra={**source_cfg.extra, "venue_map": {}},
    )
    raw_events = HkinfoProgramSource(raw_cfg).fetch(FixtureHttp(ROOT / "hradec-vyber"))
    events = HkinfoProgramSource(source_cfg).fetch(FixtureHttp(ROOT / "hradec-vyber"))

    # The anchored configuration filter admits each selected institution (with
    # museum sub-sites), but none of the rest of the city-wide calendar.
    original_venues = {event.venue for event in raw_events}
    assert len(raw_events) == len(events) == 109
    assert all(event.venue and re.search(source_cfg.extra["include_venue"], event.venue, re.IGNORECASE) for event in raw_events)
    for venue in (
        "Petrof Gallery, Hradec Králové",
        "Filharmonie Hradec Králové , Hradec Králové",
        "Sál Soni Červené, Hradec Králové",
        "Galerie moderního umění v Hradci Králové, Hradec Králové",
        "Muzeum východních Čech v Hradci Králové, Hradec Králové",
        "Muzeum východních Čech - budova ARCHA, Hradec Králové",
        "Hlavní odborné pracoviště Gayerova kasárna, Hradec Králové",
        "Hvězdárna a planetárium v Hradci Králové, Hradec Králové",
        "Galerie Artičok, Hradec Králové",
        "AC klub, Hradec Králové",
        "Adalbertinum, Hradec Králové",
    ):
        assert venue in original_venues
    assert all("Nábleší" not in (event.venue or "") and "NUUK" not in (event.venue or "") for event in raw_events)

    by_title = {event.title: event for event in events}
    assert by_title["ODPOLEDNÍ PROGRAM PRO DĚTI"].native_category == "Pro děti"
    assert by_title["Architóny | Jaroslav Svěcený - Vivaldi u Kotěry"].native_category == "Koncert"
    assert by_title["Zářijový SWAP"].native_category is None  # HKinfo type 18 = Ostatní
    assert all(event.venue != "Sál Soni Červené, Hradec Králové" for event in events)
    assert any(event.venue == "Sál Soni Červené, Filharmonie Hradec Králové" for event in events)

    kept = apply_source_filters(events, source_cfg)
    assert len(kept) == 92
    filtered_titles = {event.title for event in kept}
    assert "Štěpán Rak & Miloš Dvořáček - KONCERT ZRUŠEN!" not in filtered_titles
    assert not any(title.startswith(("Taneční 2026", "Zahájení kurzů tance")) for title in filtered_titles)
    exclusion = re.compile(source_cfg.exclude_title or "")
    assert all(exclusion.search(title) for title in ("ZRUŠENO", "ZRUŠENÝ koncert", "ZRUŠENÁ akce", "Zrusene vystoupení"))


def test_hkinfo_year_boundary_and_empty_selection():
    html = (ROOT / "hradec-hkinfo/program.html").read_text()
    html = html.replace("25<br>-<br>27", "30<br>-<br>2").replace("září", "prosinec - leden")
    cfg = SourceConfig("sauna-nuuk", "hkinfo_program", url="https://www.hkinfo.cz/cs/program",
                       extra={"include_venue": "nuuk"})
    src = HkinfoProgramSource(cfg)
    december = src.parse(html, year=2026, month=12)[0]
    january = src.parse(html, year=2027, month=1)[0]
    assert december.start.date() == january.start.date() == date(2026, 12, 30)
    assert december.end.date() == january.end.date() == date(2027, 1, 2)
    assert december.source_id == january.source_id
    cfg.extra["include_venue"] = "Neexistující místo"
    assert src.parse(html, year=2026, month=12) == []


def test_programme_errors_do_not_become_successful_empty_feeds():
    cfg = SourceConfig("sauna-nuuk", "hkinfo_program", url="https://www.hkinfo.cz/cs/program")
    with pytest.raises(ValueError):
        HkinfoProgramSource(cfg).parse("<html>Server error</html>", year=2026, month=9)
    with pytest.raises(ValueError):
        NaplavkaProgramSource(cfg).parse("<html>Server error</html>")

    class Unavailable:
        def get_text(self, url):
            raise ConnectionError("Programme unavailable")

    with pytest.raises(ConnectionError):
        HkinfoProgramSource(cfg).fetch(Unavailable())
