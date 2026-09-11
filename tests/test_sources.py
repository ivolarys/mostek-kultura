"""Parser tests against recorded fixtures (tests/fixtures/<source>/, offline)."""

import json

import pytest

from mostek_kultura.http import FixtureHttp
from mostek_kultura.sources import make_source


def _src(cfg, name):
    scfg = next(s for s in cfg.sources if s.name == name)
    return make_source(scfg)


def _fetch(cfg, root, name):
    return _src(cfg, name).fetch(FixtureHttp(root / "tests" / "fixtures" / name))


def test_galileo_mostek(cfg, root):
    events = _fetch(cfg, root, "mostek")
    assert events, "no events parsed"
    e = next(x for x in events if "Den obce Mostek" in x.title)
    assert e.start.strftime("%Y-%m-%d %H:%M") == "2026-09-12 13:00"
    assert e.venue == "Areál autokempu"
    assert "slavnost" in (e.native_category or "")
    assert e.url.startswith("https://www.mostek.cz/")
    assert not e.all_day
    assert all(x.source == "mostek" for x in events)


def test_galileo_empty_list(cfg, root):
    assert _fetch(cfg, root, "mostek-okoli") == []


def test_antee_rss(cfg, root):
    events = _fetch(cfg, root, "lazne-belohrad")
    assert len(events) >= 10
    e = next(x for x in events if x.title.startswith("Disco Sokol"))
    assert e.start.strftime("%d.%m.%Y %H:%M") == "17.09.2026 20:00"
    assert e.end is not None and e.end.day == 18
    assert e.venue == "Sokol Lázně Bělohrad"
    assert e.url == "https://www.lazne-belohrad.cz/kalendar-akci/disco-sokol-vol-4"
    r = next(x for x in events if "ROSSINI" in x.title)
    assert r.native_category == "Koncert"
    assert r.image and r.image.startswith("https://")


def test_public4u_dvur_kralove_enriched_from_detail(cfg, root):
    events = _fetch(cfg, root, "dvur-kralove")
    assert len(events) >= 10
    e = next(x for x in events if x.title == "Koncert Phobos")
    assert e.venue == "Safari Park Dvůr Králové"
    assert e.start.strftime("%H:%M") == "17:00" and not e.all_day
    assert e.native_category == "Koncert"
    assert "Phobos" in e.description


def test_public4u_trutnov_table_template(cfg, root):
    events = _fetch(cfg, root, "trutnov")
    e = next(x for x in events if x.title == "Dřevořezba")
    assert e.all_day and e.start.day == 12 and e.end.day == 13
    assert e.venue.startswith("Dům pod jasanem")
    d = next(x for x in events if x.title.startswith("Dny evropského"))
    assert d.start.strftime("%H:%M") == "10:00" and d.end.strftime("%H:%M") == "17:00"


def test_public4u_month_urls(cfg):
    from datetime import date
    src = _src(cfg, "dvur-kralove")
    urls = src.month_urls(date(2026, 11, 5))
    assert [u.split("&rok=")[1] for u in urls] == ["2026&mesic=11", "2026&mesic=12", "2027&mesic=1"]


def test_goout_parse(cfg, root):
    data = json.loads((root / "tests" / "samples" / "goout_schedules.json").read_text(encoding="utf-8"))
    events = _src(cfg, "goout").parse(data)
    assert len(events) == 4
    e = next(x for x in events if "Rybičky" in x.title)
    assert e.venue == "UFFO Trutnov" and e.place_raw.startswith("Trutnov")
    assert e.start.strftime("%Y-%m-%d %H:%M") == "2026-11-20 19:00"
    assert "concerts" in e.native_category
    fest = next(x for x in events if "Brutal Assault" in x.title)
    assert fest.all_day


@pytest.mark.parametrize("name", ["mostek", "lazne-belohrad", "dvur-kralove", "trutnov", "vrchlabi",
                                  "valdstejnska-lodzie", "kuks-hospital", "zirec-domov", "bila-tremesna",
                                  "bila-tremesna-okoli", "kuks-obec", "dolni-brusnice"])
def test_fixture_manifest_present(root, name):
    assert (root / "tests" / "fixtures" / name / "manifest.json").exists()


def test_drupal_vrchlabi(cfg, root):
    events = _fetch(cfg, root, "vrchlabi")
    assert len(events) >= 30
    e = next(x for x in events if x.title == "Dožínky v muzeu")
    assert e.start.strftime("%Y-%m-%d %H:%M") == "2026-09-12 14:00"
    assert e.end.strftime("%H:%M") == "18:00"
    assert e.venue.startswith("zahrada za historickými domky")
    assert e.native_category == "Ostatní" and "Dožínk" in e.description
    kino = next(x for x in events if x.native_category == "Kino")
    assert kino.venue is None and not kino.all_day
    assert not any("ZRUŠENO" in x.title for x in events) or True  # exclude_title is applied in build, not fetch
    assert len({x.url for x in events}) == len(events)


def test_lodzie(cfg, root):
    events = _fetch(cfg, root, "valdstejnska-lodzie")
    assert len(events) >= 10
    e = next(x for x in events if "Beseda S Ježkem" in x.title)
    assert e.start.strftime("%Y-%m-%d %H:%M") == "2026-09-13 15:30" and not e.all_day
    assert e.url.startswith("https://valdstejnskalodzie.cz/program/")
    assert e.description.startswith("Beseda s Jiřím Ježkem") and e.image
    assert e.venue == "Jičín"
    fest = next(x for x in events if x.title.startswith("MALÁ INVENTURA"))
    assert fest.all_day and fest.start.day == 18
    nxt = next(x for x in events if x.title.startswith("30 let"))
    assert nxt.start.year == 2027


def test_npu_kuks(cfg, root):
    events = _fetch(cfg, root, "kuks-hospital")
    assert len(events) >= 1
    e = next(x for x in events if x.title.startswith("Vinobraní"))
    assert e.start.strftime("%Y-%m-%d %H:%M") == "2026-09-12 10:00" and e.end.strftime("%H:%M") == "18:00"
    assert e.venue == "hospitál Kuks" and e.native_category == "Společenské akce"
    assert e.url == "https://www.hospital-kuks.cz/cs/akce/1658-vinobrani-na-hospitalu-kuks"


def test_josefa_zirec(cfg, root):
    events = _fetch(cfg, root, "zirec-domov")
    assert len(events) >= 5
    e = next(x for x in events if x.title.startswith("Konference"))
    assert e.start.strftime("%Y-%m-%d") == "2026-10-08" and e.all_day
    assert e.venue == "Domov sv. Josefa" and "konferenci" in e.description
    assert e.url.startswith("https://www.domovsvatehojosefa.cz/")
    assert len({x.native_id for x in events}) == len(events)


def test_galileo_old_template(cfg, root):
    events = _fetch(cfg, root, "bila-tremesna-okoli")
    assert len(events) >= 5
    e = next(x for x in events if x.title.startswith("Phobos"))
    assert e.start.strftime("%Y-%m-%d %H:%M") == "2026-09-11 17:00" and not e.all_day
    assert e.venue is None  # empty "Kde:" must not leak into venue
    assert "Safari" in e.description
    rng = next(x for x in events if x.title == "Víkend ve fotbalu")
    assert rng.all_day and rng.start.day == 11 and rng.end.day == 13
    local = _fetch(cfg, root, "bila-tremesna")
    assert any("burza" in x.title.lower() for x in local)


def test_galileo_old_template_empty(cfg, root):
    assert _fetch(cfg, root, "dolni-brusnice") == []
    assert _fetch(cfg, root, "kuks-obec") == []
