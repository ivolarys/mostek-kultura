from mostek_kultura.build import fetch_all
from mostek_kultura.classify import classify
from mostek_kultura.normalize import PlaceResolver, dedupe, flag_time, in_scope, resolve_places

HRADEC_SOURCES = {
    "bio-central", "cinestar-hradec", "klicperovo-divadlo", "divadlo-drak",
    "naplavka-hk", "nablesi", "sauna-nuuk",
}


def test_hradec_recordings_survive_pipeline(root, cfg):
    events, statuses = fetch_all(cfg, root, offline=True, only=HRADEC_SOURCES, persist=False)
    assert {s.name for s in statuses} == HRADEC_SOURCES
    assert all(s.status == "ok" and s.count > 0 for s in statuses), statuses
    events = flag_time(events, cfg.horizon_days)
    resolver = PlaceResolver(cfg)
    resolve_places(events, resolver, {s.name: s.place for s in cfg.sources})
    classify(events, cfg, {}, use_llm=False)
    assert all(e.place == "Hradec Králové" and in_scope(e, resolver) for e in events)
    assert {e.source for e in events} == HRADEC_SOURCES
    assert all(e.category == "film" for e in events if e.source in {"bio-central", "cinestar-hradec"})
    assert all(e.category == "trh" for e in events if e.source == "nablesi")
    assert any(e.category == "vystava" for e in events if e.source == "divadlo-drak")
    screenings = {(e.source, e.start, e.venue, e.title) for e in events if e.category == "film"}
    result = dedupe(events, {s.name: s.priority for s in cfg.sources})
    assert {(e.source, e.start, e.venue, e.title) for e in result if e.category == "film"} == screenings
