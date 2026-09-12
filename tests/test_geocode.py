import json
from datetime import UTC, datetime

from mostek_kultura.config import Config, Place
from mostek_kultura.dates import TZ
from mostek_kultura.geocode import cache_key, geocode_events, load_cache, save_cache
from mostek_kultura.model import Event


def _ev(title, place, venue=None):
    return Event(title=title, start=datetime(2026, 9, 20, 18, 0, tzinfo=TZ), source="test",
                 place=place, venue=venue)


def _cfg(places):
    return Config(timezone="Europe/Prague", horizon_days=60, summary_top_n=10, places=places,
                  venues_allow=[], categories=[], category_map={}, sources=[])


def test_offline_cache_application(cfg, tmp_path):
    """No network (online=False): cache is only read, never written to."""
    cache_path = tmp_path / "geocode.json"
    now = datetime.now(UTC).isoformat(timespec="seconds")
    cache = {
        cache_key("Hankův dům", "Dvůr Králové nad Labem"): {
            "lat": 50.43, "lon": 15.83, "precision": "venue", "q": "x", "ts": now,
        },
        cache_key(None, "Dvůr Králové nad Labem"): {
            "lat": 50.43, "lon": 15.80, "precision": "place", "q": "y", "ts": now,
        },
        cache_key(None, "Trutnov"): {
            "lat": None, "lon": None, "precision": "none", "q": "z", "ts": now,
        },
    }
    save_cache(cache_path, cache)

    ev_venue = _ev("Koncert", "Dvůr Králové nad Labem", venue="Hankův dům")
    ev_place_via_unknown_venue = _ev("Trh", "Dvůr Králové nad Labem", venue="Neznámé místo")
    ev_place_only = _ev("Vernisáž", "Dvůr Králové nad Labem")
    ev_miss_none = _ev("Schůze", "Trutnov")
    ev_miss_unknown = _ev("Beseda", "Hořice")
    events = [ev_venue, ev_place_via_unknown_venue, ev_place_only, ev_miss_none, ev_miss_unknown]

    returned = geocode_events(events, cfg, cache_path, online=False)

    assert returned == cache  # nothing added/changed offline

    assert ev_venue.geo == "venue"
    assert (ev_venue.lat, ev_venue.lon) == (50.43, 15.83)

    # venue key not cached -> falls back to the place centroid
    assert ev_place_via_unknown_venue.geo == "place"
    assert (ev_place_via_unknown_venue.lat, ev_place_via_unknown_venue.lon) == (50.43, 15.80)

    assert ev_place_only.geo == "place"
    assert (ev_place_only.lat, ev_place_only.lon) == (50.43, 15.80)

    # place key cached but precision "none" -> miss
    assert ev_miss_none.geo is None and ev_miss_none.lat is None and ev_miss_none.lon is None
    # place key not cached at all -> miss
    assert ev_miss_unknown.geo is None and ev_miss_unknown.lat is None

    # cache on disk is untouched
    assert load_cache(cache_path) == cache


def test_online_new_lookup_writes_cache_and_respects_bbox(tmp_path, monkeypatch):
    cache_path = tmp_path / "geocode.json"
    mycfg = _cfg([Place("Kuks", [])])

    def fake_nominatim_get(q):
        if q == "Zámek Kuks, Kuks, Česko":
            return [{"lat": "50.45", "lon": "15.85",
                     "display_name": "Zámek Kuks, Kuks, okres Trutnov, Česko"}]
        if q == "Mimo bbox, Kuks, Česko":
            return [{"lat": "10.0", "lon": "10.0", "display_name": "Mimo bbox, Elsewhere"}]
        if q == "Kuks, okres Trutnov, Česko":
            return [{"lat": "50.46", "lon": "15.86", "display_name": "Kuks, okres Trutnov, Česko"}]
        return []

    monkeypatch.setattr("mostek_kultura.geocode._nominatim_get", fake_nominatim_get)
    monkeypatch.setattr("mostek_kultura.geocode.time.sleep", lambda s: None)

    ev_ok = _ev("Koncert", "Kuks", venue="Zámek Kuks")
    ev_bbox = _ev("Něco", "Kuks", venue="Mimo bbox")

    cache = geocode_events([ev_ok, ev_bbox], mycfg, cache_path, online=True, max_new=10)

    assert ev_ok.geo == "venue"
    assert (ev_ok.lat, ev_ok.lon) == (50.45, 15.85)
    assert cache[cache_key("Zámek Kuks", "Kuks")]["precision"] == "venue"

    # outside the CZ sanity bbox -> treated as a miss, falls back to the place centroid
    assert ev_bbox.geo == "place"
    assert (ev_bbox.lat, ev_bbox.lon) == (50.46, 15.86)
    assert cache[cache_key("Mimo bbox", "Kuks")]["precision"] == "none"
    assert cache[cache_key(None, "Kuks")]["precision"] == "place"

    save_cache(cache_path, cache)
    reloaded = json.loads(cache_path.read_text(encoding="utf-8"))
    assert reloaded[cache_key("Zámek Kuks", "Kuks")]["lat"] == 50.45
