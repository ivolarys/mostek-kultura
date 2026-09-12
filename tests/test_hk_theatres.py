"""Focused fixture tests for the two public Hradec Králové theatre programmes."""

import pytest

from mostek_kultura.config import SourceConfig
from mostek_kultura.http import FixtureHttp
from mostek_kultura.sources.drak_program import DrakProgramSource
from mostek_kultura.sources.klicperovo_program import KlicperovoProgramSource


def test_klicperovo_public_scenes_and_multiple_terms(root):
    source = KlicperovoProgramSource(SourceConfig(
        name="klicperovo-divadlo", type="klicperovo_program",
        url="https://www.klicperovodivadlo.cz/program/", place="Hradec Králové",
    ))
    events = source.fetch(FixtureHttp(root / "tests" / "fixtures" / "klicperovo-divadlo"))
    hana = [event for event in events if event.title == "Hana"]
    assert len(hana) >= 2
    assert hana[0].start.strftime("%Y-%m-%d %H:%M") == "2026-09-12 19:00"
    assert hana[0].end and hana[0].end.strftime("%H:%M") == "20:50"
    assert hana[0].venue == "Studio Beseda, Mýtská 126"
    assert hana[0].place == hana[0].place_raw == "Hradec Králové"
    assert hana[0].native_category == "Divadlo"
    assert any(event.venue == "Klicperovo divadlo, Dlouhá 99/9" for event in events)
    foyer = next(event for event in events if event.title.startswith("Miloš Chromek"))
    assert foyer.venue == "Foyer hlavní scény, Dlouhá 99/9"
    opera = next(event for event in events if event.title == "Opera je cool")
    assert opera.venue == "Sál Soni Červené, Filharmonie Hradec Králové"
    assert opera.native_category == "Koncert"
    swing = next(event for event in events if event.title.startswith("Osvobozené divadlo"))
    assert swing.native_category == "Koncert"
    assert not any(event.title == "Cyrano" and event.start.strftime("%Y-%m-%d") == "2026-09-16" for event in events)
    assert not any(event.title == "Cyrano" and event.start.strftime("%Y-%m-%d") == "2026-09-21" for event in events)
    assert not any(
        event.title == "A pak usnu a vstanu" and event.start.strftime("%Y-%m-%d") == "2026-10-26"
        for event in events
    )
    assert not any("pro školy" in (event.description or "").lower() for event in events)


def test_drak_public_rows_keep_sold_out_but_skip_school_only(root):
    source = DrakProgramSource(SourceConfig(
        name="divadlo-drak", type="drak_program", url="https://draktheatre.cz/program-3/",
        place="Hradec Králové",
    ))
    events = source.fetch(FixtureHttp(root / "tests" / "fixtures" / "divadlo-drak"))
    sedmero = [event for event in events if event.title == "Sedmero krkavců"]
    assert len(sedmero) == 1
    event = sedmero[0]
    assert event.start.strftime("%Y-%m-%d %H:%M") == "2026-10-01 17:00"
    assert event.venue == "Divadlo DRAK – Hlavní scéna" and event.native_category == "Divadlo"
    assert event.place == event.place_raw == "Hradec Králové"
    exhibit = next(event for event in events if event.title == "Město pro každého")
    assert exhibit.start.strftime("%Y-%m-%d %H:%M") == "2026-09-12 10:00"
    assert exhibit.end and exhibit.end.strftime("%H:%M") == "17:00"
    assert exhibit.venue == "Divadlo DRAK – Muzeum loutek a galerie"
    assert exhibit.native_category == "Výstava"
    assert len({event.native_id for event in events}) == len(events)


@pytest.mark.parametrize(
    ("source", "html"),
    [
        (KlicperovoProgramSource(SourceConfig(name="k", type="klicperovo_program", url="https://example.test/program/")), "<main></main>"),
        (DrakProgramSource(SourceConfig(name="d", type="drak_program", url="https://example.test/program/")), "<main></main>"),
    ],
)
def test_theatre_sources_raise_on_missing_programme_schema(source, html):
    with pytest.raises(ValueError, match="markup missing"):
        source.parse(html)
