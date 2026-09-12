"""Festival dates stay explicit and cover the last advertised day."""

from datetime import date

import pytest

from mostek_kultura.http import FixtureHttp
from mostek_kultura.normalize import PlaceResolver, flag_time, resolve_places
from mostek_kultura.sources import make_source


def source(cfg):
    return make_source(next(s for s in cfg.sources if s.name == "podzimni-sneni"))


class PageHttp:
    def __init__(self, alt):
        self.alt = alt

    def get_text(self, url):
        return f'<title>Podzimní snění</title><img class="hero-date-image" alt="{self.alt}">'


def test_recorded_festival_is_in_hradec_with_actual_venue(cfg, root):
    events = source(cfg).fetch(FixtureHttp(root / "tests/fixtures/podzimni-sneni"))
    assert len(events) == 1
    event = events[0]
    assert event.title == "Podzimní snění 2026"
    assert event.start.isoformat() == "2026-11-06T00:00:00+01:00"
    assert event.end.date() == date(2026, 11, 8)
    assert event.end.hour == 23 and event.all_day
    assert event.native_category == "festival"
    assert event.url == "https://podzimnisneni.cz/"
    assert event.image.startswith("https://podzimnisneni.cz/uploads/2026/")
    assert "Běleč nad Orlicí" in event.venue
    resolve_places(events, PlaceResolver(cfg), {s.name: s.place for s in cfg.sources})
    assert event.place == "Hradec Králové"
    assert flag_time(events, 60, ref=date(2026, 9, 12)) == events
    assert flag_time(events, 60, ref=date(2026, 11, 8)) == events
    assert event.ongoing
    assert flag_time(events, 60, ref=date(2026, 11, 9)) == []


@pytest.mark.parametrize("alt", ["6.–8. listopadu", "termín připravujeme", "8.–6. listopadu 2026", "30.–31. února 2026"])
def test_no_guessed_year_or_invalid_dates(cfg, alt):
    with pytest.raises(ValueError):
        source(cfg).fetch(PageHttp(alt))


def test_new_edition_gets_its_own_dates_and_identity(cfg):
    old = source(cfg).fetch(PageHttp("6.–8. listopadu 2026"))[0]
    new = source(cfg).fetch(PageHttp("5. – 7. listopadu 2027"))[0]
    assert new.start.date() == date(2027, 11, 5)
    assert new.end.date() == date(2027, 11, 7)
    assert new.title == "Podzimní snění 2027"
    assert new.source_id != old.source_id
