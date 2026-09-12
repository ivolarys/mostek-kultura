from mostek_kultura.config import SourceConfig
from mostek_kultura.dates import TZ
from mostek_kultura.http import FixtureHttp
from mostek_kultura.sources.bio_central import BioCentralSource
from mostek_kultura.sources.cinestar import CineStarSource


def test_bio_central_json_ld_and_city_filter(root):
    source = BioCentralSource(SourceConfig(name="bio-central", type="bio_central", url="https://biocentral.cz/", place="Hradec Králové"))
    events = source.fetch(FixtureHttp(root / "tests" / "fixtures" / "bio-central"))
    assert len(events) == 177
    first = events[0]
    assert first.start.strftime("%Y-%m-%d %H:%M") == "2026-09-12 13:00"
    assert first.end.strftime("%H:%M") == "14:28"
    assert first.venue == "Bio Central" and first.native_category == "Film" and first.place_raw == "Hradec Králové"
    cars = [e for e in events if e.title == "Auta"]
    assert len(cars) > 2 and len({e.native_id for e in cars}) == len(cars)
    assert max(e.start.year for e in events) == 2028
    assert source._parse({"@type": "Event", "name": "Cizí kino", "startDate": "2026-09-12T18:00:00+02:00",
                          "location": {"name": "Kino", "address": {"addressLocality": "Praha"}}}) is None


def test_cinestar_public_programme_has_halls_and_multiple_showtimes(root):
    source = CineStarSource(SourceConfig(name="cinestar-hradec", type="cinestar", url="https://cinestar.cz/cz/hradec", place="Hradec Králové"))
    events = source.fetch(FixtureHttp(root / "tests" / "fixtures" / "cinestar-hradec"))
    assert len(events) >= 170
    first = events[0]
    assert first.start.strftime("%Y-%m-%d %H:%M") == "2026-09-12 11:00"
    assert first.venue == "CineStar Hradec Králové — Sál 4"
    assert first.native_category == "Film" and first.url.startswith("https://cinestar.cz/cz/hradec/filmy/movie/")
    assert first.place_raw == "Hradec Králové"
    cars = [e for e in events if e.title == "Auta DABING"]
    assert len(cars) > 2 and len({e.native_id for e in cars}) == len(cars)
    assert all(e.start.tzinfo == TZ and "CineStar Hradec Králové" in (e.venue or "") for e in events)


def test_cinestar_skips_schema_failure():
    source = CineStarSource(SourceConfig(name="cinestar-hradec", type="cinestar", url="https://cinestar.cz/cz/hradec"))
    assert source._parse({"EventId": "1", "Start": "2026-09-12T09:00:00+00:00"}, {}) is None
    assert source._parse({"EventId": "1", "Start": "2026-09-12T09:00:00+00:00", "movieInCinemasAvailability": [
        {"TitleArray": "Film", "movie": []}
    ]}, {}) is not None


def test_cinestar_rejects_graphql_error():
    source = CineStarSource(SourceConfig(name="cinestar-hradec", type="cinestar", url="https://cinestar.cz/cz/hradec"))

    class ErrorHttp:
        def get_json(self, url):
            return {"errors": [{"message": "bad query"}]}

    try:
        source.fetch(ErrorHttp())
    except ValueError as exc:
        assert "GraphQL" in str(exc)
    else:
        raise AssertionError("GraphQL errors must not look like a successful empty programme")


def test_bio_central_rejects_error_html_in_fetch():
    source = BioCentralSource(SourceConfig(name="bio-central", type="bio_central", url="https://biocentral.cz/", place="Hradec Králové"))

    class ErrorHttp:
        def get_text(self, url):
            return "<html><body>error</body></html>"

        def post_text(self, url, data):
            return "<html><body>error</body></html>"

    try:
        source.fetch(ErrorHttp())
    except ValueError as exc:
        assert "no Event JSON-LD" in str(exc)
    else:
        raise AssertionError("Bio error HTML must not look like a successful empty programme")
