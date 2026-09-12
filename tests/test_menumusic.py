"""MENU programmes retain their dated shows, locations and publication years."""

from datetime import date

import pytest

from mostek_kultura.classify import classify
from mostek_kultura.http import FixtureHttp
from mostek_kultura.normalize import PlaceResolver, flag_time, resolve_places
from mostek_kultura.render import build_sources_page
from mostek_kultura.sources import make_source


def source(cfg):
    return make_source(next(s for s in cfg.sources if s.name == 'menumusic-hk'))


class RssHttp:
    def __init__(self, payload):
        self.payload = payload

    def get_text(self, url):
        return self.payload


def test_menu_recorded_programme_dates_and_shared_evenings(cfg, root):
    events = source(cfg).fetch(FixtureHttp(root / 'tests/fixtures/menumusic-hk'))
    current = flag_time(events, cfg.horizon_days, ref=date(2026, 9, 12))
    assert len(current) == 6
    expected = [
        ('Virtuální přítelkyně', '2026-09-13T18:00:00+02:00', 'projekce'),
        ('ROUILLEUX', '2026-09-13T20:00:00+02:00', 'koncert'),
        ('SNOW TRAIL', '2026-09-17T20:00:00+02:00', 'koncert'),
        ('AMOOSED', '2026-09-18T20:00:00+02:00', 'projekce'),
        ('SLOW SLOW LORIS', '2026-09-19T20:00:00+02:00', 'koncert'),
        ('DREKKA', '2026-09-27T20:00:00+02:00', 'koncert'),
    ]
    for title, start, category in expected:
        event = next(e for e in current if title in e.title)
        assert event.start.isoformat() == start
        assert category in event.native_category.lower()
        assert not event.all_day
        assert event.venue == 'Hradecká sýpka'
        assert event.image.startswith('https://64.media.tumblr.com/')
        assert event.url.startswith('https://menumusic.cz/post/')
        assert 'fbclid' not in event.url
    assert 'ORCHARD' in next(e.title for e in current if 'ROUILLEUX' in e.title)
    assert 'NO VIDA' in next(e.title for e in current if 'SNOW TRAIL' in e.title)
    assert 'B°TONG' in next(e.title for e in current if 'DREKKA' in e.title)
    assert len({e.source_id for e in current}) == len(current)
    assert not any('DESOLATION COLONY' in e.title for e in events)  # Explicit Prague show.
    resolve_places(current, PlaceResolver(cfg), {s.name: s.place for s in cfg.sources})
    assert all(e.place == 'Hradec Králové' for e in current)
    classify(current, cfg, {}, use_llm=False)
    assert [e.category for e in current].count('film') == 2
    assert [e.category for e in current].count('koncert') == 4
    groups = build_sources_page(current, cfg, [])['groups']
    hk = next(g for g in groups if g['place'] == 'Hradec Králové')
    assert 'menumusic-hk' in {s['name'] for s in hk['sources']}


def test_menu_old_programme_does_not_roll_into_current_year(cfg, root, monkeypatch):
    fixture = FixtureHttp(root / 'tests/fixtures/menumusic-hk')
    events = source(cfg).fetch(fixture)
    monkeypatch.setenv('MOSTEK_NOW', '2027-09-12T12:00:00+02:00')
    later = source(cfg).fetch(fixture)
    assert [(e.title, e.start, e.source_id) for e in later] == [(e.title, e.start, e.source_id) for e in events]
    assert not flag_time(later, cfg.horizon_days, ref=date(2027, 9, 12))


def test_menu_error_page_is_not_an_empty_calendar(cfg):
    with pytest.raises(ValueError):
        source(cfg).fetch(RssHttp('<html><body>Service unavailable</body></html>'))
    assert source(cfg).fetch(RssHttp('<rss version="2.0"><channel><title>MENU</title></channel></rss>')) == []


def test_menu_requires_hradec_location_in_mixed_city_feed(cfg):
    from html import escape

    def item(body, identifier):
        return (f'<item><link>https://menumusic.cz/post/{identifier}</link>'
                f'<guid>post-{identifier}</guid><pubDate>Sun, 16 Aug 2026 21:25:36 +0200</pubDate>'
                f'<description>{escape(body)}</description></item>')

    posts = [
        item('<h1>17.9.2026 20:00</h1><h2>KLUB, OLOMOUC</h2><h1>Other city / koncert</h1>', '1'),
        item('<h1>18.9.2026 20:00</h1><h1>Unknown location / koncert</h1>', '2'),
        item('<h1>19.9.2026 20:00</h1><h2>HRADECKÁ SÝPKA, HRADEC KRÁLOVÉ</h2>'
             '<h1>Hradec show / koncert</h1>', '3'),
    ]
    events = source(cfg).fetch(RssHttp('<rss><channel>' + ''.join(posts) + '</channel></rss>'))
    assert len(events) == 1
    assert events[0].title == 'Hradec show'
    assert events[0].start.isoformat() == '2026-09-19T20:00:00+02:00'


def test_menu_slashes_in_artwork_and_performer_names_are_not_genres(cfg, root):
    events = source(cfg).fetch(FixtureHttp(root / 'tests/fixtures/menumusic-hk'))
    opening = next(e for e in events if 'DOPPELGÄNGERS' in e.title)
    assert 'C30/37' in opening.title
    assert opening.native_category == 'vernisáž'
    octopoulpe = next(e for e in events if 'OCTOPOULPE' in e.title)
    assert '(KOR/FR)' in octopoulpe.title
    assert octopoulpe.native_category is None
    assert not any('Předprodej' in e.title for e in events)
